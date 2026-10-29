"""Read-only independent review of archived PADMM iterations; imports no Newton."""
from __future__ import annotations
import ast
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "experiments/kamino_pd_lab/convergence"
OUT = Path(__file__).with_suffix(".json")


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def flatten(obj, prefix=""):
    result = {}
    for k, v in obj.items():
        if isinstance(v, dict):
            result.update(flatten(v, prefix + k + "."))
        else:
            result[prefix + k] = v
    return result


def main():
    p = load(HERE / "protocol.json")
    report = load(HERE / "analysis.json")
    checks, observations, run_summaries, configs, terminals = [], [], [], {}, {}
    lock = load(ROOT / "manifests/source-lock.json")

    def check(name, passed, detail=None):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    check("source lock commit", p["source_commit"] == "7e75abe28b8d69522bc0b34837aaed2c303dff5a")
    source_files = ["newton/_src/solvers/kamino/_src/solvers/padmm/kernels.py", "newton/_src/solvers/kamino/_src/solvers/padmm/math.py"]
    for file in source_files:
        check("fixed source " + file, digest(ROOT / "sources/newton-v1.7.0" / file) == lock["files"][file])
    check("ten archived formal runs", len(report["runs"]) == 10)
    hashes = {}
    for run in report["runs"]:
        label = run["variant"] + "/" + str(run["repeat"])
        folder = ROOT / run["run"]
        result = load(folder / "result.json")
        cfg = load(folder / "resolved-config.json")
        configs[(run["variant"], run["repeat"])] = cfg
        check(label + " immutable files", all(digest(folder / file) == h for file, h in result["files_sha256"].items()))
        check(label + " frozen protocol", result["protocol_sha256"] == digest(HERE / "protocol.json") == digest(folder / "protocol.json"))
        hashes[result["run_id"]] = {"result": digest(folder / "result.json"), "iterations": digest(folder / "iterations.npz"), "trajectory": digest(folder / "trajectory.npz"), "runner": digest(folder / "runner.py")}
        code = (folder / "runner.py").read_text(encoding="utf-8")
        syntax = ast.parse(code)
        observer = next(n for n in ast.walk(syntax) if isinstance(n, ast.FunctionDef) and n.name == "observe")
        calls = [n for n in ast.walk(observer) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id == "self" and n.func.attr == "original"]
        check(label + " delegate exactly once statically", len(calls) == 1)
        # Both retained runner versions copy all recorded views; capacity-only difference is permitted.
        observer_text = ast.get_source_segment(code, observer)
        copied_status = 'initial_status = d.status.numpy()[0].copy()' in observer_text
        copied_pre = any(f'row[name] = getattr(d.state, field).numpy(){suffix}.copy()' in observer_text for suffix in ("", "[active_slice]"))
        copied_post = any(f'row[name] = getattr(d.state, name).numpy(){suffix}.copy()' in observer_text for suffix in ("", "[active_slice]"))
        check(label + " pre/post views explicitly copied", copied_status and copied_pre and copied_post and 'status[name].copy()' in observer_text)
        with np.load(folder / "iterations.npz", allow_pickle=False) as z:
            count = int(z["dim"][0, 0])
            vectors = {"x", "y", "z", "P", "pre_x_p", "pre_y_input", "pre_z_input"}
            i = {k: (z[k][:, :count].copy() if k in vectors else z[k].copy()) for k in z.files}
        with np.load(folder / "trajectory.npz", allow_pickle=False) as z:
            t = {k: z[k].copy() for k in z.files if k != "step_wall_s_including_export"}
        check(label + " six active rows one effort bound", count == 6 and np.all(i["nbc"] == 1) and np.all(i["vio"] == 0))
        x, y, z, scale, xp, yp, zp = [i[k].astype(np.float64) for k in ("x", "y", "z", "P", "pre_x_p", "pre_y_input", "pre_z_input")]
        rho, eta = i["rho"].astype(np.float64), i["eta"].astype(np.float64)
        b = int(i["bcgo"][0, 0])
        lower, upper = i["bound_lower"][:, 0].astype(np.float64), i["bound_upper"][:, 0].astype(np.float64)
        primal_terms = scale * (x - y)
        dual_a, dual_b = eta * (x - xp), rho * (y - yp)
        cp = (x[:, b] - lower) * np.maximum(z[:, b], 0)
        cn = (upper - x[:, b]) * np.maximum(-z[:, b], 0)
        calculated = np.column_stack((np.max(abs(primal_terms), axis=1), np.max(abs((dual_a + dual_b) / scale), axis=1), abs(cp + cn)))
        actual = np.column_stack([i["status_" + k][:, 0] for k in ("r_p", "r_d", "r_c")])
        eps = np.finfo(np.float32).eps
        allowance = 64 * eps * np.column_stack((np.max(scale * (abs(x) + abs(y)), axis=1), np.max((abs(dual_a) + abs(dual_b)) / scale, axis=1), abs(cp) + abs(cn))) + 1e-12
        error = abs(actual - calculated)
        check(label + " independent physical residuals", np.all(error <= allowance), {"max_error": error.max(axis=0).tolist(), "max_allowance_ratio": (error / allowance).max(axis=0).tolist()})
        # z is the updated dual, not the accelerated input or the projected multiplier.
        expected_z = zp + rho * (y - x)
        z_allowance = 8 * eps * (abs(zp) + abs(rho * (y - x))) + 1e-12
        check(label + " dual update from captured pre-state", np.all(abs(z - expected_z) <= z_allowance), float(np.max(abs(z - expected_z))))
        check(label + " pre-x has actual history", np.any(xp != x), int(np.count_nonzero(xp != x)))
        indices, counts, terminal_ids = i["outer_step"], [], []
        valid_sequence = True
        prior_x_valid = True
        for step in range(80):
            rows = np.flatnonzero(indices == step)
            counts.append(len(rows))
            terminal_ids.append(int(rows[-1]))
            valid_sequence &= np.array_equal(i["status_iterations"][rows, 0], np.arange(1, len(rows)+1))
            prior_x_valid &= np.array_equal(i["pre_x_p"][rows[1:]], i["x"][rows[:-1]])
        terminal_ids = np.asarray(terminal_ids)
        check(label + " active iterations contiguous and terminal count", valid_sequence and np.array_equal(counts, t["status_iterations"][1:, 0]), {"total": sum(counts), "min_per_step": min(counts), "max_per_step": max(counts)})
        check(label + " pre-x equals previous saved post-x", prior_x_valid)
        check(label + " terminal status matches trajectory", all(np.array_equal(i["status_" + key][terminal_ids], t["status_" + key][1:]) for key in ("converged", "iterations", "r_p", "r_d", "r_c")))
        configured_eps = np.asarray([cfg["effective_solver"]["padmm"][key] for key in ("primal_tolerance", "dual_tolerance", "compl_tolerance")], dtype=np.float32)
        stopped = (i["status_iterations"][:, 0] > 1) & np.all(actual <= configured_eps, axis=1)
        check(label + " configured stopping Boolean", np.array_equal(stopped, i["status_converged"][:, 0].astype(bool)))
        strict = np.all(actual[terminal_ids] <= np.float32(1e-7), axis=1)
        terminals[(run["variant"], run["repeat"])] = actual[terminal_ids]
        if run["variant"] == "budget1000":
            check(label + " 1000 effective iterations for every step", all(c == 1000 for c in counts), sum(counts))
        if run["variant"] == "baseline":
            with np.load(ROOT / p["legacy_baselines"][run["repeat"]-1] / "trajectory.npz", allow_pickle=False) as old:
                keys = ["body_q", "body_qd", "joint_q", "joint_qd", "joint_lambdas_tau", "applied_body_wrench"]
                maximum = {k: float(np.max(abs(t[k] - old[k]))) for k in keys}
                check(label + " legacy physical observation exact", all(v == 0 for v in maximum.values()), maximum)
                check(label + " legacy post-step status exact", all(np.array_equal(t["status_"+k][1:], old["status_"+k][1:]) for k in ("converged", "iterations", "r_p", "r_d", "r_c")))
        detailed = []
        for step in (0, 1, 39, 40, 41, 79):
            ids = np.flatnonzero(indices == step)[-20:]
            end = ids[-1]
            zero_projection_rc = abs((y[end, b]-lower[end])*max(z[end, b], 0) + (upper[end]-y[end, b])*max(-z[end, b], 0))
            correction = float(rho[end, 0] * (y[end, b] - x[end, b]))
            half_ulp = .5 * abs(float(np.spacing(i["pre_z_input"][end, b])))
            nochange = i["z"][end, b] == i["pre_z_input"][end, b]
            rounded = np.float32(i["pre_z_input"][end, b] + np.float32(correction))
            detailed.append({"step": step, "rc_from_x_J": float(calculated[end, 2]), "counterfactual_rc_from_y_J": float(zero_projection_rc), "x_minus_y": float(x[end,b]-y[end,b]), "z_before": float(zp[end,b]), "z_after": float(z[end,b]), "rho_y_minus_x": correction, "half_ulp_z": half_ulp, "correction_nonzero_below_half_ulp": correction != 0 and abs(correction) < half_ulp, "float32_addition_loses_increment": bool(rounded == i["pre_z_input"][end,b] and correction != 0), "saved_z_unchanged": bool(nochange), "bounded_tail_distinct": len(np.unique(np.column_stack([i[k][ids,b] for k in ("x", "y", "z")]), axis=0)), "rc_tail_range_J": [float(actual[ids,2].min()), float(actual[ids,2].max())]})
        if run["variant"] in ("baseline", "budget1000"):
            check(label + " bounded tail plateau and lost float32 increments", all(d["bounded_tail_distinct"] == 1 and d["float32_addition_loses_increment"] and d["saved_z_unchanged"] and d["counterfactual_rc_from_y_J"] == 0 and d["rc_from_x_J"] > 1e-7 for d in detailed), detailed)
        run_summaries.append({"run_id": result["run_id"], "variant": run["variant"], "repeat": run["repeat"], "configured_converged_fraction": float(stopped[terminal_ids].mean()), "strict_converged_fraction": float(strict.mean()), "terminal_rc_median_J": float(np.median(actual[terminal_ids,2])), "terminal_rc_range_J": [float(actual[terminal_ids,2].min()), float(actual[terminal_ids,2].max())], "active_iterations": sum(counts), "diagnostics": detailed})
    for variant in p["variants"]:
        for repeat in (1, 2):
            for section in ("solver", "effective_solver"):
                base = flatten(configs[("baseline", repeat)][section])
                other = flatten(configs[(variant, repeat)][section])
                diff = {key: [base[key], other[key]] for key in base if base[key] != other[key]}
                check(variant + str(repeat) + " exact intervention " + section, set(diff) == set(p["variants"][variant]["overrides"]), diff)
            if variant == "budget1000":
                check("200 vs 1000 terminal residuals exact repeat" + str(repeat), np.array_equal(terminals[("baseline", repeat)], terminals[(variant, repeat)]))
    observations = [
        "Source computes complementarity from unprojected x and newly updated z, not projected y. Replacing x with y would erase the bounded-row residual in the sampled plateau and is not the implemented stopping criterion.",
        "P*x is physical generalized impulse and z/P is physical constraint velocity; their product and bound product have energy units J. Translational/rotational residual components otherwise mix their corresponding units; rc is not a torque error.",
        "Copied pre/post arrays, contiguous active iteration counters, exact legacy post-step physics/status equality and independently reconstructed residuals reject the specific view-alias/observation explanation for the selected baseline evidence.",
        "Every budget1000 step performed 1000 active iterations. Its terminal residuals exactly equal baseline200, supporting a persistent plateau in this scene, not a claim that arbitrarily many iterations can never help.",
        "Only compl_tolerance is relaxed in compl1e6. Configured convergence and original strict convergence must be reported separately; relaxed termination does not solve the original strict residual gate.",
        "Selected baseline and1000 tails have fixed bounded x/y/z, nonzero correction below half a float32 ULP of z, and an unchanged rounded z. This directly supports local float32 quantization/stagnation consistency. No matched float64 solver was run, so the evidence does not prove a universal precision floor or rule out other algorithms/configurations."
    ]
    failed = [c for c in checks if not c["passed"]]
    output = {"status": "passed" if not failed else "failed", "reviewer": "independent limit-switch agent", "scope": "Read-only raw/source review; no simulation and no import of target analyzer", "script_sha256": digest(__file__), "analysis_sha256": digest(HERE / "analysis.json"), "protocol_sha256": digest(HERE / "protocol.json"), "passed": len(checks)-len(failed), "failed": len(failed), "checks": checks, "run_summaries": run_summaries, "observations": observations, "input_hashes": hashes, "limits": "No matched high-precision implementation, no contact/GPU/multiworld generalization, no performance comparison."}
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps({"status": output["status"], "passed": output["passed"], "failed": output["failed"], "failed_names": [c["name"] for c in failed]}))


if __name__ == "__main__":
    main()
