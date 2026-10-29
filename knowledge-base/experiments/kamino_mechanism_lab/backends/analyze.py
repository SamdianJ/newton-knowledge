"""Independently recompute preregistered backend observations from saved arrays."""
import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "manifests/source-lock.json").exists())


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def flatten(obj, prefix=""):
    result = {}
    for k, value in obj.items():
        key = prefix + k
        if isinstance(value, dict) and value:
            result.update(flatten(value, key + "."))
        else:
            result[key] = value
    return result


def evaluate(run, data, protocol):
    scene = protocol["scene"]
    p = data["body_q"][:, 0, :3].astype(np.float64)
    q = data["body_q"][:, 0, 3:].astype(np.float64)
    vel = data["body_qd"][:, 0, :3].astype(np.float64)
    omega = data["body_qd"][:, 0, 3:].astype(np.float64)
    t = data["time"]
    p0, axis, gravity = (np.array(scene[k], dtype=np.float64) for k in ("initial_position_m", "joint_axis", "gravity"))
    acc = float(gravity @ axis)
    expected_p = p0 + 0.5 * acc * t[:, None] ** 2 * axis
    expected_v = acc * t[:, None] * axis
    pre = t <= protocol["reference"]["precontact_window_s"][1] + 1e-12
    tail = t >= protocol["acceptance"]["physical_criteria"]["tail_window_s"][0] - 1e-12
    disp = p - p0
    off_axis = np.linalg.norm(disp - np.outer(disp @ axis, axis), axis=1)
    angle = 2 * np.arccos(np.clip(np.abs(q[:, 3]) / np.linalg.norm(q, axis=1), 0, 1))
    penetration = np.maximum(0, scene["radius_m"] - p[:, 2])
    target_error = np.linalg.norm(p - np.asarray(protocol["reference"]["contact_center_m"]), axis=1)
    energy = 0.5 * scene["mass_kg"] * np.sum(vel * vel, axis=1) + 0.5 * scene["inertia_kg_m2"][0] * np.sum(omega * omega, axis=1) - scene["mass_kg"] * (p @ gravity)
    metrics = {
        "precontact_position_error_max_m": float(np.linalg.norm(p[pre] - expected_p[pre], axis=1).max()),
        "precontact_velocity_error_max_m_s": float(np.linalg.norm(vel[pre] - expected_v[pre], axis=1).max()),
        "off_axis_distance_max_m": float(off_axis.max()),
        "rotation_deviation_max_rad": float(angle.max()),
        "peak_penetration_max_m": float(penetration.max()),
        "tail_contact_center_error_max_m": float(target_error[tail].max()),
        "tail_speed_max_m_s": float(np.linalg.norm(vel[tail], axis=1).max()),
        "energy_growth_over_initial_max_j": float(max(0, (energy - energy[0]).max())),
        "contact_count_max": int(data["contact_count"].max()),
        "contact_steps": int(np.count_nonzero(data["contact_count"])),
        "converged_fraction": float(data["status_converged"].mean()),
        "status_iterations_max": int(data["status_iterations"].max()),
        "r_p_max": float(data["status_r_p"].max()),
        "r_d_max": float(data["status_r_d"].max()),
        "r_c_max": float(data["status_r_c"].max()),
        "final_position_m": p[-1].tolist(),
        "final_velocity_m_s": vel[-1].tolist(),
        "joint_coordinate_geometry_error_max_m": float(np.abs(data["joint_q"][:, 0] - disp @ axis).max()),
    }
    physical = [{"metric": k, "actual": metrics[k], "limit": threshold, "passed": metrics[k] <= threshold} for k, threshold in protocol["acceptance"]["physical_criteria"].items() if k != "tail_window_s"]
    cfg = run["resolved_config"]
    backend = protocol["variants"][run["variant"]]["dynamics_solver"]
    expected_config = (False, True, "LLTB") if backend == "padmm" else (True, False, "LLTBRCM")
    actual_config = (cfg["sparse_jacobian"], cfg["dynamics"]["preconditioning"], cfg["dynamics"]["linear_solver_type"])
    checks = [
        {"check": "completed", "passed": run["status"] == "completed"},
        {"check": "samples and per-step statuses", "passed": len(t) == 145 and len(data["status_iterations"]) == 144 and len(data["contact_count"]) == 144},
        {"check": "raw arrays finite", "passed": all(bool(np.isfinite(v).all()) for v in data.values())},
        {"check": "actual contact active", "passed": metrics["contact_count_max"] > 0},
        {"check": "actual iterations active", "passed": metrics["status_iterations_max"] > 0},
        {"check": "intended backend and dependent config", "passed": cfg["dynamics_solver"] == backend and actual_config == expected_config and cfg["sparse_dynamics"] is False and cfg["integrator"] == "euler"},
    ]
    np.savez_compressed(HERE / (run["run_id"] + "-derived.npz"), time=t, penetration=penetration, guide_error=off_axis, kinetic_plus_potential_energy=energy, center_error=target_error, continuous_reference_position=expected_p, continuous_reference_velocity=expected_v)
    return {"run_id": run["run_id"], "variant": run["variant"], "repeat": run["repeat"], "metrics": metrics, "physical_criteria": physical, "evidence_checks": checks, "physical_passed": all(c["passed"] for c in physical), "evidence_passed": all(c["passed"] for c in checks)}


