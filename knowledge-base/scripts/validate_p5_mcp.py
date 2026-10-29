"""Legacy consumers and provenance through actual stdio, using current content."""

import asyncio
import json
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def main():
    from maintenance import archive_file

    for name in ["p5-mcp-validation.json", "p5-mcp-trace.json"]:
        archive_file(ROOT / "evaluations" / name, ROOT)
    checks = []
    trace = []

    def check(value, name):
        checks.append({"name": name, "passed": bool(value)})

    config = json.loads((ROOT / "mcp_service/configs/mcp.json").read_text())[
        "mcpServers"
    ]["newton_knowledge"]
    config["env"] = {
        **config.get("env", {}),
        "NEWTON_KB_SITE_URL": "http://127.0.0.1:18448",
    }
    async with stdio_client(StdioServerParameters(**config)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(tool, args):
                result = await session.call_tool(tool, args)
                data = result.structured_content
                trace.append({"tool": tool, "arguments": args, "result": data})
                check(
                    not result.is_error and data["status"] == "ok",
                    "call success " + tool + " " + str(args),
                )
                check(
                    bool(data.get("knowledge_built_at")) and bool(data.get("solver")),
                    "legacy envelope " + tool,
                )
                check(
                    len(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
                    <= 32000,
                    "bounded aliases " + tool,
                )
                return data

            found = await call(
                "search_knowledge",
                {"query": "iterations", "kind": "parameter", "limit": 5},
            )
            check(
                len(json.dumps(found, ensure_ascii=False, separators=(",", ":")))
                <= 6000,
                "five-hit budget including legacy aliases",
            )
            check(
                all(
                    h["kind"] == h["record_type"]
                    and h["next_call"] == h["read_next_call"]
                    and h["solver"] == (h["owner_solver"] or "shared")
                    for h in found["hits"]
                ),
                "legacy hit shape and executable next_call",
            )
            for name, solver, default in [
                ("iterations", "vbd", "10"),
                ("iterations", "mujoco", "None"),
                ("padmm.max_iterations", "kamino", "200"),
                ("full_surface", "vbd", "False"),
                ("substeps", "vbd", None),
            ]:
                data = await call("get_parameter", {"name": name, "solver": solver})
                p = data["parameters"][0]
                check(
                    p["declared_default"] == default,
                    "legacy declared default " + solver + " " + name,
                )
                check(
                    all(
                        k in p
                        for k in [
                            "name",
                            "owner",
                            "layer",
                            "summary",
                            "source_refs",
                            "associated_experiments",
                            "related_node_id",
                        ]
                    ),
                    "legacy parameter shape " + name,
                )
            for alias in ["tri_ke", "tri_ka", "edge_ke", "contact_ke", "contact_mu"]:
                data = await call("get_parameter", {"name": alias})
                check(
                    all(
                        p.get("name")
                        and p["source_refs"]
                        and "associated_experiments" in p
                        for p in data["parameters"]
                    ),
                    "legacy group aliases " + alias,
                )
            exp = await call(
                "get_experiment", {"experiment_id": "full_surface", "detail": "full"}
            )
            check(
                exp["id"] == "full_surface"
                and exp["observation"] == exp["experiment"]["observation"],
                "flat experiment aliases",
            )
            check(
                Path(exp["artifacts"]["curve"]["local_path"]).is_file()
                and Path(exp["artifacts"]["runner"]["local_path"]).is_file(),
                "legacy artifact dictionary local files",
            )
            check(
                exp["artifacts"]["viewer_url"].startswith("http://127.0.0.1:18448/")
                and all(
                    Path(v["raw_data"]["local_path"]).is_file() and v["runner_sha256"]
                    for v in exp["variants"]
                ),
                "legacy web URL and variant raw data",
            )
            inventory = await call("get_document", {"limit": 10})
            check(
                all(d["path"] for d in inventory["documents"]),
                "legacy document inventory usable paths",
            )
            first = inventory["documents"][0]
            doc = await call("get_document", {"path": first["path"], "max_lines": 4})
            check(
                doc["content"] == doc["text"]
                and doc["next_start_line"]
                == doc["next_call"]["arguments"]["start_line"],
                "legacy document content continuation",
            )
            src = await call(
                "get_source",
                {
                    "path": "newton/_src/solvers/vbd/solver_vbd.py",
                    "start_line": 80,
                    "max_lines": 200,
                },
            )
            check(
                src["content"] == src["text"]
                and src["next_start_line"]
                == src["next_call"]["arguments"]["start_line"],
                "legacy source content continuation",
            )
            # A validation report is discovered from its incoming/outgoing typed relation.
            receipt = json.loads(
                (ROOT / "knowledge/validation-receipts.json").read_text()
            )["records"]["concept:collisions"]
            rel = await call(
                # Keep each page within the API's 32000-character envelope;
                # follow every continuation until the receipt edge is found.
                "get_relations", {"node_id": "concept:collisions", "limit": 10}
            )
            while not any(
                e["relation"] == "validated_by" for e in rel["edges"]
            ) and rel.get("next_call"):
                rel = await call(
                    rel["next_call"]["tool"], rel["next_call"]["arguments"]
                )
            edge = next(
                (e for e in rel["edges"] if e["relation"] == "validated_by"), None
            )
            check(edge is not None, "validation provenance discovered by relation")
            if edge:
                report = await call(
                    edge["read_next_call"]["tool"],
                    {**edge["read_next_call"]["arguments"], "max_lines": 30},
                )
                check(
                    report["record"]["evidence_type"] == "task_validation"
                    and receipt["report_sha256"] == report["metadata"]["sha256"],
                    "validation report readable, separate from physics",
                )
    failed = sum(not c["passed"] for c in checks)
    report = {
        "phase": "P5",
        "status": "failed" if failed else "passed",
        "build_id": json.loads((ROOT / "knowledge/current.json").read_text())[
            "build_id"
        ],
        "passed": len(checks) - failed,
        "failed": failed,
        "calls": len(trace),
        "checks": checks,
    }
    for name, value in [
        ("p5-mcp-validation.json", report),
        ("p5-mcp-trace.json", trace),
    ]:
        (ROOT / "evaluations" / name).write_text(
            json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(json.dumps({k: v for k, v in report.items() if k != "checks"}))
    if failed:
        print([c for c in checks if not c["passed"]])
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
