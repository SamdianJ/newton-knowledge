"""Read every new physical case via an external stdio MCP client."""

import asyncio
import hashlib
import json
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def main():
    from maintenance import archive_file

    for name in ("p4-mcp-validation.json", "p4-mcp-trace.json"):
        archive_file(ROOT / "evaluations" / name, ROOT)
    checks, trace = [], []

    def check(value, name):
        checks.append({"name": name, "passed": bool(value)})

    config = json.loads((ROOT / "mcp_service/configs/mcp.json").read_text())[
        "mcpServers"
    ]["newton_knowledge"]
    cases = json.loads(
        (ROOT / "experiments/solver_parameter_lab/catalog.json").read_text(
            encoding="utf-8"
        )
    )["cases"]
    async with stdio_client(StdioServerParameters(**config)) as (read, write):
        async with ClientSession(read, write) as client:
            await client.initialize()

            async def call(name, args):
                result = await client.call_tool(name, args)
                body = result.structured_content
                trace.append({"tool": name, "arguments": args, "result": body})
                check(
                    not result.is_error and body["status"] == "ok", "successful " + name
                )
                check(
                    len(json.dumps(body, ensure_ascii=False)) <= 32000,
                    "bounded " + name,
                )
                return body

            for case in cases:
                solver, cid = case["solver"], case["id"]
                found = await call(
                    "search_knowledge",
                    {
                        "query": case["parameter"],
                        "solver": solver,
                        "kind": "lab_experiment",
                        "limit": 5,
                    },
                )
                hit = next(
                    (h for h in found["hits"] if h["id"] == case["record_id"]), None
                )
                check(hit is not None, "discover actual experiment " + cid)
                check(
                    all(h["owner_solver"] == solver for h in found["hits"]),
                    "scope " + cid,
                )
                if not hit:
                    continue
                exp = await call(
                    hit["read_next_call"]["tool"], hit["read_next_call"]["arguments"]
                )
                full = await call(
                    "get_experiment",
                    {"experiment_id": cid, "solver": solver, "detail": "full"},
                )
                check(
                    "initial_geometry" not in exp["experiment"]
                    and "initial_geometry" in full["experiment"],
                    "summary/full " + cid,
                )
                check(
                    exp["record"]["evidence_type"] == "measured"
                    and len(exp["experiment"]["variants"]) == 2,
                    "real A/B " + cid,
                )
                check(exp["view_url"] == case["viewer_url"], "exact replay " + cid)
                for variant in exp["experiment"]["variants"]:
                    check(
                        hashlib.sha256(
                            (ROOT / variant["raw_file"]).read_bytes()
                        ).hexdigest()
                        == variant["raw_sha256"],
                        "raw hash " + variant["run_id"],
                    )
                    check(
                        variant["reproduction"]["run_id"] != variant["run_id"],
                        "independent reproduction " + variant["run_id"],
                    )
                for rid in case["associations"]:
                    p = await call(
                        "get_parameter", {"record_id": rid, "solver": solver}
                    )
                    check(
                        p["experiment_status"] == "measured"
                        and case["record_id"] in {e["id"] for e in p["experiments"]},
                        "parameter association " + rid,
                    )
                rel = await call(
                    "get_relations", {"node_id": case["record_id"], "limit": 20}
                )
                check(
                    set(case["associations"]) <= {e["target"] for e in rel["edges"]},
                    "graph group relation " + cid,
                )
                src = await call(
                    exp["program_source_call"]["tool"],
                    exp["program_source_call"]["arguments"],
                )
                check(
                    src["sha256"] == case["variants"][0]["program_sha256"],
                    "frozen runner source " + cid,
                )
                ref = exp["source_refs"][0]
                source = await call(
                    "get_source",
                    {"path": ref["path"], "start_line": ref["line"], "max_lines": 30},
                )
                check(
                    source["sha256"] == ref["sha256"], "Newton definition source " + cid
                )
    failed = sum(not c["passed"] for c in checks)
    build_id = json.loads((ROOT / "knowledge/current.json").read_text())["build_id"]
    report = {
        "phase": "P4",
        "status": "passed" if not failed else "failed",
        "build_id": build_id,
        "passed": len(checks) - failed,
        "failed": failed,
        "calls": len(trace),
        "checks": checks,
    }
    (ROOT / "evaluations/p4-mcp-validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (ROOT / "evaluations/p4-mcp-trace.json").write_text(
        json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in report.items() if k != "checks"}))
    if failed:
        print([c for c in checks if not c["passed"]])
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
