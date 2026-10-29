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


def build(np, wp, newton, SolverKamino, protocol, variant):
    drive, warmstart = "bounded_implicit_pd", "containers"
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
    for key, value in protocol["variants"][variant]["overrides"].items():
        owner, field = key.split(".")
        setattr(getattr(config, owner), field, value)
    config.validate()
    solver = SolverKamino(model, config=config)
    state = model.state()
    newton.eval_fk(model, model.joint_q, model.joint_qd, state)
    return model, solver, state, model.control(), config


def snapshot(state, control, solver, defined=True):
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
    import numpy as np
    status = solver.status.numpy() if defined else None
    data["status_defined"] = np.array([defined])
    for name in ("converged", "iterations", "r_p", "r_d", "r_c"):
        data["status_" + name] = status[name].copy() if defined else np.array([0 if name in ("converged", "iterations") else np.nan])
    return data


def command(control, drive, sign):
    control.joint_f.fill_(10. * sign if drive == "explicit" else 0.)
    control.joint_target_q.fill_(sign if drive != "explicit" else 0.)
    control.joint_target_qd.zero_()


class IterationRecorder:
    """Observe active iterations; delegate every call exactly once, including no-ops."""

    def __init__(self, solver, config):
        self.fd = solver._solver_kamino.solver_fd
        self.accel = config.padmm.use_acceleration
        self.max_iterations = config.padmm.max_iterations
        self.rows = []
        self.outer_step = -1
        self.method = "_step_accel" if self.accel else "_step"
        self.original = getattr(self.fd, self.method)
        setattr(self.fd, self.method, self.observe)

    def observe(self, problem):
        d = self.fd.data
        initial_status = d.status.numpy()[0].copy()
        active = initial_status["converged"] == 0 and initial_status["iterations"] < self.max_iterations
        if active:
            row = {"outer_step": self.outer_step}
            for name, field in (("pre_x_p", "x_p"), ("pre_y_input", "y_hat" if self.accel else "y_p"), ("pre_z_input", "z_hat" if self.accel else "z_p")):
                row[name] = getattr(d.state, field).numpy().copy()
            for name in ("P", "bound_lower", "bound_upper", "bcgo", "nbc", "vio", "dim"):
                row[name] = getattr(problem.data, name).numpy().copy()
            row["rho"] = d.penalty.numpy()["rho"].copy()
            conf = d.config.numpy()
            for name in ("eta", "primal_tolerance", "dual_tolerance", "compl_tolerance"):
                row[name] = conf[name].copy()
        result = self.original(problem)
        if active:
            for name in ("x", "y", "z"):
                row[name] = getattr(d.state, name).numpy().copy()
            status = d.status.numpy()
            fields = ["converged", "iterations", "r_p", "r_d", "r_c"]
            if self.accel:
                fields += ["restart", "num_restarts", "r_dx", "r_dy", "r_dz"]
            for name in fields:
                row["status_" + name] = status[name].copy()
            if int(status["iterations"][0]) != int(initial_status["iterations"]) + 1:
                raise ValueError("Active iteration did not advance exactly once")
            self.rows.append(row)
        return result


