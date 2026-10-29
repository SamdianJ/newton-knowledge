"""Run one preregistered Kamino backend setting in a fresh CPU process."""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import inspect
import json
import math
import os
import platform
import shutil
import sys
import time
import traceback
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "manifests/source-lock.json").exists())
SOURCE = ROOT / "sources/newton-v1.7.0"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def plain(x):
    if dataclasses.is_dataclass(x):
        return {f.name: plain(getattr(x, f.name)) for f in dataclasses.fields(x)}
    if isinstance(x, dict):
        return {str(k): plain(v) for k, v in x.items()}
    if isinstance(x, (tuple, list)):
        return [plain(v) for v in x]
    if hasattr(x, "tolist"):
        return plain(x.tolist())
    if isinstance(x, float) and not math.isfinite(x):
        return str(x)
    if x is None or isinstance(x, (int, float, str, bool)):
        return x
    return str(x)


def save(path, value):
    Path(path).write_text(json.dumps(plain(value), ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


class Tee:
    def __init__(self, console, file):
        self.console, self.file = console, file

    def write(self, text):
        self.console.write(text)
        self.file.write(text)
        self.flush()
        return len(text)

    def flush(self):
        self.console.flush()
        self.file.flush()


def execute(args, protocol, output, result):
    sys.path.insert(0, str(SOURCE))
    import numpy as np
    import warp as wp
    import newton
    from newton.solvers import SolverKamino

    lock = json.loads((ROOT / "manifests/source-lock.json").read_text(encoding="utf-8"))
    paths = ["newton/__init__.py", "newton/_src/solvers/kamino/solver_kamino.py", "newton/_src/solvers/kamino/config.py", "newton/_src/solvers/kamino/_src/solvers/padmm/solver.py", "newton/_src/solvers/kamino/_src/solvers/dvi/solver.py"]
    hashes = {p: sha(SOURCE / p) for p in paths}
    if not all(h == lock["files"][p] for p, h in hashes.items()):
        raise RuntimeError("Pinned source hash mismatch")
    if Path(inspect.getfile(SolverKamino)).resolve() != (SOURCE / paths[1]).resolve():
        raise RuntimeError("Loaded Kamino outside pinned source")
    environment = {"python": sys.version, "executable": sys.executable, "platform": platform.platform(), "pid": os.getpid(), "device": "cpu", "dependencies": {name: version(name) for name in ("numpy", "warp-lang", "newton")}, "source_commit": protocol["commit"], "source_sha256": hashes, "loaded_solver": inspect.getfile(SolverKamino)}
    save(output / "environment.json", environment)
    result["environment"] = environment
    scene = protocol["scene"]
    save(output / "scene.json", scene)
    result["scene_sha256"] = sha(output / "scene.json")
    backend = protocol["variants"][args.variant]["dynamics_solver"]
    dt, steps = protocol["simulation"]["dt_s"], protocol["simulation"]["steps"]
    with wp.ScopedDevice("cpu"):
        builder = newton.ModelBuilder(up_axis=newton.Axis.Z, gravity=wp.vec3(*scene["gravity"]))
        SolverKamino.register_custom_attributes(builder)
        material = newton.ModelBuilder.ShapeConfig(density=0.0, mu=scene["contact_mu"], ke=scene["shape_ke_kd"][0], kd=scene["shape_ke_kd"][1], restitution=scene["contact_restitution"])
        builder.add_ground_plane(cfg=material, label="ground")
        builder.begin_world()
        initial = wp.transform(wp.vec3(*scene["initial_position_m"]), wp.quat_identity())
        inertia = scene["inertia_kg_m2"]
        body = builder.add_link(xform=initial, mass=scene["mass_kg"], inertia=[inertia[0], 0, 0, 0, inertia[1], 0, 0, 0, inertia[2]], com=wp.vec3(0, 0, 0), lock_inertia=True, label="guided_sphere")
        builder.add_shape_sphere(body=body, radius=scene["radius_m"], cfg=material)
        joint = builder.add_joint_prismatic(-1, body, parent_xform=initial, child_xform=wp.transform_identity(), axis=wp.vec3(*scene["joint_axis"]), target_ke=0.0, target_kd=0.0, damping=0.0, armature=0.0, friction=0.0, actuator_mode=newton.JointTargetMode.NONE, label="inclined_guide")
        builder.add_articulation([joint])
        builder.end_world()
        model = builder.finalize(device="cpu")
        state0, state1, control = model.state(), model.state(), model.control()
        newton.eval_fk(model, model.joint_q, model.joint_qd, state0)
        cfg = SolverKamino.Config(dynamics_solver=backend, use_collision_detector=True, use_fk_solver=False, integrator="euler")
        for name in ("padmm", "dvi", "fk"):
            section = getattr(cfg, name, None)
            if hasattr(section, "use_graph_conditionals"):
                section.use_graph_conditionals = False
        cfg.constraints.alpha = protocol["common_overrides"]["constraints.alpha"]
        cfg.constraints.gamma = protocol["common_overrides"]["constraints.gamma"]
        cfg.constraints.delta = protocol["common_overrides"]["constraints.delta"]
        cfg.collision_detector.max_contacts_per_world = protocol["common_overrides"]["collision_detector.max_contacts_per_world"]
        cfg.validate()
        result["requested_config"] = plain(cfg)
        started = time.perf_counter()
        solver = SolverKamino(model, config=cfg)
        result["initialization_s"] = time.perf_counter() - started
        result["resolved_config"] = plain(solver._config)
        result["visual"] = {"body_shapes": [{"body": 0, "type": "sphere", "radius": scene["radius_m"]}], "floor": 0.0}
        result["model"] = {"body_count": model.body_count, "world_count": model.world_count, "joint_count": model.joint_count, "body_mass": model.body_mass.numpy(), "body_inertia": model.body_inertia.numpy(), "body_com": model.body_com.numpy(), "joint_axis": model.joint_axis.numpy()}
        expected = (False, True, "LLTB") if backend == "padmm" else (True, False, "LLTBRCM")
        actual = (solver._config.sparse_jacobian, solver._config.dynamics.preconditioning, solver._config.dynamics.linear_solver_type)
        if actual != expected or solver._config.dynamics_solver != backend or solver._config.sparse_dynamics or solver._config.integrator != "euler":
            raise RuntimeError("Backend configuration did not resolve as preregistered")
        states, velocities = [state0.body_q.numpy().copy()], [state0.body_qd.numpy().copy()]
        joints, joint_vel = [state0.joint_q.numpy().copy()], [state0.joint_qd.numpy().copy()]
        timings, counts, statuses = [], [], {}
        try:
            for step in range(steps):
                state0.clear_forces()
                started = time.perf_counter()
                solver.step(state0, state1, control, None, dt)
                wp.synchronize_device("cpu")
                timings.append(time.perf_counter() - started)
                state0, state1 = state1, state0
                states.append(state0.body_q.numpy().copy())
                velocities.append(state0.body_qd.numpy().copy())
                joints.append(state0.joint_q.numpy().copy())
                joint_vel.append(state0.joint_qd.numpy().copy())
                status = solver.status.numpy()
                for field in status.dtype.names:
                    statuses.setdefault(field, []).append(np.asarray(status[field]).reshape(-1)[0].item())
                counts.append(int(solver._contacts_kamino.model_active_contacts.numpy()[0]))
                if not np.isfinite(states[-1]).all() or not np.isfinite(velocities[-1]).all():
                    raise RuntimeError("Nonfinite trajectory")
                if (step + 1) % 48 == 0:
                    print(f"PROGRESS {backend} {step + 1}/{steps}", flush=True)
        finally:
            arrays = {"time": np.arange(len(states)) * dt, "body_q": np.asarray(states), "body_qd": np.asarray(velocities), "joint_q": np.asarray(joints), "joint_qd": np.asarray(joint_vel), "step_seconds": np.asarray(timings), "contact_count": np.asarray(counts), "body_mass": model.body_mass.numpy(), "body_inertia": model.body_inertia.numpy()}
            arrays.update({"status_" + k: np.asarray(v) for k, v in statuses.items()})
            np.savez_compressed(output / "trajectory.npz", **arrays)
            result["raw_file"] = (output / "trajectory.npz").relative_to(ROOT).as_posix()
            result["raw_sha256"] = sha(output / "trajectory.npz")
            result["samples"] = len(states)
        result["status"] = "completed"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=HERE / "protocol.json")
    parser.add_argument("--variant", choices=("A", "B"), required=True)
    parser.add_argument("--repeat", type=int, choices=(1, 2), required=True)
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    if not protocol["status"].startswith("frozen"):
        raise RuntimeError("Protocol must be frozen before execution")
    rid = f"{protocol['case_id']}_{args.variant}_r{args.repeat}_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}"
    output = HERE / "runs" / rid
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(args.protocol, output / "protocol.json")
    shutil.copyfile(Path(__file__), output / "runner.py")
    result = {"run_id": rid, "case_id": protocol["case_id"], "variant": args.variant, "repeat": args.repeat, "solver": "kamino", "status": "started", "started_at": datetime.now(UTC).isoformat(), "runner_sha256": sha(Path(__file__)), "protocol_sha256": sha(args.protocol), "pid": os.getpid(), "instrumentation": protocol["instrumentation"]}
    out, err = sys.stdout, sys.stderr
    with (output / "run.log").open("w", encoding="utf-8") as log:
        sys.stdout, sys.stderr = Tee(out, log), Tee(err, log)
        try:
            execute(args, protocol, output, result)
        except Exception as exc:
            result.update(status="failed", error=type(exc).__name__ + ": " + str(exc))
            traceback.print_exc()
        finally:
            sys.stdout, sys.stderr = out, err
    result["finished_at"] = datetime.now(UTC).isoformat()
    save(output / "result.json", result)
    print(json.dumps({"run_id": rid, "status": result["status"], "result": str(output / 'result.json')}))
    if result["status"] != "completed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
