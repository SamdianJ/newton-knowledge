"""Execute one frozen Newton 1.7.0 parameter-lab variant and preserve its inputs."""

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

sys.dont_write_bytecode = True
ROOT = next(
    p
    for p in Path(__file__).resolve().parents
    if (p / "planning/p4/protocol.json").is_file()
)
LAB = ROOT / "experiments/solver_parameter_lab"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plain(value):
    if dataclasses.is_dataclass(value):
        return {
            f.name: plain(getattr(value, f.name)) for f in dataclasses.fields(value)
        }
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    if hasattr(value, "tolist"):
        return value.tolist()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return {
        "type": type(value).__module__ + "." + type(value).__qualname__,
        "name": getattr(value, "__qualname__", None),
    }


def save(path, value):
    path.write_text(
        json.dumps(plain(value), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


class Tee:
    def __init__(self, console, file):
        self.console = console
        self.file = file

    def write(self, value):
        self.console.write(value)
        self.console.flush()
        self.file.write(value)
        self.file.flush()
        return len(value)

    def flush(self):
        self.console.flush()
        self.file.flush()


def scene_description(case):
    if "stack" in case["scene"]:
        bodies = [
            {
                "shape": "box",
                "half_extents": [0.1, 0.1, 0.1],
                "density": 500.0,
                "at": [0.002 * i, 0, 0.101 + 0.22 * i],
                "tilt_y": 0.012 * i,
            }
            for i in range(5)
        ]
    else:
        height = 0.085 if case["id"] == "kamino_contact_stabilization" else 0.35
        bodies = [
            {
                "shape": "sphere",
                "radius": 0.1,
                "density": 1 / (4 / 3 * math.pi * 0.1**3),
                "at": [0, 0, height],
                "tilt_y": 0.0,
            }
        ]
    return {
        "world_count": 1,
        "up_axis": "Z",
        "gravity": [0, 0, -9.81],
        "floor_z": 0.0,
        "bodies": bodies,
        "mu": 0.6,
        "common_ke": 20000.0,
        "common_kd": 300.0,
    }


def make_model(scene, treatment, newton, wp):
    ke = float(treatment.get("ke", scene["common_ke"]))
    kd = 2 * math.sqrt(ke) if "ke" in treatment else scene["common_kd"]
    builder = newton.ModelBuilder(up_axis=newton.Axis.Z, gravity=wp.vec3(0, 0, -9.81))
    builder.add_ground_plane(
        cfg=newton.ModelBuilder.ShapeConfig(density=0, mu=scene["mu"], ke=ke, kd=kd),
        label="ground",
    )
    builder.begin_world()
    visual = []
    for i, item in enumerate(scene["bodies"]):
        rotation = wp.quat_from_axis_angle(wp.vec3(0, 1, 0), item["tilt_y"])
        body = builder.add_body(
            xform=wp.transform(wp.vec3(*item["at"]), rotation), label="body_" + str(i)
        )
        cfg = newton.ModelBuilder.ShapeConfig(
            density=item["density"], mu=scene["mu"], ke=ke, kd=kd
        )
        if item["shape"] == "sphere":
            builder.add_shape_sphere(body=body, radius=item["radius"], cfg=cfg)
            visual.append({"body": body, "type": "sphere", "radius": item["radius"]})
        else:
            h = item["half_extents"]
            builder.add_shape_box(body=body, hx=h[0], hy=h[1], hz=h[2], cfg=cfg)
            visual.append({"body": body, "type": "box", "half_extents": h})
    builder.end_world()
    model = builder.finalize(device="cpu")
    return model, visual, {"ke": ke, "kd": kd}


def support_extent(poses, shape, np):
    if shape["type"] == "sphere":
        return np.full(poses.shape[0], shape["radius"])
    q = poses[:, 3:7].astype(float)
    q = q / np.linalg.norm(q, axis=1)[:, None]
    x, y, z, w = q.T
    rowz = np.column_stack(
        (2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y))
    )
    return np.abs(rowz) @ np.asarray(shape["half_extents"])


def measure(arrays, visual, mass, inertia, np):
    poses = arrays["body_q"]
    vel = arrays["body_qd"]
    extents = np.column_stack(
        [support_extent(poses[:, i], s, np) for i, s in enumerate(visual)]
    )
    bottoms = poses[:, :, 2] - extents
    tops = poses[:, :, 2] + extents
    penetration = np.maximum(0, -bottoms.min(axis=1)) * 1000
    # Full rigid-body kinetic energy, using world angular velocity and body inertia.
    energy = 0.5 * np.sum(mass[None, :] * np.sum(vel[:, :, :3] ** 2, axis=2), axis=1)
    for i in range(poses.shape[1]):
        q = poses[:, i, 3:].astype(float)
        q /= np.linalg.norm(q, axis=1)[:, None]
        x, y, z, w = q.T
        rotations = np.stack(
            (
                1 - 2 * (y * y + z * z),
                2 * (x * y - z * w),
                2 * (x * z + y * w),
                2 * (x * y + z * w),
                1 - 2 * (x * x + z * z),
                2 * (y * z - x * w),
                2 * (x * z - y * w),
                2 * (y * z + x * w),
                1 - 2 * (x * x + y * y),
            ),
            axis=1,
        ).reshape(-1, 3, 3)
        omega = np.einsum("tji,tj->ti", rotations, vel[:, i, 3:6])
        energy += 0.5 * np.einsum("ti,ij,tj->t", omega, inertia[i], omega)
    tail = max(1, len(penetration) // 5)
    metrics = {
        "finite": bool(all(np.isfinite(v).all() for v in arrays.values())),
        "steps": len(arrays["step_ms"]),
        "initial_penetration_mm": float(penetration[0]),
        "max_penetration_mm": float(penetration.max()),
        "final_penetration_mm": float(penetration[-1]),
        "tail_penetration_mm": float(penetration[-tail:].mean()),
        "initial_stack_height_m": float(tops[0].max()),
        "final_stack_height_m": float(tops[-1].max()),
        "max_speed_m_s": float(np.linalg.norm(vel[:, :, :3], axis=2).max()),
        "final_kinetic_energy_J": float(energy[-1]),
        "max_kinetic_energy_J": float(energy.max()),
        "step_ms_median_after_warmup": float(np.median(arrays["step_ms"][5:])),
    }
    for field in ("r_p", "r_d", "r_c", "iterations", "converged"):
        key = "status_" + field
        if key in arrays:
            a = arrays[key]
            metrics[field + "_final"] = float(a[-1])
            metrics[field + "_p95"] = float(np.percentile(a, 95))
            metrics[field + "_mean"] = float(a.mean())
    return metrics, {
        "penetration_mm": penetration,
        "stack_height_m": tops.max(axis=1),
        "kinetic_energy_J": energy,
    }


def run(args, case, protocol, run_dir, result):
    import numpy as np
    import newton
    import warp as wp

    result["environment"] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "device": "cpu",
        "packages": {
            n: version(n)
            for n in ["newton", "numpy", "warp-lang", "mujoco", "mujoco-warp"]
        },
        "executable": sys.executable,
    }
    if result["environment"]["packages"]["newton"] != "1.7.0":
        raise RuntimeError("Wrong Newton version")
    wp.init()
    result["environment"]["warp_devices"] = [str(d) for d in wp.get_devices()]
    cls = (
        newton.solvers.SolverMuJoCo
        if case["solver"] == "mujoco"
        else newton.solvers.SolverKamino
    )
    relative = (
        "newton/_src/solvers/" + case["solver"] + "/solver_" + case["solver"] + ".py"
    )
    source_file = Path(inspect.getfile(cls))
    locked = json.loads((ROOT / "manifests/source-lock.json").read_text())["files"][
        relative
    ]
    result["source_verification"] = {
        "path": relative,
        "installed_path": str(source_file),
        "sha256": sha(source_file),
        "expected_sha256": locked,
        "matches_snapshot": sha(source_file) == locked,
    }
    if not result["source_verification"]["matches_snapshot"]:
        raise RuntimeError("Installed solver differs from fixed source")
    description = scene_description(case)
    treatment = case[args.variant]
    dt = protocol["common"]["dt_seconds"]
    steps = round(case["duration_seconds"] / dt)
    if args.steps is not None:
        steps = args.steps
        result["run_class"] = "probe_override_not_ab"
    save(run_dir / "scene.json", description)
    result["scene_sha256"] = sha(run_dir / "scene.json")
    started = time.perf_counter()
    with wp.ScopedDevice("cpu"):
        model, visual, materials = make_model(description, treatment, newton, wp)
        state0 = model.state()
        state1 = model.state()
        control = model.control()
        newton.eval_fk(model, model.joint_q, model.joint_qd, state0)
        if case["solver"] == "mujoco":
            requested = {
                "use_mujoco_cpu": True,
                "use_mujoco_contacts": True,
                "iterations": int(treatment.get("iterations", 50)),
            }
            solver = cls(model, **requested)
        else:
            cfg = cls.Config(dynamics_solver="padmm", use_collision_detector=True)
            for name in ("padmm", "dvi", "fk"):
                section = getattr(cfg, name, None)
                if hasattr(section, "use_graph_conditionals"):
                    section.use_graph_conditionals = False
            cfg.padmm.max_iterations = int(treatment.get("max_iterations", 60))
            cfg.constraints.gamma = float(treatment.get("gamma", 0.01))
            cfg.constraints.delta = 1e-6
            cfg.collision_detector.max_contacts_per_world = 128
            cfg.validate()
            requested = plain(cfg)
            solver = cls(model, config=cfg)
        result["initialization_ms"] = (time.perf_counter() - started) * 1000
        result["config"] = {
            "constructor": requested,
            "treatment": treatment,
            "material_values": materials,
            "dt": dt,
            "steps": steps,
            "model": {
                "world_count": model.world_count,
                "body_mass": model.body_mass.numpy(),
                "body_inertia": model.body_inertia.numpy(),
                "body_com": model.body_com.numpy(),
                "body_world": model.body_world.numpy(),
                "shape_world": model.shape_world.numpy(),
                "gravity": model.gravity.numpy(),
                "shape_material_ke": model.shape_material_ke.numpy(),
                "shape_material_kd": model.shape_material_kd.numpy(),
                "shape_material_mu": model.shape_material_mu.numpy(),
            },
            "scene_description": description,
            "seed": "no RNG",
        }
        if model.world_count != 1 or model.body_count != len(visual):
            raise RuntimeError("Unexpected model shape")
        mass = model.body_mass.numpy().astype(float)
        inertia = model.body_inertia.numpy().astype(float)
        if not np.all(mass > 0) or not np.all(np.linalg.eigvalsh(inertia) > 0):
            raise RuntimeError("Nonphysical primitive inertia")
        states = [state0.body_q.numpy().copy()]
        velocities = [state0.body_qd.numpy().copy()]
        timings = []
        status_samples = {}
        native_ncon = []
        native_niter = []
        for step in range(steps):
            state0.clear_forces()
            clock = time.perf_counter_ns()
            solver.step(state0, state1, control, None, dt)
            wp.synchronize_device("cpu")
            timings.append((time.perf_counter_ns() - clock) / 1e6)
            state0, state1 = state1, state0
            pose = state0.body_q.numpy().copy()
            velocity = state0.body_qd.numpy().copy()
            if not np.isfinite(pose).all() or not np.isfinite(velocity).all():
                raise RuntimeError("Nonfinite state at step " + str(step))
            states.append(pose)
            velocities.append(velocity)
            if case["solver"] == "kamino":
                status = solver.status.numpy()
                for field in status.dtype.names:
                    status_samples.setdefault(field, []).append(
                        np.asarray(status[field]).reshape(-1)[0].item()
                    )
            else:
                native_ncon.append(solver.mj_data.ncon)
                if hasattr(solver.mj_data, "solver_niter"):
                    native_niter.append(int(np.max(solver.mj_data.solver_niter)))
            if (step + 1) % 60 == 0:
                print(
                    "PROGRESS "
                    + case["id"]
                    + " "
                    + args.variant
                    + " "
                    + str(step + 1)
                    + "/"
                    + str(steps),
                    flush=True,
                )
        arrays = {
            "times": np.arange(steps + 1, dtype=float) * dt,
            "body_q": np.asarray(states),
            "body_qd": np.asarray(velocities),
            "step_ms": np.asarray(timings),
            "body_mass": mass,
            "body_inertia": inertia,
        }
        for field, values in status_samples.items():
            arrays["status_" + field] = np.asarray(values)
        if native_ncon:
            arrays["native_ncon"] = np.asarray(native_ncon)
        if native_niter:
            arrays["native_solver_niter"] = np.asarray(native_niter)
        metrics, curves = measure(arrays, visual, mass, inertia, np)
        arrays.update({"curve_" + k: v for k, v in curves.items()})
        np.savez_compressed(run_dir / "trajectory.npz", **arrays)
        result.update(
            visual={"body_shapes": visual, "floor": 0.0},
            metrics=metrics,
            raw_file=(run_dir / "trajectory.npz").relative_to(ROOT).as_posix(),
            raw_sha256=sha(run_dir / "trajectory.npz"),
            samples=steps + 1,
            duration_seconds=steps * dt,
        )
        if case["solver"] == "mujoco":
            result["resolved_backend"] = {
                k: plain(getattr(solver.mj_model.opt, k))
                for k in (
                    "iterations",
                    "tolerance",
                    "integrator",
                    "solver",
                    "cone",
                    "impratio",
                    "disableflags",
                    "timestep",
                )
            }
            result["resolved_backend"].update(
                geom_solref=solver.mj_model.geom_solref.tolist(),
                geom_solimp=solver.mj_model.geom_solimp.tolist(),
                geom_friction=solver.mj_model.geom_friction.tolist(),
            )
            if result["resolved_backend"]["iterations"] != requested["iterations"]:
                raise RuntimeError("Treatment did not reach native option")
            if args.steps is None and max(native_ncon, default=0) <= 0:
                raise RuntimeError("No actual contact in contact experiment")
        else:
            result["resolved_backend"] = plain(solver._config)
            if args.steps is None and max(status_samples.get("iterations", [0])) <= 0:
                raise RuntimeError("No active PADMM iterations")
        result["status"] = (
            "completed" if args.steps is None else "probe_completed_not_ab"
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True)
    parser.add_argument("--variant", choices=["A", "B"], required=True)
    parser.add_argument(
        "--protocol", type=Path, default=ROOT / "planning/p4/protocol.json"
    )
    parser.add_argument("--steps", type=int)
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    case = next(c for c in protocol["cases"] if c["id"] == args.case)
    identifier = (
        args.case
        + "_"
        + args.variant
        + "_"
        + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    )
    directory = LAB / "runs" / identifier
    directory.mkdir(parents=True)
    shutil.copyfile(args.protocol, directory / "protocol.json")
    shutil.copyfile(Path(__file__), directory / "run_program.py")
    result = {
        "run_id": identifier,
        "case_id": args.case,
        "solver": case["solver"],
        "variant": args.variant,
        "version": "1.7.0",
        "source_commit": protocol["commit"],
        "started_at": datetime.now(UTC).isoformat(),
        "status": "started",
        "run_class": "full_variant",
        "program_sha256": sha(Path(__file__)),
        "protocol_sha256": sha(args.protocol),
        "protocol_file": (directory / "protocol.json").relative_to(ROOT).as_posix(),
        "archived_program": (directory / "run_program.py").relative_to(ROOT).as_posix(),
        "timing_scope": protocol["common"]["timing"],
        "warmup_steps": 5,
    }
    original_out, original_err = sys.stdout, sys.stderr
    with (directory / "run.log").open("w", encoding="utf-8") as log:
        sys.stdout = Tee(original_out, log)
        sys.stderr = Tee(original_err, log)
        try:
            run(args, case, protocol, directory, result)
        except Exception as exc:
            result.update(status="failed", error=type(exc).__name__ + ": " + str(exc))
            traceback.print_exc()
        finally:
            result["finished_at"] = datetime.now(UTC).isoformat()
            sys.stdout, sys.stderr = original_out, original_err
    save(directory / "result.json", result)
    print(
        "RUN_RESULT "
        + json.dumps(
            {k: result[k] for k in ("run_id", "status", "case_id", "variant")},
            ensure_ascii=False,
        )
        + " "
        + str(directory / "result.json"),
        flush=True,
    )
    if result["status"] not in ("completed", "probe_completed_not_ab"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
