"""Run one pre-frozen drive/reset variant; never overwrite a run directory."""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import inspect
import json
import math
import platform
import shutil
import sys
import time
import traceback
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "manifests/source-lock.json").exists())
HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def plain(value):
    if dataclasses.is_dataclass(value):
        return {f.name: plain(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    if hasattr(value, "tolist"):
        return plain(value.tolist())
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return {"type": type(value).__module__ + "." + type(value).__qualname__}


def save(path, value):
    Path(path).write_text(json.dumps(plain(value), ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


class Tee:
    def __init__(self, console, log):
        self.console, self.log = console, log

    def write(self, value):
        self.console.write(value)
        self.log.write(value)
        self.flush()
        return len(value)

    def flush(self):
        self.console.flush()
        self.log.flush()


def build(np, wp, newton, SolverKamino, protocol, drive, warmstart):
    builder = newton.ModelBuilder()
    SolverKamino.register_custom_attributes(builder)
    builder.begin_world()
    body = builder.add_link(mass=1.0, inertia=[1., 0., 0., 0., 1., 0., 0., 0., 1.], com=wp.vec3(.5, 0., 0.), lock_inertia=True)
    bounded = drive == "bounded_implicit_pd"
    joint = builder.add_joint_revolute(-1, body, axis=newton.Axis.Y, effort_limit=1., target_ke=100. if bounded else 0., target_kd=2. if bounded else 0., armature=0., actuator_mode=newton.JointTargetMode.POSITION if bounded else newton.JointTargetMode.NONE)
    builder.add_articulation([joint])
    builder.end_world()
    model = builder.finalize(device="cpu")
    model.set_gravity((0., 0., 0.))
    model.request_state_attributes("body_qdd")
    config = SolverKamino.Config(dynamics_solver="padmm", sparse_jacobian=False, sparse_dynamics=False, use_collision_detector=False, use_fk_solver=False)
    config.padmm.use_graph_conditionals = False
    config.padmm.max_iterations = 200
    config.padmm.use_acceleration = True
    config.padmm.warmstart_mode = warmstart
    config.padmm.primal_tolerance = 1e-7
    config.padmm.dual_tolerance = 1e-7
    config.padmm.compl_tolerance = 1e-7
    solver = SolverKamino(model, config=config)
    state = model.state()
    newton.eval_fk(model, model.joint_q, model.joint_qd, state)
    return model, solver, state, model.control(), config


def snapshot(state, control, solver):
    data = {}
    for key in ("body_q", "body_qd", "body_qdd", "joint_q", "joint_qd", "joint_lambdas_tau", "body_f"):
        value = getattr(state, key, None)
        if value is not None:
            data[key] = value.numpy().copy()
    for key in ("joint_f", "joint_target_q", "joint_target_qd"):
        value = getattr(control, key, None)
        if value is not None:
            data["control_" + key] = value.numpy().copy()
    # Private diagnostic reads are recorded as instrumentation, not public API.
    internal = solver._solver_kamino.data
    if "joint_lambdas_tau" not in data:
        # Newton adds this extended State field lazily on first step/reset.
        # Preserve its initial zero-width/zero-valued sample so the entire
        # measured channel survives serialization alongside subsequent samples.
        data["joint_lambdas_tau"] = internal.joints.lambda_tau_j.numpy().copy()
    data["internal_time"] = internal.time.time.numpy().copy()
    data["internal_steps"] = internal.time.steps.numpy().copy()
    data["applied_body_wrench"] = internal.bodies.w_a_i.numpy().copy()
    status = solver.status.numpy()
    for name in ("converged", "iterations", "r_p", "r_d", "r_c"):
        data["status_" + name] = status[name].copy()
    return data


def command(control, drive, sign):
    control.joint_f.fill_(10. * sign if drive == "explicit" else 0.)
    control.joint_target_q.fill_(sign if drive != "explicit" else 0.)
    control.joint_target_qd.zero_()


def simulate(np, model, solver, state, control, drive, steps, dt):
    rows = [snapshot(state, control, solver)]
    elapsed = []
    output = model.state()
    for step in range(steps):
        state.clear_forces()
        command(control, drive, 1. if step < 40 else -1.)
        start = time.perf_counter()
        solver.step(state, output, control=control, contacts=None, dt=dt)
        # Snapshot .numpy() synchronizes; time is diagnostic only.
        rows.append(snapshot(output, control, solver))
        elapsed.append(time.perf_counter() - start)
        state, output = output, state
    if any(set(row) != set(rows[0]) for row in rows):
        raise ValueError("Snapshot channels changed during run; raw columns must never be silently dropped")
    arrays = {key: np.stack([row[key] for row in rows]) for key in rows[0]}
    arrays["time"] = np.arange(steps + 1, dtype=np.float64) * dt
    arrays["step_wall_s_including_export"] = np.asarray(elapsed)
    return state, arrays


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True)
    parser.add_argument("--variant", choices=("A", "B"), required=True)
    parser.add_argument("--repeat", type=int, choices=(1, 2), required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--expected-protocol-sha", required=True)
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    if sha(args.protocol) != args.expected_protocol_sha or protocol.get("status") != "frozen_before_runs":
        raise ValueError("Protocol must be explicitly frozen and SHA256-matched before execution")
    case = next(c for c in protocol["cases"] if c["id"] == args.case)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    out = HERE / "runs" / f"{args.case}_{args.variant}_r{args.repeat}_{stamp}"
    out.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, out / "runner.py")
    shutil.copyfile(args.protocol, out / "protocol.json")
    save(out / "scene.json", protocol["scene"])
    result = {"case": args.case, "variant": args.variant, "repeat": args.repeat, "status": "started", "protocol_sha256": args.expected_protocol_sha, "runner_sha256": sha(__file__), "started_at": datetime.now(UTC).isoformat(), "run_directory": out.relative_to(ROOT).as_posix()}
    save(out / "result.json", result)
    log = (out / "run.log").open("w", encoding="utf-8")
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = Tee(old_out, log), Tee(old_err, log)
    exit_code = 0
    try:
        import numpy as np
        import warp as wp
        import newton
        from newton.solvers import SolverKamino

        source_path = Path(inspect.getfile(SolverKamino)).resolve()
        source_root = ROOT / "sources/newton-v1.7.0"
        rel = "newton/_src/solvers/kamino/solver_kamino.py"
        lock = json.loads((ROOT / "manifests/source-lock.json").read_text(encoding="utf-8"))
        if sha(source_path) != lock["files"][rel] or sha(source_root / rel) != lock["files"][rel]:
            raise ValueError("Imported solver does not match pinned source")
        installed_parent = Path(newton.__file__).resolve().parent.parent
        locked_python = {p: h for p, h in lock["files"].items() if p.startswith("newton/") and p.endswith(".py")}
        missing = [p for p in locked_python if not (installed_parent / p).is_file()]
        changed = [p for p, h in locked_python.items() if (installed_parent / p).is_file() and sha(installed_parent / p) != h]
        source_validation = {"checked_python_files": len(locked_python), "missing": missing, "changed": changed, "installed_parent": str(installed_parent)}
        save(out / "installed-source-validation.json", source_validation)
        if missing or changed:
            raise ValueError("Installed Newton Python tree differs from locked source: " + repr(source_validation))
        source_files = {s["path"]: sha(source_root / s["path"]) for s in protocol["source_refs"]}
        environment = {"python": sys.version, "platform": platform.platform(), "packages": {n: version(n) for n in ("numpy", "warp-lang", "newton")}, "device": "cpu", "source_commit": protocol["source_commit"], "source_path": str(source_path), "source_file_sha256": sha(source_path), "source_lock_sha256": sha(ROOT / "manifests/source-lock.json"), "source_refs_sha256": source_files, "private_instrumentation": ["_model_kamino.joints.dof_act_paths", "_solver_kamino.data.bodies.w_a_i", "_solver_kamino.data.time"]}
        environment["installed_source_validation"] = source_validation
        save(out / "environment.json", environment)
        wp.init()
        drive = case["variants"][args.variant]["drive"] if args.case == "kamino_drive_effort_paths" else "bounded_implicit_pd"
        warmstart = "containers" if args.case == "kamino_drive_effort_paths" else "internal"
        model, solver, state, control, config = build(np, wp, newton, SolverKamino, protocol, drive, warmstart)
        save(out / "resolved-config.json", {"solver": plain(config), "drive": drive, "joint_target_mode": model.joint_target_mode.numpy(), "dof_act_paths": solver._model_kamino.joints.dof_act_paths.numpy(), "dof_act_types": solver._model_kamino.joints.dof_act_types.numpy(), "body_mass": model.body_mass.numpy(), "body_inertia": model.body_inertia.numpy(), "body_com": model.body_com.numpy(), "joint_effort_limit": model.joint_effort_limit.numpy(), "joint_target_ke": model.joint_target_ke.numpy(), "joint_target_kd": model.joint_target_kd.numpy()})
        dt = protocol["common_run"]["dt_s"]
        if args.case != "kamino_drive_effort_paths":
            if args.variant == "B" or args.case == "kamino_reset_preserve_replay":
                state, warm = simulate(np, model, solver, state, control, drive, 60, dt)
                np.savez_compressed(out / "warmup.npz", **warm)
            if args.case == "kamino_reset_preserve_replay" and args.variant == "A":
                donor = snapshot(state, control, solver)
                model, solver, state, control, config = build(np, wp, newton, SolverKamino, protocol, drive, warmstart)
                state.body_q.assign(donor["body_q"])
                state.body_qd.assign(donor["body_qd"])
            command(control, drive, -1.)
            before = snapshot(state, control, solver)
            success = wp.zeros(model.world_count, dtype=wp.bool, device="cpu")
            reset_config = None if args.case == "kamino_reset_default_replay" else SolverKamino.ResetConfig.preserve()
            solver.reset(state=state, config=reset_config, success_mask=success)
            after = snapshot(state, control, solver)
            np.savez_compressed(out / "reset-snapshots.npz", **{"before_" + k: v for k, v in before.items()}, **{"after_" + k: v for k, v in after.items()}, success_mask=success.numpy())
        state, arrays = simulate(np, model, solver, state, control, drive, protocol["common_run"]["steps"], dt)
        np.savez_compressed(out / "trajectory.npz", **arrays)
        result.update(status="completed", samples=len(arrays["time"]), raw_sha256=sha(out / "trajectory.npz"), note="Completion is not acceptance; independent analyzer applies frozen criteria.")
    except Exception as exc:
        exit_code = 1
        traceback.print_exc()
        result.update(status="failed", error=repr(exc))
    finally:
        result["finished_at"] = datetime.now(UTC).isoformat()
        sys.stdout.flush()
        sys.stderr.flush()
        sys.stdout, sys.stderr = old_out, old_err
        log.close()
        result["files_sha256"] = {p.name: sha(p) for p in sorted(out.iterdir()) if p.is_file() and p.name != "result.json"}
        save(out / "result.json", result)
        print(json.dumps({"status": result["status"], "run": result["run_directory"]}))
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
