"""Run one frozen Kamino four-bar case; preserve failures as well as successes."""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import inspect
import json
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
sys.dont_write_bytecode = True


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def plain(value):
    if dataclasses.is_dataclass(value):
        return {field.name: plain(getattr(value, field.name)) for field in dataclasses.fields(value)}
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if hasattr(value, "tolist"):
        return value.tolist()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return {"type": type(value).__module__ + "." + type(value).__qualname__}


def save(path, value):
    path.write_text(json.dumps(plain(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class Tee:
    def __init__(self, stream, file):
        self.stream, self.file = stream, file

    def write(self, text):
        self.stream.write(text)
        self.file.write(text)
        self.flush()
        return len(text)

    def flush(self):
        self.stream.flush()
        self.file.flush()


def model_from_scene(protocol, loop, gravity, newton, wp, np):
    scene = protocol["scene"]
    builder = newton.ModelBuilder(up_axis=newton.Axis.Z, gravity=wp.vec3(*gravity))
    newton.solvers.SolverKamino.register_custom_attributes(builder)
    builder.begin_world(label="fourbar")
    bodies = []
    positions = np.array(scene["body_centers_m"])
    for name, dim, mass, pos in zip(scene["body_names"], scene["dimensions_xyz_m"], scene["mass_kg"], positions):
        dx, dy, dz = dim
        inert = [mass * (dy * dy + dz * dz) / 12, mass * (dx * dx + dz * dz) / 12, mass * (dx * dx + dy * dy) / 12]
        body = builder.add_link(label=name, mass=mass, inertia=wp.mat33(np.diag(inert)), xform=wp.transform(wp.vec3(*pos), wp.quat_identity()), lock_inertia=True)
        builder.add_shape_box(body=body, hx=dx / 2, hy=dy / 2, hz=dz / 2, cfg=newton.ModelBuilder.ShapeConfig(density=0, has_shape_collision=False, has_particle_collision=False))
        bodies.append(body)
    fixed = builder.add_joint_fixed(parent=-1, child=bodies[0], parent_xform=wp.transform(wp.vec3(*positions[0]), wp.quat_identity()), child_xform=wp.transform_identity(), label="world_fixed_base")
    joint_ids = [fixed]
    parent_ids = [0, 1, 2, 3]
    child_ids = [1, 2, 3, 0]
    for i, anchor in enumerate(np.array(scene["hinge_positions_m"])):
        if i == 3 and not loop:
            continue
        parent, child = parent_ids[i], child_ids[i]
        dof = newton.ModelBuilder.JointDofConfig(axis=newton.Axis.Y, actuator_mode=newton.JointTargetMode.EFFORT if i == 0 else newton.JointTargetMode.NONE, effort_limit=float("inf") if i == 0 else 0.0, limit_lower=-1e20, limit_upper=1e20)
        joint_ids.append(builder.add_joint_revolute(parent=bodies[parent], child=bodies[child], parent_xform=wp.transform(wp.vec3(*(anchor - positions[parent])), wp.quat_identity()), child_xform=wp.transform(wp.vec3(*(anchor - positions[child])), wp.quat_identity()), axis=dof, label=scene["joint_order"][i+1]))
    builder.add_articulation(joint_ids[:4], label="fourbar_spanning_tree")
    builder.end_world()
    model = builder.finalize(device="cpu", skip_validation_joints=True)
    model.rigid_contact_max = 1
    return model


def make_config(protocol, case, variant, model, newton):
    config = newton.solvers.SolverKamino.Config.from_model(model)
    for field, value in {**protocol["solver"], **case["solver_override"], **case["variants"][variant]}.items():
        if field == "loop_closing_hinge":
            continue
        if field == "backend":
            field = "dynamics_solver"
        target = config
        names = field.split(".")
        for name in names[:-1]:
            target = getattr(target, name)
        setattr(target, names[-1], value)
    return config


def run(protocol, case, variant, directory):
    import numpy as np
    import warp as wp
    import newton
    from newton.solvers import SolverKamino

    wp.init()
    wp.set_device("cpu")
    source = Path(inspect.getfile(SolverKamino)).resolve()
    expected = ROOT / "sources/newton-v1.7.0/newton/_src/solvers/kamino/solver_kamino.py"
    if source != expected.resolve() or sha(source) != json.loads((ROOT / "manifests/source-lock.json").read_text())["files"]["newton/_src/solvers/kamino/solver_kamino.py"]:
        raise ValueError("Installed Kamino must be the fixed source snapshot")
    environment = {"python": sys.version, "platform": platform.platform(), "device": "cpu", "packages": {name: version(name) for name in ("numpy", "warp-lang", "newton")}, "kamino_source": str(source), "kamino_sha256": sha(source), "source_lock_sha256": sha(ROOT / "manifests/source-lock.json")}
    save(directory / "environment.json", environment)
    is_fk = case["id"] == "kamino_fourbar_fk"
    model = model_from_scene(protocol, loop=True if is_fk else variant == "B", gravity=[0,0,0] if is_fk else case["gravity_m_s2"], newton=newton, wp=wp, np=np)
    config = make_config(protocol, case, variant, model, newton)
    solver = SolverKamino(model, config)
    state, output = model.state(), model.state()
    control = model.control()
    solver.reset(state)
    save(directory / "resolved-config.json", plain(solver._config))
    model_arrays = {name: getattr(model, name).numpy().tolist() for name in ("joint_parent", "joint_child", "joint_X_p", "joint_X_c", "joint_q_start", "joint_qd_start", "body_mass", "body_inertia")}
    save(directory / "scene.json", {**protocol["scene"], "loop_closing_hinge": True if is_fk else variant == "B", "model_arrays": model_arrays, "internal_instrumentation": "Read solver._config solely to archive resolved settings; simulation uses public ModelBuilder/SolverKamino/reset/step/status."})
    arrays = {name: [] for name in ("time", "body_q", "body_qd", "joint_q", "joint_qd")}
    statuses = []
    elapsed = []

    def sample(t):
        arrays["time"].append(t)
        for name in ("body_q", "body_qd", "joint_q", "joint_qd"):
            arrays[name].append(getattr(state, name).numpy().copy())

    if is_fk:
        success = wp.zeros(1, dtype=wp.bool, device="cpu")
        for i, angle in enumerate(case["input_actuator_angles_rad"]):
            requested = wp.array([angle], dtype=wp.float32, device="cpu")
            start = time.perf_counter()
            solver.reset(state, config=SolverKamino.ResetConfig(body_poses=SolverKamino.ResetConfig.FromActuatorQ(requested)), success_mask=success)
            sample(float(i))
            elapsed.append(time.perf_counter() - start)
            statuses.append(bool(success.numpy()[0]))
        arrays["requested_angle"] = case["input_actuator_angles_rad"]
        arrays["reset_success"] = statuses
    else:
        sample(0.0)
        active_dof = int(model.joint_qd_start.numpy()[1])
        effort = np.zeros(model.joint_dof_count, dtype=np.float32)
        effort[active_dof] = case["actuator_torque_Nm"]
        for i in range(case["steps"]):
            state.clear_forces()
            control.joint_f.assign(effort)
            start = time.perf_counter()
            solver.step(state, output, control, None, case["dt_s"])
            wp.synchronize_device("cpu")
            elapsed.append(time.perf_counter() - start)
            state, output = output, state
            sample((i + 1) * case["dt_s"])
            status = solver.status.numpy()
            statuses.append({field: status[field].tolist() for field in ("converged", "iterations", "r_p", "r_d", "r_c")})
    arrays["elapsed_seconds"] = elapsed
    np.savez_compressed(directory / "trajectory.npz", **{k: np.asarray(v) for k,v in arrays.items()})
    save(directory / "solver-status.json", statuses)
    return {"samples": len(arrays["time"]), "trajectory_sha256": sha(directory / "trajectory.npz"), "environment": environment, "all_finite": all(np.isfinite(np.asarray(v)).all() for v in arrays.values()), "scope": "FK samples are ordered pose queries, not time integration; loop dynamics samples include t=0 and all 120 steps."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=HERE / "protocol.json")
    parser.add_argument("--case", required=True)
    parser.add_argument("--variant", choices=["A","B"], required=True)
    parser.add_argument("--repeat", type=int, required=True)
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    if protocol["status"] != "frozen_before_runs":
        raise ValueError("Protocol must be frozen before any Newton import or run")
    case = next(c for c in protocol["cases"] if c["id"] == args.case)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    directory = HERE / "runs" / f"{args.case}-{args.variant}-r{args.repeat}-{stamp}"
    directory.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(args.protocol, directory / "protocol.json")
    shutil.copyfile(__file__, directory / "runner.py")
    result = {"case_id": args.case, "variant": args.variant, "repeat": args.repeat, "run_id": directory.name, "started_utc": stamp, "protocol_sha256": sha(args.protocol), "runner_sha256": sha(__file__), "status": "started"}
    with (directory / "run.log").open("w", encoding="utf-8") as log:
        out, err = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = Tee(out, log), Tee(err, log)
        try:
            result.update(run(protocol, case, args.variant, directory))
            result["status"] = "completed"
        except Exception as exc:
            result.update(status="failed", error=type(exc).__name__ + ": " + str(exc))
            traceback.print_exc()
        finally:
            save(directory / "result.json", result)
            sys.stdout, sys.stderr = out, err
    print(json.dumps({"run": str(directory.relative_to(ROOT)), "status": result["status"], "error": result.get("error")}, ensure_ascii=False))
    if result["status"] != "completed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
