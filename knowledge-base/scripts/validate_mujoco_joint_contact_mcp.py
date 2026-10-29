"""Verify all measured MuJoCo joint/contact outcomes through an external MCP client."""
from __future__ import annotations

import asyncio
import hashlib
import json
import traceback
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evaluations/mujoco-joint-contact-2026-10-29"
ORIGINAL_FRICTION_CASES = {"mujoco_sliding_friction_mu", "mujoco_torsional_friction_condim"}
NEGATIVE_CASES = ORIGINAL_FRICTION_CASES | {cid + "_stable" for cid in ORIGINAL_FRICTION_CASES}


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


async def main():
    from maintenance import archive_file

    OUT.mkdir(parents=True, exist_ok=True)
    for name in ("mcp-validation.json", "mcp-trace.json", "mcp-partial-trace.json"):
        archive_file(OUT / name, ROOT)
    checks, trace = [], []
    initial_build = load(ROOT / "knowledge/current.json")["build_id"]

    def check(value, name, detail=None):
        item = {"check": name, "passed": bool(value)}
        if detail is not None:
            item["detail"] = detail
        checks.append(item)
        if not value:
            print("FAILED: " + name, flush=True)

    config = load(ROOT / "mcp_service/configs/mcp.json")["mcpServers"]["newton_knowledge"]
    cases = load(ROOT / "experiments/mujoco_joint_contact_lab/catalog.json")["cases"]
    check(len(cases) == 12, "twelve preregistered joint/contact cases available")
    outcomes = {case["id"]: case["physical_acceptance"] for case in cases}
    check(all(outcomes.get(cid) == "failed_criteria" for cid in NEGATIVE_CASES), "all four original and high-impratio friction negative results remain formally published")
    check(sum(status == "passed" for status in outcomes.values()) <= 8, "retrieval does not promote failed physical criteria")
    try:
        async with stdio_client(StdioServerParameters(**config)) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()

                async def call(name, arguments, expected_status="ok"):
                    response = await client.call_tool(name, arguments)
                    body = response.structured_content
                    trace.append({"tool": name, "arguments": arguments, "result": body, "is_error": response.is_error})
                    check(not response.is_error and isinstance(body, dict) and body.get("status") == expected_status, "MCP status " + name + " " + expected_status)
                    check(len(json.dumps(body, ensure_ascii=False)) <= 32000, "bounded MCP response " + name)
                    if isinstance(body, dict) and "build_id" in body:
                        check(body["build_id"] == initial_build, "same publication throughout " + name)
                    return body

                for case in cases:
                    cid, rid = case["id"], case["record_id"]
                    found = await call("search_knowledge", {"query": case["title"], "solver": "mujoco", "kind": "lab_experiment", "limit": 5})
                    hit = next((h for h in found.get("hits", []) if h["id"] == rid), None)
                    check(hit is not None, "title-query discovers new case in top five " + cid)
                    check(all(h["owner_solver"] == "mujoco" and h["record_type"] == "lab_experiment" for h in found.get("hits", [])), "filtered discovery scope " + cid)
                    if hit is None:
                        continue
                    exp = await call(hit["read_next_call"]["tool"], hit["read_next_call"]["arguments"])
                    full = await call("get_experiment", {"experiment_id": cid, "solver": "mujoco", "detail": "full"})
                    expected_accepted = case["physical_acceptance"] == "passed"
                    for label, result in (("summary", exp), ("full", full)):
                        check(result["record"]["owner_solver"] == "mujoco", "read retains solver owner " + cid + " " + label)
                        check(result["experiment"]["physical_acceptance"] == case["physical_acceptance"], "read retains physical outcome " + cid + " " + label)
                        check(result["record"]["coverage"]["experiment_validated"] == expected_accepted, "failed experiment not promoted " + cid + " " + label)
                        check(bool(result.get("scope_note")) and result["experiment"].get("limitations") == case["limitations"], "scope and limitations returned " + cid + " " + label)
                    check("initial_geometry" not in exp["experiment"] and bool(full["experiment"].get("initial_geometry")), "summary/full geometry boundary " + cid)
                    check(exp["view_url"] == case["viewer_url"], "case-specific replay URL " + cid)
                    check(exp["experiment"]["association_relation"] == "measures_behavior_of" and exp["experiment"].get("association_scope"), "association roles remain scoped " + cid)
                    check(exp["record"]["evidence_type"] == "measured" and len(exp["experiment"]["variants"]) == 2, "failed or passed runs remain measured evidence " + cid)
                    for variant in exp["experiment"]["variants"]:
                        expected_variant = next(v for v in case["variants"] if v["variant"] == variant["variant"])
                        check(variant["config"] == expected_variant["config"], "read preserves native configuration and sampling phase " + cid + variant["variant"])
                        repeated = variant["reproduction"]
                        check(variant["run_id"] != repeated["run_id"], "independent repeat accessible " + cid + variant["variant"])
                        for run in (variant, repeated):
                            check(sha(ROOT / run["raw_file"]) == run["raw_sha256"], "read raw fingerprint " + run["run_id"])
                    program_call = exp["program_source_call"]
                    program = await call(program_call["tool"], program_call["arguments"])
                    check(program["sha256"] == case["variants"][0]["program_sha256"] and program["path"] == case["program_source_call"]["arguments"]["path"], "exact archived runner source " + cid)
                    check(program["path"].startswith("mujoco_joint_contact_lab/") and "/runs/" in program["path"], "runner is archived under new lab " + cid)
                    ref = exp["source_refs"][0]
                    source = await call("get_source", {"path": ref["path"], "start_line": ref["line"], "max_lines": 25})
                    check(source["sha256"] == ref["sha256"], "fixed Newton source " + cid)
                    relations = await call("get_relations", {"node_id": rid, "limit": 20})
                    matched = [e for e in relations["edges"] if e["source"] == rid and e["target"] in case["associations"]]
                    check({e["target"] for e in matched} == set(case["associations"]) and all(e["relation"] == "measures_behavior_of" for e in matched), "no direct-parameter claim in graph " + cid)
                    wrong = await call("get_experiment", {"experiment_id": cid, "solver": "kamino"}, expected_status="no_measured_evidence")
                    check("experiment" not in wrong, "negative solver query cannot leak MuJoCo data " + cid)
                document = await call("get_document", {"path": "solvers/mujoco/experiments.md", "max_lines": 200})
                body = document.get("text", "")
                check(all(term in body for term in ("阻尼", "armature", "摩擦", "限位")), "new experiment document exposes results and limits")
    except Exception:
        (OUT / "mcp-partial-trace.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (OUT / "mcp-error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
    check(load(ROOT / "knowledge/current.json")["build_id"] == initial_build, "publication did not change during external-client test")
    failed = sum(not c["passed"] for c in checks)
    report = {"status": "passed" if not failed else "failed", "build_id": initial_build, "passed": len(checks) - failed, "failed": failed, "calls": len(trace), "checks": checks, "scope": "Real stdio reads of twelve MuJoCo joint/contact cases, including four original/high-impratio negative results; physical acceptance is checked against the frozen protocol. Retrieval is a title-query discoverability test, not a semantic recall benchmark. No physics executed."}
    (OUT / "mcp-validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "mcp-trace.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "checks"}, ensure_ascii=False))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