def main():
    protocol = read(HERE / "protocol.json")
    run_paths = sorted((HERE / "runs").glob("*/result.json"))
    runs = [read(p) for p in run_paths]
    checks, artifacts, loaded, evaluated = [], {}, {}, []
    for path, run in zip(run_paths, runs):
        directory = path.parent
        checks.append({"check": "protocol unchanged " + run["run_id"], "passed": sha(directory / "protocol.json") == run["protocol_sha256"] == sha(HERE / "protocol.json")})
        checks.append({"check": "archived runner intact " + run["run_id"], "passed": sha(directory / "runner.py") == run["runner_sha256"]})
        if run["status"] != "completed":
            checks.append({"check": "no failed run silently discarded " + run["run_id"], "passed": False})
            continue
        raw = ROOT / run["raw_file"]
        checks.append({"check": "raw hash " + run["run_id"], "passed": sha(raw) == run["raw_sha256"]})
        with np.load(raw, allow_pickle=False) as npz:
            data = {k: npz[k].copy() for k in npz.files}
        loaded[(run["variant"], run["repeat"])] = (run, data)
        evaluation = evaluate(run, data, protocol)
        evaluation["result_file"] = path.relative_to(ROOT).as_posix()
        evaluation["raw_file"] = run["raw_file"]
        evaluation["raw_sha256"] = run["raw_sha256"]
        evaluated.append(evaluation)
        for p in directory.iterdir():
            if p.is_file():
                artifacts[p.relative_to(ROOT).as_posix()] = sha(p)
    checks.append({"check": "four independently spawned successful runs", "passed": set(loaded) == {("A", 1), ("A", 2), ("B", 1), ("B", 2)} and len({r["pid"] for r in runs}) == 4})
    repetitions = []
    repeat_tol = protocol["acceptance"]["repeat_tolerance"]
    for variant in ("A", "B"):
        if (variant, 1) not in loaded or (variant, 2) not in loaded:
            continue
        one, two = loaded[(variant, 1)][1], loaded[(variant, 2)][1]
        for field in ("body_q", "body_qd", "joint_q", "joint_qd"):
            repetitions.append({"variant": variant, "field": field, "max_abs_difference": float(np.abs(one[field] - two[field]).max()), "atol": repeat_tol[field + "_atol"], "rtol": repeat_tol["rtol"], "passed": bool(np.allclose(one[field], two[field], atol=repeat_tol[field + "_atol"], rtol=repeat_tol["rtol"]))})
    a, da = loaded[("A", 1)]
    b, db = loaded[("B", 1)]
    for field in ("body_q", "body_qd", "joint_q", "joint_qd"):
        checks.append({"check": "same initial physical state " + field, "passed": bool(np.array_equal(da[field][0], db[field][0]))})
    for field in ("body_mass", "body_inertia"):
        checks.append({"check": "same physical model " + field, "passed": bool(np.array_equal(da[field], db[field]))})
    diffs = {}
    for label in ("requested_config", "resolved_config"):
        aa, bb = flatten(a[label]), flatten(b[label])
        diffs[label] = {k: {"A": aa.get(k), "B": bb.get(k)} for k in sorted(set(aa) | set(bb)) if aa.get(k) != bb.get(k)}
        checks.append({"check": "exact predeclared configuration-group difference " + label, "passed": set(diffs[label]) == set(protocol["allowed_configuration_diff_paths"])})
    save(HERE / "configuration-diff.json", diffs)
    tail = da["time"] >= 0.5 - 1e-12
    pair = {"tail_position_difference_max_m": float(np.linalg.norm(da["body_q"][tail, 0, :3] - db["body_q"][tail, 0, :3], axis=1).max()), "tail_velocity_difference_max_m_s": float(np.linalg.norm(da["body_qd"][tail, 0, :3] - db["body_qd"][tail, 0, :3], axis=1).max()), "all_time_position_difference_max_m": float(np.linalg.norm(da["body_q"][:, 0, :3] - db["body_q"][:, 0, :3], axis=1).max()), "all_time_velocity_difference_max_m_s": float(np.linalg.norm(da["body_qd"][:, 0, :3] - db["body_qd"][:, 0, :3], axis=1).max())}
    pair["narrow_tail_agreement_passed"] = pair["tail_position_difference_max_m"] <= protocol["acceptance"]["tail_pair_position_tolerance_m"] and pair["tail_velocity_difference_max_m_s"] <= protocol["acceptance"]["tail_pair_velocity_tolerance_m_s"]
    evidence_pass = all(c["passed"] for c in checks + repetitions) and all(r["evidence_passed"] for r in evaluated)
    physical_pass = all(r["physical_passed"] for r in evaluated)
    observation = ("两配置组均通过事前物理门槛，且在此单导轨/单接触尾段一致。" if physical_pass and pair["narrow_tail_agreement_passed"] else "存在事前物理门槛或尾段一致性未通过；保留为有效负结果，不能泛化为两后端等价。") + " 配置差异是后端及其依赖默认组；同名残差定义不同，耗时未用于排名。"
    case = {"id": protocol["case_id"], "title": protocol["title"], "solver": "kamino", "protocol_sha256": sha(HERE / "protocol.json"), "variants": evaluated, "metrics": pair, "criteria": protocol["acceptance"], "observation": observation, "limitations": protocol["limitations"], "source_refs": protocol["source_refs"], "evidence_valid": evidence_pass, "physical_criteria_passed": physical_pass, "configuration_differences": diffs, "repeatability": repetitions}
    report = {"status": "passed" if evidence_pass else "failed", "physical_outcome": "passed" if physical_pass else "criteria_failed", "cases": [case], "checks": checks, "runs": [{"run_id": r["run_id"], "status": r["status"], "variant": r["variant"], "repeat": r["repeat"]} for r in runs], "artifacts_sha256": artifacts, "analyzer_sha256": sha(Path(__file__)), "limitations": "Analysis independently derives geometry/continuous reference/energy from NPZ; solver status is logged instrumentation, not a physical oracle. Negative physical results do not invalidate properly collected evidence."}
    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcParams["svg.hashsalt"] = "kamino-backend-guided-contact-v1"
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(11, 7), constrained_layout=True)
    for label, data in (("PADMM", da), ("DVI", db)):
        t = data["time"]
        position = data["body_q"][:, 0, :3]
        displacement = position - np.asarray(protocol["scene"]["initial_position_m"])
        direction = np.asarray(protocol["scene"]["joint_axis"])
        guide = np.linalg.norm(displacement - np.outer(displacement @ direction, direction), axis=1)
        axes[0, 0].plot(t, position[:, 2], label=label)
        axes[0, 1].plot(t, np.linalg.norm(data["body_qd"][:, 0, :3], axis=1), label=label)
        axes[1, 0].semilogy(t, np.maximum(guide, 1e-12), label=label)
        axes[1, 1].semilogy(t[1:], np.maximum(data["status_r_d"], 1e-12), label=label)
    axes[0, 0].axhline(0.1, color="black", linewidth=1, linestyle="--", label="sphere rest center")
    axes[0, 0].set_ylabel("center z [m]")
    axes[0, 1].set_ylabel("speed [m/s]")
    axes[1, 0].set_ylabel("off-axis distance [m]")
    axes[1, 1].set_ylabel("r_d [m/s or rad/s]")
    axes[1, 1].set_title("Backend-specific definitions; not an accuracy ranking", fontsize=9)
    for ax in axes.flat:
        ax.set_xlabel("time [s]")
        ax.grid(alpha=0.25)
        ax.legend()
    fig.suptitle("One inclined prismatic guide + one sphere-floor contact; CPU")
    fig.savefig(HERE / "curves.svg", metadata={"Date": None})
    fig.savefig(HERE / "curves.png", dpi=140)
    plt.close(fig)
    report["plot"] = (HERE / "curves.svg").relative_to(ROOT).as_posix()
    report["plot_sha256"] = sha(HERE / "curves.svg")
    save(HERE / "analysis.json", report)
    print(json.dumps({"status": report["status"], "physical_outcome": report["physical_outcome"], "pair": pair, "variants": [{"variant": r["variant"], "repeat": r["repeat"], "failed_criteria": [c for c in r["physical_criteria"] if not c["passed"]], "metrics": r["metrics"]} for r in evaluated]}, ensure_ascii=False))
    if not evidence_pass:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
