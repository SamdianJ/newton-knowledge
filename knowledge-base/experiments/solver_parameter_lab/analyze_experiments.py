"""Recompute physical metrics from frozen arrays; publish only verified A/B pairs."""

from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )


def rotate(q, vectors):
    # Quaternion-vector product, independently from the runner's matrix formula.
    xyz, w = q[..., :3], q[..., 3:4]
    return vectors + 2 * np.cross(xyz, np.cross(xyz, vectors) + w * vectors)


def recompute(run, arrays):
    pose = arrays["body_q"].astype(float)
    pose[..., 3:] /= np.linalg.norm(pose[..., 3:], axis=-1, keepdims=True)
    velocity = arrays["body_qd"].astype(float)
    top, bottom = [], []
    for i, shape in enumerate(run["visual"]["body_shapes"]):
        if shape["type"] == "sphere":
            extent = np.full(len(pose), shape["radius"])
        else:
            corners = np.array(list(itertools.product((-1, 1), repeat=3))) * np.array(
                shape["half_extents"]
            )
            points = rotate(pose[:, i, None, 3:], corners[None])
            extent = np.max(points[..., 2], axis=1)
        bottom.append(pose[:, i, 2] - extent)
        top.append(pose[:, i, 2] + extent)
    penetration = np.maximum(0, -np.min(bottom, axis=0)) * 1000
    height = np.max(top, axis=0)
    masses = arrays["body_mass"].astype(float)
    inertia = arrays["body_inertia"].astype(float)
    conjugate = pose[..., 3:].copy()
    conjugate[..., :3] *= -1
    omega_body = rotate(conjugate, velocity[..., 3:])
    energy = np.sum(0.5 * masses * np.sum(velocity[..., :3] ** 2, axis=-1), axis=-1)
    energy += 0.5 * np.einsum("tbi,bij,tbj->t", omega_body, inertia, omega_body)
    return penetration, height, energy


def differences(a, b, prefix=""):
    if isinstance(a, dict) and isinstance(b, dict):
        result = []
        for key in sorted(set(a) | set(b)):
            result += differences(
                a.get(key), b.get(key), prefix + ("." if prefix else "") + key
            )
        return result
    return [] if a == b else [{"path": prefix, "A": a, "B": b}]


TITLES = {
    "mujoco_iterations_stack": (
        "MuJoCo · 接触迭代预算",
        "iterations",
        ["newton:1.7.0:mujoco:iterations"],
    ),
    "mujoco_contact_response": (
        "MuJoCo · 接触软化参数组",
        "shape_material_ke + shape_material_kd",
        ["model:mujoco:shape_material_ke", "model:mujoco:shape_material_kd"],
    ),
    "kamino_padmm_budget": (
        "Kamino · PADMM 迭代预算",
        "config.padmm.max_iterations",
        ["newton:1.7.0:kamino:config.padmm.max_iterations"],
    ),
    "kamino_contact_stabilization": (
        "Kamino · 接触位置稳定化",
        "config.constraints.gamma",
        ["newton:1.7.0:kamino:config.constraints.gamma"],
    ),
}


