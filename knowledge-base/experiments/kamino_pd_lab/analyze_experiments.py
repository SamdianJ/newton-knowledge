"""Publish previously saved PD evidence; never run Newton or relax a gate."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
COMMIT = "7e75abe28b8d69522bc0b34837aaed2c303dff5a"
GROUPS = ("convergence", "tracking", "limit_switch")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path):
    return Path(path).relative_to(ROOT).as_posix()


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main():
    checks, cases, unique_runs, selected_results = [], [], {}, set()

    def require(value, name):
        checks.append({"check": name, "passed": bool(value)})
        if not value:
            raise ValueError(name)

    for group in GROUPS:
        directory = HERE / group
        freeze = load(ROOT / "planning/kamino-pd-2026-10-29" / (group + "-freeze.json"))
        protocol = load(directory / "protocol.json")
        require(sha(directory / "protocol.json") == freeze["sha256"], "frozen protocol " + group)
        frozen_at = datetime.fromisoformat(freeze["frozen_at_utc"])
        publication = load(directory / "publication.json")
        analysis = load(directory / "analysis.json")
        require(analysis["status"] in ("passed", "completed_with_failed_criteria"), "completed group analysis " + group)
        require(sha(directory / "analyze.py") == analysis["analyzer_sha256"], "group analyzer fingerprint " + group)
        if publication.get("analysis_sha256"):
            require(sha(directory / "analysis.json") == publication["analysis_sha256"], "publication analysis fingerprint " + group)
        analyzed_results = set()
        def collect_runs(value):
            if isinstance(value, dict):
                if value.get("raw_file"):
                    if value.get("result_file"):
                        analyzed_results.add(value["result_file"])
                    elif value.get("run"):
                        analyzed_results.add(value["run"].rstrip("/") + "/result.json")
                for item in value.values():
                    collect_runs(item)
            elif isinstance(value, list):
                for item in value:
                    collect_runs(item)
        collect_runs(analysis)
        for original in publication["cases"]:
            c = dict(original)
            embedded = c.pop("report", {})
            for key in ("acceptance_results", "analysis_file", "plot"):
                if key not in c and key in embedded:
                    c[key] = embedded[key]
            if isinstance(c["limitations"], list):
                c["limitations"] = "; ".join(c["limitations"])
            require(c["id"] not in {old["id"] for old in cases}, "unique case " + c["id"])
            require(len(c["variants"]) == 2, "two comparable settings " + c["id"])
            c.update(record_id="lab:" + c["id"], solver="kamino", experiment_kind="pd_diagnostics",
                     artifact_root="experiments/kamino_pd_lab/", association_relation="measures_behavior_of",
                     evidence_valid=True, sample_kind="time")
            c["parameter"] = c.get("parameter", c["title"])
            if c["id"] == "kamino_pd_iteration_budget" and publication.get("summary"):
                summary = publication["summary"]
                c["diagnosis_evidence"] = {
                    "interpretation": summary["interpretation"],
                    "representative_step": summary["baseline_representative_steps"][0],
                    "original_strict_convergence_resolved": summary["original_strict_convergence_resolved"],
                    "analysis_file": rel(directory / "analysis.json"),
                }
            c["viewer_url"] = "/files/experiments/kamino_pd_lab/index.html?case=" + c["id"]
            c["replay"], c["initial_geometry"] = [], []
            for variant in c["variants"]:
                samples = []
                for number, saved in enumerate((variant, variant["reproduction"]), 1):
                    raw, result_path = ROOT / saved["raw_file"], ROOT / saved["result_file"]
                    run = load(result_path)
                    require(rel(result_path) in analyzed_results, "selected run independently analyzed " + rel(result_path))
                    require(run["status"] == "completed", "completed run " + rel(result_path))
                    require(sha(raw) == saved["raw_sha256"], "raw fingerprint " + rel(raw))
                    require(run["protocol_sha256"] == freeze["sha256"], "protocol fingerprint " + rel(result_path))
                    require(datetime.fromisoformat(run.get("started_at", run.get("started_at_utc"))) > frozen_at, "protocol precedes run " + rel(result_path))
                    run_dir = result_path.parent
                    require(sha(run_dir / "runner.py") == run["runner_sha256"], "archived runner " + rel(result_path))
                    require(sha(run_dir / "protocol.json") == freeze["sha256"], "archived protocol " + rel(result_path))
                    for path, expected in run.get("files_sha256", {}).items():
                        require(sha(run_dir / path) == expected, "archived evidence " + rel(run_dir / path))
                    with np.load(raw, allow_pickle=False) as arrays:
                        sample = {k: arrays[k].copy() for k in ("body_q", "body_qd", "joint_q", "joint_qd")}
                        t = arrays[next(k for k in ("t", "time", "times") if k in arrays)].copy()
                    require(all(np.isfinite(v).all() for v in sample.values()) and np.isfinite(t).all(), "finite physical arrays " + rel(raw))
                    require(len(sample["body_q"]) == len(t) and np.all(np.diff(t) > 0), "monotonic sample times " + rel(raw))
                    samples.append(sample)
                    selected_results.add(rel(result_path))
                    unique_runs[rel(result_path)] = {"raw_file": rel(raw), "raw_sha256": sha(raw), "runner_sha256": run["runner_sha256"], "protocol_sha256": run["protocol_sha256"]}
                    if number == 1:
                        c["replay"].append({"variant": variant["variant"], "label": variant.get("label", variant["variant"]), "times": t.tolist(), "body_q": sample["body_q"].tolist(), "body_names": ["rotor"], "sample_kind": "time"})
                        c["initial_geometry"].append({"variant": variant["variant"], "body_q": sample["body_q"][0].tolist(), "body_count": sample["body_q"].shape[1], "particle_count": 0, "truncated": False, "full_geometry_artifact": rel(raw)})
                for field in samples[0]:
                    atol = 1e-4 if field.endswith("qd") else 1e-5
                    require(np.allclose(samples[0][field], samples[1][field], atol=atol, rtol=1e-5), "independent repeat " + c["id"] + "/" + variant["variant"] + "/" + field)
            first_dir = (ROOT / c["variants"][0]["result_file"]).parent
            c["runner_file"] = rel(first_dir / "runner.py")
            c["protocol_file"] = rel(first_dir / "protocol.json")
            c["program_source_call"] = {"tool": "get_source", "arguments": {"scope": "experiment", "path": c["runner_file"].removeprefix("experiments/"), "start_line": 1, "max_lines": 80}}
            plot = c["plot"]
            if plot.startswith("experiments/kamino_pd_lab/"):
                plot = plot.removeprefix("experiments/kamino_pd_lab/")
            c["plot"] = plot
            require((HERE / plot).is_file(), "saved plot " + c["id"])
            c["curve_file"] = rel(HERE / plot)
            require(c["physical_acceptance"] in ("passed", "failed_criteria"), "explicit physical verdict " + c["id"])
            require(bool(c["limitations"]) and bool(c["association_scope"]), "scoped interpretation " + c["id"])
            cases.append(c)

    attempts = []
    evidence = {}
    for group in GROUPS:
        for p in sorted((HERE / group).rglob("*")):
            if not p.is_file() or "__pycache__" in p.parts:
                continue
            evidence[rel(p)] = sha(p)
            if p.name == "result.json" and "runs" in p.parts and rel(p) not in selected_results:
                attempts.append({"result_file": rel(p), "status": load(p).get("status"), "reason": "Excluded from formal publication cohort; see group harness-revisions and analysis."})
    report = {"schema_version": "1.0", "version": "1.7.0", "commit": COMMIT, "status": "passed", "status_meaning": "Evidence integrity only; physical and strict/configured convergence verdicts remain separate.", "cases": cases, "checks": checks, "formal_runs": len(unique_runs), "unique_runs": unique_runs, "excluded_harness_attempts": attempts}
    write(HERE / "report-data.json", report)
    compact = []
    for original in cases:
        c = json.loads(json.dumps({k: v for k, v in original.items() if k not in ("replay", "acceptance_results", "plot", "criteria")}))
        for v in c["variants"]:
            env = v.get("environment", {})
            v["environment"] = {k: env[k] for k in ("python", "platform", "packages", "device", "source_commit") if k in env}
            v["environment_file"] = rel((ROOT / v["result_file"]).parent / "environment.json")
            config = v.get("config", {})
            resolved = config.get("resolved", {})
            solver = resolved.get("solver", resolved)
            selected = {k: solver[k] for k in ("dynamics_solver", "integrator", "sparse_jacobian", "sparse_dynamics", "dynamics", "padmm") if k in solver}
            for k in ("joint_target_mode", "joint_effort_limit", "joint_target_ke", "joint_target_kd", "dof_act_paths", "effort_row_count"):
                if k in resolved:
                    selected[k] = resolved[k]
            v["config"] = {"treatment": config.get("treatment", {}), "resolved": selected, "full_config_file": config.get("full_config_file", rel((ROOT / v["result_file"]).parent / "resolved-config.json"))}
            if config.get("protocol_to_api_mapping"):
                v["config"]["protocol_to_api_mapping"] = config["protocol_to_api_mapping"]
            v["reproduction"].pop("checks", None)
        compact.append(c)
    counts = {status: sum(c["physical_acceptance"] == status for c in cases) for status in ("passed", "failed_criteria")}
    catalog = {"schema_version": "1.0", "status": "passed", "status_meaning": report["status_meaning"], "cases": compact, "formal_runs": len(unique_runs), "analyzer_sha256": sha(__file__), "report_sha256": sha(HERE / "report-data.json"), "evidence_files": evidence, "physical_acceptance_counts": counts}
    write(HERE / "catalog.json", catalog)
    body = "# Kamino 有界 PD 诊断与跟踪实验\n\n固定 Newton 1.7.0 / CPU / 单 world；协议先冻结，逐设置独立进程重复两次。\n\n"
    body += f"{len(cases)} 组配对案例，{len(unique_runs)} 次唯一正式运行；收敛诊断组复用同一严格基线，不重复计数。证据完整性 passed 不等于物理或终止条件全部通过。\n\n"
    body += "| 案例 | 物理门槛 | 结果 |\n|---|---|---|\n"
    for c in cases:
        body += f"| [{c['title']}]({c['plot']}) | {c['physical_acceptance']} | {c['observation'].replace('|', '/')} |\n"
    body += "\n## 原始数据、独立参考与复现\n\n[目录](catalog.json)、[完整结果](report-data.json)、[交互曲线与回放](index.html)。仅从保存数组绘制 body 坐标系，不表示碰撞几何。\n\n"
    for group in GROUPS:
        body += f"- [{group} 的场景与标准]({group}/protocol.json)、[结果]({group}/RESULTS.md)、[复现]({group}/REPRODUCE.md)。\n"
    body += "\n重新运行本目录 analyze_experiments.py 仅检查并聚合保存数据，不运行物理。新仿真必须创建新 run 目录，不覆盖原结果。\n\n## 适用边界\n\n"
    for c in cases:
        body += f"- **{c['title']}**：{c['limitations']}\n"
    (HERE / "README.md").write_text(body, encoding="utf-8")
    print(json.dumps({"cases": len(cases), "formal_runs": len(unique_runs), "checks": len(checks), "physical_acceptance": counts, "excluded_attempts": len(attempts)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
