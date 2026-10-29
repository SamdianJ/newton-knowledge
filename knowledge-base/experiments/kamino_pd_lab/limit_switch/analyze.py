"""Score immutable switching runs with a solver-independent scalar PD reference."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "manifests/source-lock.json").exists())


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def maxabs(a):
    return float(np.max(np.abs(a)))


def reference(protocol, variant):
    """Independent I=1 scalar implicit optimality solution, no Newton imports."""
    n = protocol["run"]["steps"]
    h = protocol["run"]["dt_s"]
    kp = protocol["scene"]["kp_Nm_per_rad"]
    kd = protocol["scene"]["kd_Nms_per_rad"]
    q, v = np.zeros(n + 1), np.zeros(n + 1)
    free, tau, limits, targets = (np.zeros(n) for _ in range(4))
    for k in range(n):
        phase = k // protocol["run"]["phase_steps"]
        limits[k] = protocol["case"]["variants"][variant]["limits_Nm"][phase]
        targets[k] = protocol["run"]["target_q_rad"][phase]
        free[k] = (kp * (targets[k] - q[k]) - (kd + h * kp) * v[k]) / (1 + h * kd + h * h * kp)
        tau[k] = np.clip(free[k], -limits[k], limits[k])
        v[k + 1] = v[k] + h * tau[k]
        q[k + 1] = q[k] + h * v[k + 1]
    return {"joint_q": q, "joint_qd": v, "effort": tau, "free_effort": free, "limits": limits, "target_q": targets}


def main():
    protocol = load(HERE / "protocol.json")
    ph, rh = sha(HERE / "protocol.json"), sha(HERE / "runner.py")
    gates = protocol["criteria"]
    selected, excluded = [], []
    for file in sorted((HERE / "runs").glob("*/result.json")):
        result = load(file)
        if result["status"] == "completed" and result["protocol_sha256"] == ph and result["runner_sha256"] == rh:
            selected.append((file.parent, result))
        else:
            excluded.append({"run": file.parent.relative_to(ROOT).as_posix(), "status": result["status"], "runner_sha256": result["runner_sha256"], "reason": result.get("error", "non-current protocol or runner")})
    if len(selected) != 4 or {(r["variant"], r["repeat"]) for _, r in selected} != {("A", 1), ("A", 2), ("B", 1), ("B", 2)}:
        raise ValueError("Expected exactly four completed runs: A/B by repeats 1/2; failures remain in runs")
    cases, records, raw = [], {}, {}
    checks = []

    def check(name, actual, expected, passed):
        checks.append({"name": name, "actual": actual, "expected": expected, "passed": bool(passed)})

    check("frozen design", sha(HERE / "DESIGN.md"), protocol["design_sha256"], sha(HERE / "DESIGN.md") == protocol["design_sha256"])

    for path, result in selected:
        variant, repeat = result["variant"], result["repeat"]
        data = dict(np.load(path / "trajectory.npz", allow_pickle=False))
        cfg, events = load(path / "resolved-config.json"), load(path / "events.json")
        src = load(path / "installed-source-validation.json")
        ref = reference(protocol, variant)
        raw[(variant, repeat)] = data
        first = len(checks)
        prefix = result["run_id"] + ": "
        metrics = {}

        def upper(name, value, maximum):
            metrics[name] = value
            check(prefix + name, value, {"max": maximum}, value <= maximum)

        check(prefix + "archived files", len(result["files_sha256"]), "all hashes match", all(sha(path / k) == h for k, h in result["files_sha256"].items()))
        check(prefix + "source tree", src["checked_python_files"], 809, src["checked_python_files"] == 809 and not src["changed"] and not src["missing"])
        finite = all(np.isfinite(a[1:] if k.startswith("status_") else a).all() for k, a in data.items())
        check(prefix + "finite arrays", bool(finite), True, finite)
        check(prefix + "time grid", len(data["t"]), 121, len(data["t"]) == 121 and np.allclose(data["t"], np.arange(121) * .005, atol=1e-14, rtol=0))
        check(prefix + "model contract", cfg["body_com"], "mass1 COM0 Iidentity POSITION kp20 kd2", cfg["body_mass"] == [1.] and cfg["body_com"] == [[0., 0., 0.]] and np.allclose(cfg["body_inertia"], np.eye(3)[None]) and cfg["joint_target_ke"] == [20.] and cfg["joint_target_kd"] == [2.])
        q, v = data["joint_q"][:, 0], data["joint_qd"][:, 0]
        tau = data["joint_lambdas_tau"][1:, 0]
        wrench = data["applied_body_wrench"][1:, 0, 4]
        h = protocol["run"]["dt_s"]
        upper("angle_reference_rad", maxabs(q - ref["joint_q"]), gates["angle_reference_rad"])
        upper("speed_reference_rad_s", maxabs(v - ref["joint_qd"]), gates["speed_reference_rad_s"])
        upper("effort_reference_Nm", maxabs(tau - ref["effort"]), gates["effort_reference_Nm"])
        upper("wrench_reference_Nm", maxabs(wrench - ref["effort"]), gates["effort_reference_Nm"])
        upper("effort_bound_excess_Nm", float(np.maximum(np.abs(tau) - ref["limits"], 0).max()), gates["effort_bound_excess_Nm"])
        upper("wrench_bound_excess_Nm", float(np.maximum(np.abs(wrench) - ref["limits"], 0).max()), gates["effort_bound_excess_Nm"])
        upper("bound_impulse_error_Nms", maxabs(data["step_bound_after_step"][:, 0] - h * ref["limits"]), gates["bound_impulse_error_Nms"])
        upper("integration_residual_rad", maxabs(np.diff(q) - h * v[1:]), gates["integration_residual_rad"])
        upper("momentum_residual_Nm", maxabs(np.diff(v) / h - tau), gates["momentum_residual_Nm"])
        upper("body_momentum_residual_Nm", maxabs(np.diff(data["body_qd"][:, 0, 4]) / h - wrench), gates["momentum_residual_Nm"])
        upper("anchor_drift_m", float(np.linalg.norm(data["body_q"][:, 0, :3], axis=1).max()), gates["anchor_drift_m"])
        notify_deltas = [max(e["notify_state_max_abs"].values()) for e in events]
        upper("notify_state_change", max(notify_deltas), gates["notify_state_change"])
        check(prefix + "command limit", data["step_command_limit"].tolist(), ref["limits"].tolist(), np.array_equal(data["step_command_limit"], ref["limits"]))
        check(prefix + "actual model limit", data["step_model_limit_after_step"][:, 0].tolist(), "equal to command at every step", np.array_equal(data["step_model_limit_after_step"][:, 0], ref["limits"]))
        check(prefix + "preserved effort row", cfg["dof_act_paths"], [2], cfg["dof_act_paths"] == [2] and cfg["effort_row_count"] == 1 and all(e["path_before"] == e["path_after"] == e["path_after_step"] == [2] and e["effort_row_count"] == 1 for e in events))
        expected_edges = [20, 40, 80, 100] if variant == "A" else []
        actual_edges = [e["step_index"] for e in events if e["notify_called"]]
        check(prefix + "public notify precedes step", actual_edges, expected_edges, actual_edges == expected_edges and all(e["sequence"].index("notify") < e["sequence"].index("step") for e in events if e["notify_called"]))
        stale = sum(abs(tau[k] - ref["effort"][k]) > gates["effort_reference_Nm"] for k in expected_edges)
        upper("stale_limit_steps", int(stale), gates["stale_limit_steps"])
        if variant == "A":
            for phase, expected in enumerate(protocol["branch_expectation_A"]):
                sl = slice(phase * 20, (phase + 1) * 20)
                sign = 1 if expected.startswith("positive") else -1
                saturated = not expected.endswith("unsaturated")
                if saturated:
                    actual = maxabs(tau[sl] - sign * ref["limits"][sl])
                    passed = actual <= gates["effort_reference_Nm"] and np.all(sign * ref["free_effort"][sl] > ref["limits"][sl])
                else:
                    actual = float((ref["limits"][sl] - np.abs(tau[sl])).min())
                    passed = actual >= gates["unsaturated_margin_Nm"] and np.all(sign * tau[sl] > 0)
                check(prefix + f"phase{phase} {expected}", actual, "all 20 steps in preregistered branch", passed)
        metrics["status_converged_fraction"] = float(data["status_converged"][1:].mean())
        metrics["status_max_iterations"] = int(data["status_iterations"][1:].max())
        metrics["status_residual_maxima"] = {k: float(data["status_" + k][1:].max()) for k in ("r_p", "r_d", "r_c")}
        metrics["status_by_phase"] = [{"phase": p, "converged_fraction": float(data["status_converged"][1 + 20 * p:1 + 20 * (p + 1)].mean())} for p in range(6)]
        metrics["phase_observations"] = [{"phase": p, "target_rad": float(ref["target_q"][20*p]), "limit_Nm": float(ref["limits"][20*p]), "reference_free_effort_range_Nm": [float(ref["free_effort"][20*p:20*(p+1)].min()), float(ref["free_effort"][20*p:20*(p+1)].max())], "actual_effort_range_Nm": [float(tau[20*p:20*(p+1)].min()), float(tau[20*p:20*(p+1)].max())]} for p in range(6)]
        records[(variant, repeat)] = {"result": result, "path": path, "metrics": metrics, "checks": checks[first:]}
    for variant in ("A", "B"):
        a, b = raw[(variant, 1)], raw[(variant, 2)]
        for key, atol in (("body_q", 1e-5), ("body_qd", 1e-4), ("joint_q", 1e-5), ("joint_qd", 1e-4), ("joint_lambdas_tau", .002), ("applied_body_wrench", .002)):
            check(variant + " independent repeat " + key, maxabs(a[key] - b[key]), {"atol": atol, "rtol": 1e-5}, np.allclose(a[key], b[key], atol=atol, rtol=1e-5))
    accepted = all(c["passed"] for c in checks)
    outcome = "passed" if accepted else "failed_criteria"
    observation = "已按公开通知契约完成正反力限切换，" + ("全部预设物理门槛通过。" if accepted else "存在未通过的预设物理门槛，保留负结果。") + "物理门槛与严格 PADMM 收敛诊断分开记录。"
    max_effort_error = max(r["metrics"]["effort_reference_Nm"] for r in records.values())
    diagnostic_fraction = [records[(v, 1)]["metrics"]["status_converged_fraction"] for v in ("A", "B")]
    observation += f" 最大力矩参考误差 {max_effort_error:.3g} N·m；A 每次切换在同一步采用新限值，状态在通知前后不跳变；A/B 收敛标记比例 {diagnostic_fraction[0]:.0%}/{diagnostic_fraction[1]:.0%}，仅适用于本小驱动场景，不覆盖旧高增益场景。"
    variant_outputs = []
    for variant in ("A", "B"):
        primary, repeated = records[(variant, 1)], records[(variant, 2)]
        def metadata(entry):
            p, r = entry["path"], entry["result"]
            return {"run_id": r["run_id"], "raw_file": (p / "trajectory.npz").relative_to(ROOT).as_posix(), "raw_sha256": sha(p / "trajectory.npz"), "program_sha256": r["runner_sha256"], "protocol_sha256": r["protocol_sha256"], "result_file": (p / "result.json").relative_to(ROOT).as_posix()}
        output = metadata(primary)
        output.update(variant=variant, label=protocol["case"]["variants"][variant]["label"], metrics=primary["metrics"], config={"treatment": protocol["case"]["variants"][variant], "resolved": load(primary["path"] / "resolved-config.json"), "full_config_file": (primary["path"] / "resolved-config.json").relative_to(ROOT).as_posix()}, environment=load(primary["path"] / "environment.json"), reproduction=metadata(repeated))
        output["reproduction"]["tolerances"] = {"q_atol": 1e-5, "qd_atol": 1e-4, "effort_atol": .002, "rtol": 1e-5}
        variant_outputs.append(output)
    case = {"id": protocol["case"]["id"], "record_id": "lab:" + protocol["case"]["id"], "solver": "kamino", "title": "有界隐式 PD：有限正力限切换、释放与重新饱和", "parameter": "joint_effort_limit notify_model_changed POSITION", "observation": observation, "physical_acceptance": outcome, "limitations": protocol["limitations"] + " Strict convergence statistics are diagnostics and may fail even if physical gates pass.", "source_refs": protocol["source_refs"], "associations": ["model:kamino:joint_effort_limit"], "association_relation": "measures_behavior_of", "association_scope": "Only finite positive effort limit is varied via public notify; gains, mode, solver budget and timestep fixed. No zero/infinite or route-allocation change coverage.", "variants": variant_outputs, "protocol_file": (records[("A", 1)]["path"] / "protocol.json").relative_to(ROOT).as_posix(), "runner_file": (records[("A", 1)]["path"] / "runner.py").relative_to(ROOT).as_posix(), "criteria": gates, "acceptance_results": checks}
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(12, 7), constrained_layout=True)
    for variant in ("A", "B"):
        d = raw[(variant, 1)]
        ref = reference(protocol, variant)
        axes[0, 0].plot(d["t"][1:], d["joint_lambdas_tau"][1:, 0], label=variant + " measured")
        axes[0, 0].plot(d["t"][1:], ref["effort"], "--", label=variant + " reference")
        axes[0, 1].plot(d["t"], d["joint_q"][:, 0], label=variant)
        axes[1, 0].plot(d["t"], d["joint_qd"][:, 0], label=variant)
        axes[1, 1].semilogy(d["t"][1:], np.maximum(d["status_r_c"][1:, 0], 1e-12), label=variant)
    axes[0, 0].step(raw[("A", 1)]["t"][1:], reference(protocol, "A")["limits"], where="post", alpha=.5, label="A limit")
    axes[0, 0].step(raw[("A", 1)]["t"][1:], -reference(protocol, "A")["limits"], where="post", alpha=.5, linestyle=":", label="A negative limit")
    axes[0, 1].step(raw[("A", 1)]["t"][1:], reference(protocol, "A")["target_q"], where="post", linestyle=":", label="target")
    axes[1, 1].axhline(1e-7, color="red", linestyle=":", label="strict criterion")
    for ax, label in zip(axes.flat, ("Effort [N m]", "Angle [rad]", "Speed [rad/s]", "Complementarity residual [J]")):
        ax.set(xlabel="Time [s]", ylabel=label)
        ax.legend()
        ax.grid(alpha=.3)
        for boundary in (.1, .2, .3, .4, .5):
            ax.axvline(boundary, color="gray", alpha=.15, linewidth=.7)
    axes[0, 0].legend(loc="lower left", fontsize=8, ncol=2)
    fig.savefig(HERE / "limit-switch.svg", metadata={"Date": None})
    fig.savefig(HERE / "limit-switch.png", dpi=140)
    plt.close(fig)
    case["plot"] = "limit_switch/limit-switch.svg"
    case["replay"] = [{"variant": v, "label": protocol["case"]["variants"][v]["label"], "times": raw[(v, 1)]["t"].tolist(), "body_q": raw[(v, 1)]["body_q"].tolist(), "body_names": ["rotor"]} for v in ("A", "B")]
    report = {"status": outcome, "physics_accepted": accepted, "formal_runs": 4, "passed_checks": sum(c["passed"] for c in checks), "failed_checks": sum(not c["passed"] for c in checks), "protocol_sha256": ph, "runner_sha256": rh, "analyzer_sha256": sha(__file__), "excluded_attempts": excluded, "cases": [case]}
    save(HERE / "analysis.json", report)
    save(HERE / "publication.json", {"cases": [case], "formal_runs": [r["run_id"] for _, r in selected]})
    text = f"# Finite effort-limit switching results\n\nPhysical acceptance: **{outcome}**; {report['passed_checks']} checks passed, {report['failed_checks']} failed. Four independent processes.\n\n{observation}\n\n"
    for variant in ("A", "B"):
        for repeat in (1, 2):
            m = records[(variant, repeat)]["metrics"]
            text += f"- {variant} repeat {repeat}: effort max error {m['effort_reference_Nm']:.8g} N m; angle {m['angle_reference_rad']:.8g} rad; speed {m['speed_reference_rad_s']:.8g} rad/s; stale-limit steps {m['stale_limit_steps']}; convergence {m['status_converged_fraction']:.1%}, max iterations {m['status_max_iterations']}.\n"
    text += "\nConvergence is reported separately; physical acceptance is not a claim that strict stopping diagnostics pass.\n\n" + protocol["limitations"] + "\n"
    (HERE / "RESULTS.md").write_text(text, encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("status", "formal_runs", "passed_checks", "failed_checks")}))


if __name__ == "__main__":
    main()