def main():
    protocol = read(ROOT / "planning/p4/protocol.json")
    checks = []

    def check(value, name):
        checks.append({"name": name, "passed": bool(value)})
        if not value:
            raise ValueError(name)

    report, catalog = [], []
    pointer = read(ROOT / "knowledge/current.json")
    records = read(ROOT / pointer["path"] / "records.json")
    for case in protocol["cases"]:
        cid = case["id"]
        variants, replay, arrays_pair = [], [], []
        for variant in ("A", "B"):
            candidates = [
                (p, read(p))
                for p in sorted(
                    (HERE / "runs").glob(cid + "_" + variant + "_*/result.json")
                )
            ]
            candidates = [
                (p, r)
                for p, r in candidates
                if r["status"] == "completed"
                and r["run_class"] == "full_variant"
                and r["protocol_sha256"] == sha(ROOT / "planning/p4/protocol.json")
            ]
            check(
                len(candidates) >= 2,
                cid + variant + " independently repeated full runs",
            )
            path, run = candidates[-1]
            folder = path.parent
            for field, file in [
                ("raw_sha256", "trajectory.npz"),
                ("program_sha256", "run_program.py"),
                ("protocol_sha256", "protocol.json"),
                ("scene_sha256", "scene.json"),
            ]:
                check(sha(folder / file) == run[field], cid + variant + " hash " + file)
            check(
                run["protocol_sha256"] == sha(ROOT / "planning/p4/protocol.json"),
                cid + variant + " frozen protocol",
            )
            check(
                run["source_verification"]["matches_snapshot"],
                cid + variant + " installed source",
            )
            check(
                run["program_sha256"] == sha(HERE / "run_experiments.py"),
                cid + variant + " current reproducible runner",
            )
            with np.load(folder / "trajectory.npz", allow_pickle=False) as data:
                arrays = {k: data[k] for k in data.files}
            prior_path, prior = candidates[-2]
            check(
                sha(ROOT / prior["raw_file"]) == prior["raw_sha256"],
                cid + variant + " repeat raw hash",
            )
            tolerance = protocol["reproduction"]
            with np.load(ROOT / prior["raw_file"], allow_pickle=False) as repeated:
                for field, atol in [
                    ("body_q", tolerance["pose_atol"]),
                    ("body_qd", tolerance["velocity_atol"]),
                ]:
                    check(
                        np.allclose(
                            arrays[field],
                            repeated[field],
                            atol=atol,
                            rtol=tolerance["rtol"],
                        ),
                        cid + variant + " independent process reproduction " + field,
                    )
            gate = protocol["bounded_response_gate"]
            check(
                np.max(np.abs(arrays["body_q"][..., :3]))
                < gate["max_abs_body_center_m"]
                and run["metrics"]["max_speed_m_s"] < gate["max_speed_m_s"]
                and run["metrics"]["max_kinetic_energy_J"]
                < gate["max_kinetic_energy_J"],
                cid + variant + " bounded response, stress runs excluded",
            )
            check(
                all(np.isfinite(a).all() for a in arrays.values()),
                cid + variant + " finite raw arrays",
            )
            check(
                len(arrays["times"]) == run["samples"]
                and np.allclose(
                    np.diff(arrays["times"]), protocol["common"]["dt_seconds"]
                ),
                cid + variant + " sample times",
            )
            p, h, e = recompute(run, arrays)
            for key, curve in [
                ("penetration_mm", p),
                ("stack_height_m", h),
                ("kinetic_energy_J", e),
            ]:
                check(
                    np.allclose(curve, arrays["curve_" + key], rtol=2e-6, atol=2e-5),
                    cid + variant + " independent curve " + key,
                )
            m = run["metrics"]
            tail = p[-max(1, len(p) // 5) :]
            expected = {
                "max_penetration_mm": p.max(),
                "final_penetration_mm": p[-1],
                "tail_penetration_mm": tail.mean(),
                "final_stack_height_m": h[-1],
                "final_kinetic_energy_J": e[-1],
                "max_kinetic_energy_J": e.max(),
                "max_speed_m_s": np.linalg.norm(
                    arrays["body_qd"][..., :3], axis=-1
                ).max(),
                "step_ms_median_after_warmup": np.median(arrays["step_ms"][5:]),
            }
            for field, value in expected.items():
                check(
                    np.isclose(m[field], value, rtol=2e-5, atol=2e-5),
                    cid + variant + " raw metric " + field,
                )
            if case["solver"] == "mujoco":
                check(
                    arrays["native_ncon"].max() > 0,
                    cid + variant + " actual native contacts",
                )
            else:
                for field in ("iterations", "converged", "r_p", "r_d", "r_c"):
                    values = arrays["status_" + field]
                    check(
                        np.isclose(m[field + "_mean"], values.mean()),
                        cid + variant + " backend status " + field,
                    )
            compact = {
                k: run[k]
                for k in (
                    "run_id",
                    "variant",
                    "metrics",
                    "raw_file",
                    "raw_sha256",
                    "program_sha256",
                    "protocol_sha256",
                    "scene_sha256",
                    "environment",
                )
            }
            compact["config"] = {
                "treatment": run["config"]["treatment"],
                "constructor": run["config"]["constructor"],
                "material_values": run["config"]["material_values"],
            }
            compact["resolved_treatment"] = (
                run["resolved_backend"]["iterations"]
                if cid == "mujoco_iterations_stack"
                else run["resolved_backend"]["geom_solref"]
                if cid == "mujoco_contact_response"
                else run["resolved_backend"]["padmm"]["max_iterations"]
                if cid == "kamino_padmm_budget"
                else run["resolved_backend"]["constraints"]["gamma"]
            )
            compact["result_file"] = path.relative_to(ROOT).as_posix()
            compact["reproduction"] = {
                "result_file": prior_path.relative_to(ROOT).as_posix(),
                "run_id": prior["run_id"],
                "raw_sha256": prior["raw_sha256"],
                "tolerances": tolerance,
            }
            variants.append(compact)
            replay.append(
                {
                    "variant": variant,
                    "times": arrays["times"].tolist(),
                    "body_q": arrays["body_q"].tolist(),
                    "visual": run["visual"],
                    "curves": {
                        "penetration_mm": p.tolist(),
                        "height_m": h.tolist(),
                        "energy_J": e.tolist(),
                    },
                }
            )
            arrays_pair.append(arrays)
        check(
            np.array_equal(arrays_pair[0]["body_q"][0], arrays_pair[1]["body_q"][0]),
            cid + " identical initial pose",
        )
        check(
            np.array_equal(arrays_pair[0]["body_qd"][0], arrays_pair[1]["body_qd"][0]),
            cid + " identical initial velocity",
        )
        check(
            np.array_equal(arrays_pair[0]["body_mass"], arrays_pair[1]["body_mass"]),
            cid + " identical masses",
        )
        check(
            variants[0]["resolved_treatment"] != variants[1]["resolved_treatment"],
            cid + " consumed backend treatment",
        )
        check(
            variants[0]["program_sha256"] == variants[1]["program_sha256"]
            and variants[0]["environment"] == variants[1]["environment"],
            cid + " same program/environment",
        )
        a, b = (v["metrics"] for v in variants)
        if cid == "mujoco_iterations_stack":
            observation = f"iterations=5 → 50 时，峰值地面穿透 {a['max_penetration_mm']:.3f} → {b['max_penetration_mm']:.3f} mm；末态最高点 {a['final_stack_height_m']:.6f} → {b['final_stack_height_m']:.6f} m。主要差异出现在接触瞬态，稳定末态差异很小；1 次迭代的失稳压力测试单独归档，不计入有效 A/B。"
        elif cid == "mujoco_contact_response":
            observation = f"ke/kd 共同调整后，峰值穿透 {a['max_penetration_mm']:.3f} → {b['max_penetration_mm']:.3f} mm，尾段穿透 {a['tail_penetration_mm']:.4f} → {b['tail_penetration_mm']:.4f} mm。不能归因于单独 ke；positive solref 的 time constant 还受 refsafe 的 2dt 下限约束。"
        elif cid == "kamino_padmm_budget":
            observation = f"20 → 60 次预算时，峰值地面穿透 {a['max_penetration_mm']:.3f} → {b['max_penetration_mm']:.3f} mm，末态 r_d {a['r_d_final']:.3g} → {b['r_d_final']:.3g}。60 次也并非每步都收敛（比例 {b['converged_mean']:.1%}）；残差与穿透需要同时看。2 次的严重误差运行单独归档。"
        else:
            observation = f"γ=0 时，末态仍重叠 {a['final_penetration_mm']:.3f} mm，但迭代收敛率 {a['converged_mean']:.0%}；γ=0.2 时重叠消退，峰值速度 {b['max_speed_m_s']:.3f} m/s。位置修正与速度约束收敛是不同问题。"
        title, parameter, associations = TITLES[cid]
        source_refs = []
        for rid in associations:
            for ref in records[rid]["source_refs"]:
                if ref not in source_refs:
                    source_refs.append(ref)
        # Freeze full resolved differences separately; summaries contain only treatment.
        runs = [read(ROOT / v["result_file"]) for v in variants]
        diff = differences(runs[0]["config"], runs[1]["config"])
        backend_diff = differences(
            runs[0]["resolved_backend"], runs[1]["resolved_backend"]
        )
        allowed_requested = {
            "mujoco_iterations_stack": {
                "constructor.iterations",
                "treatment.iterations",
            },
            "mujoco_contact_response": {
                "material_values.kd",
                "material_values.ke",
                "model.shape_material_kd",
                "model.shape_material_ke",
                "treatment.kd_rule",
                "treatment.ke",
            },
            "kamino_padmm_budget": {
                "constructor.padmm.max_iterations",
                "treatment.max_iterations",
            },
            "kamino_contact_stabilization": {
                "constructor.constraints.gamma",
                "treatment.gamma",
            },
        }
        allowed_resolved = {
            "mujoco_iterations_stack": {"iterations"},
            "mujoco_contact_response": {"geom_solref"},
            "kamino_padmm_budget": {"padmm.max_iterations"},
            "kamino_contact_stabilization": {"constraints.gamma"},
        }
        check(
            {d["path"] for d in diff} == allowed_requested[cid],
            cid + " only declared requested treatment differs",
        )
        check(
            {d["path"] for d in backend_diff} == allowed_resolved[cid],
            cid + " only declared backend treatment differs",
        )
        save(
            HERE / (cid + "-diff.json"),
            {"requested_diff": diff, "resolved_diff": backend_diff},
        )
        item = {
            "id": cid,
            "record_id": "lab:" + cid,
            "solver": case["solver"],
            "title": title,
            "parameter": parameter,
            "observation": observation,
            "associations": associations,
            "variants": variants,
            "source_refs": source_refs,
            "environment": variants[0]["environment"],
            "viewer_url": "/files/experiments/solver_parameter_lab/index.html?solver="
            + case["solver"]
            + "&case="
            + cid,
            "protocol_file": "planning/p4/protocol.json",
            "diff_file": "experiments/solver_parameter_lab/" + cid + "-diff.json",
            "initial_geometry": [
                {
                    "variant": v["variant"],
                    "body_q": r["body_q"][0],
                    "body_count": len(r["body_q"][0]),
                    "particle_count": 0,
                    "truncated": False,
                }
                for v, r in zip(variants, replay)
            ],
            "limitations": "单个固定场景；每个 A/B 值独立进程运行两次并核对轨迹。无随机重复或统计显著性声明。仅 CPU / 指定后端，不推及 GPU、其他场景或性能排名。",
            "program_source_call": {
                "tool": "get_source",
                "arguments": {
                    "scope": "experiment",
                    "path": "solver_parameter_lab/run_experiments.py",
                    "max_lines": 100,
                },
            },
        }
        fig, axes = plt.subplots(1, 3, figsize=(11, 2.8), constrained_layout=True)
        for axis, key, label in zip(
            axes,
            ("penetration_mm", "height_m", "energy_J"),
            ("Max ground overlap (mm)", "Highest surface (m)", "Kinetic energy (J)"),
        ):
            for v, rep in zip(variants, replay):
                axis.plot(
                    rep["times"],
                    rep["curves"][key],
                    label=v["variant"],
                    color="#087f8c" if v["variant"] == "A" else "#dc6b32",
                )
            axis.set(xlabel="Time (s)", ylabel=label)
            axis.grid(alpha=0.2)
            axis.legend()
        fig.savefig(HERE / (cid + ".svg"), metadata={"Date": None})
        plt.close(fig)
        report.append(
            {
                **item,
                "replay": replay,
                "plot": cid + ".svg",
                "requested_diff": diff,
                "resolved_diff": backend_diff,
            }
        )
        catalog.append(item)
    save(
        HERE / "report-data.json",
        {"version": "1.7.0", "commit": protocol["commit"], "cases": report},
    )
    save(
        HERE / "catalog.json",
        {
            "schema_version": "1.0",
            "phase": "P4",
            "status": "passed",
            "cases": catalog,
            "analyzer_sha256": sha(Path(__file__)),
            "report_sha256": sha(HERE / "report-data.json"),
            "protocol_sha256": sha(ROOT / "planning/p4/protocol.json"),
        },
    )
    save(
        ROOT / "evaluations/p4-physics-validation.json",
        {
            "phase": "P4",
            "status": "passed",
            "passed": len(checks),
            "failed": 0,
            "checks": checks,
            "pairs": len(catalog),
            "runs": sum(len(c["variants"]) for c in catalog),
            "analyzer_sha256": sha(Path(__file__)),
            "catalog_sha256": sha(HERE / "catalog.json"),
        },
    )
    print(json.dumps({"pairs": len(catalog), "runs": 8, "checks": len(checks)}))


if __name__ == "__main__":
    main()
