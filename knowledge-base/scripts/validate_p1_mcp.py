"""Exercise migration compatibility through an actual external stdio client."""

import asyncio
import json
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
checks = []
trace = []


def check(value, label):
    checks.append({"check": label, "passed": bool(value)})
    if not value:
        print("FAILED: " + label)


async def main():
    config = json.loads(
        (ROOT / "mcp_service/configs/mcp.json").read_text(encoding="utf-8")
    )["mcpServers"]["newton_knowledge"]
    baseline = json.loads(
        (ROOT / "planning/p0/migration-baseline.json").read_text(encoding="utf-8")
    )
    pointer = json.loads((ROOT / "knowledge/current.json").read_text(encoding="utf-8"))
    records = json.loads(
        (ROOT / pointer["path"] / "records.json").read_text(encoding="utf-8")
    )
    async with stdio_client(StdioServerParameters(**config)) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=30) as session:
            init = await session.initialize()
            check(
                init.server_info.name == "newton_knowledge", "actual stdio initialize"
            )
            tools = await session.list_tools()
            specs = {t.name: t.model_dump(by_alias=True) for t in tools.tools}
            contract = json.loads(
                (ROOT / "planning/p0/mcp-contract.json").read_text(encoding="utf-8")
            )
            check(
                set(specs) == set(contract["tools"]), "exactly six tool names preserved"
            )
            for name, spec in specs.items():
                check(
                    spec["inputSchema"] == contract["tools"][name]["inputSchema"],
                    "strict published input schema: " + name,
                )

            async def call(name, args, expect_error=False):
                response = await session.call_tool(name, args)
                data = response.structured_content
                trace.append(
                    {
                        "tool": name,
                        "arguments": args,
                        "is_error": bool(response.is_error),
                        "result": data,
                    }
                )
                check(
                    bool(response.is_error) == expect_error,
                    "protocol result " + name + " " + str(args)[:160],
                )
                if not expect_error:
                    check(
                        data and data.get("build_id") == pointer["build_id"],
                        "same build " + name,
                    )
                return data

            for rid in baseline["parameter_ids"]:
                record = records[rid]
                solver = record["owner_solver"]
                name = record["payload"].get("name")
                result = await call("get_parameter", {"name": name, "solver": solver})
                check(
                    result.get("status") == "ok"
                    and result.get("parameter", {}).get("id") == rid,
                    "legacy exact parameter: " + rid,
                )
                if name == "iterations" and solver in ("vbd", "mujoco"):
                    check(
                        result["parameter"]["declared_default_expression"]
                        == record["payload"]["declared_default_expression"],
                        "scoped default " + solver,
                    )
            for doc in baseline["documents"]:
                result = await call(
                    "get_document", {"path": doc["path"], "max_lines": 4}
                )
                check(
                    result["status"] == "ok" and bool(result["text"]),
                    "legacy readable document " + doc["path"],
                )
            for experiment in baseline["experiments"]:
                result = await call(
                    "get_experiment", {"experiment_id": experiment["case_id"]}
                )
                check(
                    result["status"] == "ok"
                    and len(result["experiment"]["variants"]) == 2,
                    "legacy measured A/B " + experiment["case_id"],
                )
            for name in (
                "tri_ke",
                "tri_ka",
                "tri_ke + tri_ka",
                "edge_ke",
                "contact_ke",
                "contact_mu",
                "full_surface",
                "enable_rigid_soft_full_surface_contact",
                "substeps",
            ):
                result = await call("get_parameter", {"name": name})
                check(
                    result["status"] == "ok",
                    "legacy explicit group / process alias " + name,
                )
                check(
                    result["resolved_scope"]["scope_resolution"] == "legacy_default",
                    "omitted solver visible " + name,
                )
            for solver in (
                "vbd",
                "mujoco",
                "kamino",
                "featherstone",
                "implicit-mpm",
                "semi-implicit",
                "style3d",
                "xpbd",
            ):
                result = await call(
                    "search_knowledge",
                    {"query": "Solver", "solver": solver, "limit": 5},
                )
                check(
                    result["hits"]
                    and all(h["owner_solver"] == solver for h in result["hits"]),
                    "no hidden VBD fallback " + solver,
                )
            for solver in ("mujoco", "kamino", "xpbd"):
                result = await call(
                    "get_experiment",
                    {"solver": solver, "experiment_id": "full_surface"},
                )
                check(
                    result["status"] == "no_measured_evidence",
                    "missing run cannot borrow VBD " + solver,
                )
            result = await call(
                "get_relations",
                {
                    "node_id": "pipeline:enable_rigid_soft_full_surface_contact",
                    "limit": 30,
                },
            )
            check(
                any(n["id"] == "lab:full_surface" for n in result["neighbors"]),
                "shared parameter links measured VBD evidence",
            )
            source = await call(
                "get_source",
                {"symbol_id": "symbol:newton.ModelBuilder.add_urdf", "max_lines": 8},
            )
            check(
                source["verification"] == "verified_snapshot"
                and source["sha256"] == source["manifest_sha256"],
                "symbol reader verifies full pinned source manifest",
            )
            await call(
                "search_knowledge",
                {"query": "contact", "unknown_filter": "ignored?"},
                True,
            )
            await call("search_knowledge", {"query": "contact", "stage": "bogus"}, True)
    failed = sum(not c["passed"] for c in checks)
    report = {
        "phase": "P1",
        "status": "passed" if not failed else "failed",
        "build_id": pointer["build_id"],
        "passed": len(checks) - failed,
        "failed": failed,
        "calls": len(trace),
        "checks": checks,
    }
    (ROOT / "evaluations/p1-mcp-trace.json").write_text(
        json.dumps(trace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (ROOT / "evaluations/p1-mcp-validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in report.items() if k != "checks"}))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