def simulate(np, model, solver, state, control, config, protocol, out):
    recorder = IterationRecorder(solver, config)
    rows = [snapshot(state, control, solver, defined=False)]
    elapsed = []
    output = model.state()
    dt, steps = protocol["common_run"]["dt_s"], protocol["common_run"]["steps"]
    for step in range(steps):
        state.clear_forces()
        command(control, "bounded_implicit_pd", 1. if step < 40 else -1.)
        recorder.outer_step = step
        start = time.perf_counter()
        solver.step(state, output, control=control, contacts=None, dt=dt)
        rows.append(snapshot(output, control, solver))
        elapsed.append(time.perf_counter() - start)
        state, output = output, state
    if any(set(row) != set(rows[0]) for row in rows):
        raise ValueError("Physical snapshot schema changed; no silent channel drops")
    if any(set(row) != set(recorder.rows[0]) for row in recorder.rows):
        raise ValueError("Iteration snapshot schema changed")
    arrays = {key: np.stack([row[key] for row in rows]) for key in rows[0]}
    arrays["t"] = np.arange(steps + 1, dtype=np.float64) * dt
    arrays["time"] = arrays["t"].copy()
    arrays["step_wall_s_including_export"] = np.asarray(elapsed)
    np.savez_compressed(out / "trajectory.npz", **arrays)
    iterations = {key: np.stack([row[key] for row in recorder.rows]) for key in recorder.rows[0]}
    np.savez_compressed(out / "iterations.npz", **iterations)
    return arrays, iterations


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", required=True)
    parser.add_argument("--repeat", type=int, choices=(1, 2), required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--expected-protocol-sha", required=True)
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    if sha(args.protocol) != args.expected_protocol_sha or protocol.get("status") != "frozen_before_runs":
        raise ValueError("Explicit frozen protocol and matching hash required")
    if args.variant not in protocol["variants"]:
        raise ValueError("Unknown variant")
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    out = HERE / "runs" / f"kamino_pd_convergence_{args.variant}_r{args.repeat}_{stamp}"
    out.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, out / "runner.py")
    shutil.copyfile(args.protocol, out / "protocol.json")
    save(out / "scene.json", protocol["scene"])
    result = {"case": "kamino_pd_convergence", "run_id": out.name, "variant": args.variant, "repeat": args.repeat, "status": "started", "protocol_sha256": args.expected_protocol_sha, "runner_sha256": sha(__file__), "started_at": datetime.now(UTC).isoformat(), "run_directory": out.relative_to(ROOT).as_posix()}
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
        lock = json.loads((ROOT / "manifests/source-lock.json").read_text(encoding="utf-8"))
        rel = "newton/_src/solvers/kamino/solver_kamino.py"
        if sha(source_path) != lock["files"][rel] or sha(source_root / rel) != lock["files"][rel]:
            raise ValueError("Imported solver does not match pinned source")
        installed_parent = Path(newton.__file__).resolve().parent.parent
        locked = {p: h for p, h in lock["files"].items() if p.startswith("newton/") and p.endswith(".py")}
        validation = {"checked_python_files": len(locked), "missing": [p for p in locked if not (installed_parent / p).is_file()], "changed": [p for p,h in locked.items() if (installed_parent/p).is_file() and sha(installed_parent/p) != h], "installed_parent": str(installed_parent)}
        save(out / "installed-source-validation.json", validation)
        if validation["missing"] or validation["changed"]:
            raise ValueError("Installed source differs from locked snapshot")
        environment = {"python": sys.version, "platform": platform.platform(), "packages": {n: version(n) for n in ("numpy", "warp-lang", "newton")}, "device": "cpu", "source_commit": protocol["source_commit"], "source_path": str(source_path), "source_lock_sha256": sha(ROOT / "manifests/source-lock.json"), "installed_source_validation": validation, "source_refs_sha256": {s["path"]: sha(source_root / s["path"]) for s in protocol["source_refs"]}, "private_instrumentation": ["read-only delegation of PADMMSolver._step/_step_accel", "solver_fd.data state/status/config/penalty", "problem_fd.data P/bounds/layout", "internal joints lambda, bodies applied wrench and time"]}
        save(out / "environment.json", environment)
        wp.init()
        model, solver, state, control, config = build(np, wp, newton, SolverKamino, protocol, args.variant)
        save(out / "resolved-config.json", {"solver": plain(config), "effective_solver": plain(solver._config), "treatment": protocol["variants"][args.variant], "dof_act_paths": solver._model_kamino.joints.dof_act_paths.numpy(), "body_mass": model.body_mass.numpy(), "body_inertia": model.body_inertia.numpy(), "body_com": model.body_com.numpy(), "joint_effort_limit": model.joint_effort_limit.numpy(), "joint_target_ke": model.joint_target_ke.numpy(), "joint_target_kd": model.joint_target_kd.numpy()})
        arrays, iterations = simulate(np, model, solver, state, control, config, protocol, out)
        result.update(status="completed", samples=len(arrays["t"]), active_iteration_samples=len(iterations["outer_step"]), raw_sha256=sha(out / "trajectory.npz"), iteration_sha256=sha(out / "iterations.npz"), note="Completion is not physical or strict convergence acceptance")
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


