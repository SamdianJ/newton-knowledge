"""Run one preregistered finite effort-limit switching variant."""
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


def build(wp, newton, SolverKamino, protocol):
    b = newton.ModelBuilder()
    SolverKamino.register_custom_attributes(b)
    b.begin_world()
    body = b.add_link(mass=1., inertia=[1., 0., 0., 0., 1., 0., 0., 0., 1.], com=wp.vec3(0., 0., 0.), lock_inertia=True)
    joint = b.add_joint_revolute(-1, body, axis=newton.Axis.Y, effort_limit=.25, target_ke=20., target_kd=2., armature=0., actuator_mode=newton.JointTargetMode.POSITION)
    b.add_articulation([joint])
    b.end_world()
    model = b.finalize(device="cpu")
    model.set_gravity((0., 0., 0.))
    model.request_state_attributes("body_qdd")
    p = protocol["solver"]
    config = SolverKamino.Config(**{k: p[k] for k in ("dynamics_solver", "sparse_jacobian", "sparse_dynamics", "use_collision_detector", "use_fk_solver")})
    config.dynamics.preconditioning = p["dynamics_preconditioning"]
    for name in ("max_iterations", "use_acceleration", "warmstart_mode", "primal_tolerance", "dual_tolerance", "compl_tolerance", "use_graph_conditionals"):
        setattr(config.padmm, name, p[name])
    solver = SolverKamino(model, config=config)
    state = model.state()
    newton.eval_fk(model, model.joint_q, model.joint_qd, state)
    return model, solver, state, model.control(), config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=("A", "B"), required=True)
    parser.add_argument("--repeat", choices=(1, 2), type=int, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--expected-protocol-sha", required=True)
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    if sha(args.protocol) != args.expected_protocol_sha or protocol["status"] != "frozen_before_runs":
        raise ValueError("Explicitly frozen protocol and matching SHA required")
    cid = protocol["case"]["id"]
    run_id = f"{cid}_{args.variant}_r{args.repeat}_" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    out = HERE / "runs" / run_id
    out.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, out / "runner.py")
    shutil.copyfile(args.protocol, out / "protocol.json")
    save(out / "scene.json", protocol["scene"])
    result = {"case": cid, "run_id": run_id, "variant": args.variant, "repeat": args.repeat, "status": "started", "runner_sha256": sha(__file__), "protocol_sha256": args.expected_protocol_sha, "started_at": datetime.now(UTC).isoformat(), "run_directory": out.relative_to(ROOT).as_posix()}
    save(out / "result.json", result)
    log = (out / "run.log").open("w", encoding="utf-8")
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = Tee(old_out, log), Tee(old_err, log)
    rows, events, step_rows = [], [], []
    code = 0
    try:
        import numpy as np
        import warp as wp
        import newton
        from newton.solvers import SolverKamino

        lock = json.loads((ROOT / "manifests/source-lock.json").read_text(encoding="utf-8"))
        installed = Path(newton.__file__).resolve().parent.parent
        locked = {p: h for p, h in lock["files"].items() if p.startswith("newton/") and p.endswith(".py")}
        source_check = {"checked_python_files": len(locked), "missing": [p for p in locked if not (installed / p).is_file()], "changed": [p for p, h in locked.items() if (installed / p).is_file() and sha(installed / p) != h], "installed_parent": str(installed)}
        save(out / "installed-source-validation.json", source_check)
        if source_check["missing"] or source_check["changed"] or len(locked) != 809:
            raise ValueError("Installed Newton source tree differs from frozen 809-file lock")
        refs = {r["path"]: sha(ROOT / "sources/newton-v1.7.0" / r["path"]) for r in protocol["source_refs"]}
        if any(refs[r["path"]] != r["sha256"] for r in protocol["source_refs"]):
            raise ValueError("Pinned source references changed")
        environment = {"python": sys.version, "platform": platform.platform(), "packages": {n: version(n) for n in ("numpy", "warp-lang", "newton")}, "device": "cpu", "source_commit": protocol["source_commit"], "source_lock_sha256": sha(ROOT / "manifests/source-lock.json"), "source_refs_sha256": refs, "installed_source_validation": source_check, "private_instrumentation": ["_model_kamino.joints.dof_act_paths", "_model_kamino.joints.num_effort_cts", "_solver_kamino.data.joints.bound_a", "_solver_kamino.data.bodies.w_a_i", "_solver_kamino.data.time"]}
        save(out / "environment.json", environment)
        wp.init()
        model, solver, state, control, config = build(wp, newton, SolverKamino, protocol)
        resolved = {"solver": plain(config), "variant": protocol["case"]["variants"][args.variant]}
        for key in ("joint_target_mode", "body_mass", "body_inertia", "body_com", "joint_effort_limit", "joint_target_ke", "joint_target_kd"):
            resolved[key] = getattr(model, key).numpy()
        resolved["dof_act_paths"] = solver._model_kamino.joints.dof_act_paths.numpy()
        resolved["effort_row_count"] = int(solver._model_kamino.joints.num_effort_cts.numpy().sum())
        save(out / "resolved-config.json", resolved)
        limits = protocol["case"]["variants"][args.variant]["limits_Nm"]
        run = protocol["run"]
        dt = run["dt_s"]
        output = model.state()
        rows.append(snapshot(state, control, solver))
        for step in range(run["steps"]):
            phase = step // run["phase_steps"]
            limit = limits[phase]
            before = snapshot(state, control, solver)
            old_limit = model.joint_effort_limit.numpy().copy()
            old_bound = solver._solver_kamino.data.joints.bound_a.numpy().copy()
            old_path = solver._model_kamino.joints.dof_act_paths.numpy().copy()
            changed = bool(float(old_limit[0]) != limit)
            if changed:
                model.joint_effort_limit.fill_(limit)
                solver.notify_model_changed(newton.ModelFlags.JOINT_DOF_FORCE_PROPERTIES)
            after = snapshot(state, control, solver)
            event = {"step_index": step, "phase": phase, "time_s": step * dt, "limit_before": old_limit, "limit_after": model.joint_effort_limit.numpy().copy(), "bound_before": old_bound, "bound_after_notify": solver._solver_kamino.data.joints.bound_a.numpy().copy(), "path_before": old_path, "path_after": solver._model_kamino.joints.dof_act_paths.numpy().copy(), "effort_row_count": int(solver._model_kamino.joints.num_effort_cts.numpy().sum()), "notify_called": changed, "sequence": ["model_fill", "notify", "control", "step"] if changed else ["unchanged_model", "control", "step"], "notify_state_max_abs": {k: float(np.max(np.abs(after[k] - before[k]))) for k in ("body_q", "body_qd", "joint_q", "joint_qd")}}
            state.clear_forces()
            control.joint_f.zero_()
            control.joint_target_q.fill_(run["target_q_rad"][phase])
            control.joint_target_qd.zero_()
            solver.step(state, output, control=control, contacts=None, dt=dt)
            rows.append(snapshot(output, control, solver))
            event["bound_after_step"] = solver._solver_kamino.data.joints.bound_a.numpy().copy()
            event["path_after_step"] = solver._model_kamino.joints.dof_act_paths.numpy().copy()
            events.append(event)
            step_rows.append({"phase": phase, "command_limit": limit, "target_q": run["target_q_rad"][phase], "bound_after_step": event["bound_after_step"], "model_limit_after_step": model.joint_effort_limit.numpy().copy(), "notify_called": changed})
            state, output = output, state
        if any(set(row) != set(rows[0]) for row in rows):
            raise ValueError("Snapshot field set changed")
        arrays = {key: np.stack([row[key] for row in rows]) for key in rows[0]}
        arrays["t"] = np.arange(len(rows), dtype=np.float64) * dt
        for key in step_rows[0]:
            arrays["step_" + key] = np.asarray([r[key] for r in step_rows])
        np.savez_compressed(out / "trajectory.npz", **arrays)
        save(out / "events.json", events)
        result.update(status="completed", samples=len(rows), raw_sha256=sha(out / "trajectory.npz"), note="Execution completion is separate from physical acceptance and convergence diagnostics")
    except Exception as exc:
        code = 1
        traceback.print_exc()
        save(out / "events-partial.json", events)
        if rows:
            np.savez_compressed(out / "trajectory-partial.npz", **{k: np.stack([r[k] for r in rows]) for k in rows[0]})
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
    raise SystemExit(code)


if __name__ == "__main__":
    main()


