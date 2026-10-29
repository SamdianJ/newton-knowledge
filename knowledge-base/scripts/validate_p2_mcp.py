"""Frozen task acceptance through a real external MCP stdio client.

Exact source paths come from tool results. Frozen IDs grade discovery/read
coverage; they are not hidden source paths injected into search prompts.
"""

from __future__ import annotations
import asyncio
import hashlib
import json
import time
from pathlib import Path
import tiktoken
from jsonschema import Draft202012Validator
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
checks = []
trace = []
results = []
encoding = tiktoken.get_encoding("o200k_base")


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def check(value, label):
    checks.append({"check": label, "passed": bool(value)})
    if not value:
        print("FAILED: " + label, flush=True)


async def main():
    from maintenance import archive_file

    for name in ("p2-mcp-validation.json", "p2-mcp-trace.json"):
        archive_file(ROOT / "evaluations" / name, ROOT)
    pointer = load("knowledge/current.json")
    records = load(pointer["path"] + "/records.json")
    graph = load(pointer["path"] + "/graph.json")
    contract = load("planning/p0/mcp-contract.json")
    tasks = load("planning/p0/acceptance-tasks.json")["tasks"]
    supplementary_reads = set()
    config = load("mcp_service/configs/mcp.json")["mcpServers"]["newton_knowledge"]
    active = "contract"
    read_ids = set()
    initial = {}
    async with stdio_client(StdioServerParameters(**config)) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=30) as session:
            init = await session.initialize()
            check(
                init.server_info.name == "newton_knowledge", "external stdio initialize"
            )
            listed = await session.list_tools()
            tools = {t.name: t.model_dump(by_alias=True) for t in listed.tools}
            check(set(tools) == set(contract["tools"]), "exactly six preserved tools")
            for name, spec in tools.items():
                check(
                    spec["inputSchema"] == contract["tools"][name]["inputSchema"],
                    "frozen strict schema " + name,
                )
                check(
                    spec["annotations"]["readOnlyHint"]
                    and not spec["annotations"]["destructiveHint"]
                    and not spec["annotations"]["openWorldHint"],
                    "read-only hints " + name,
                )

            async def call(name, args, error=False):
                start = time.perf_counter()
                response = await session.call_tool(name, args)
                data = response.structured_content
                text = compact(data)
                trace.append(
                    dict(
                        task=active,
                        tool=name,
                        arguments=args,
                        is_error=bool(response.is_error),
                        latency_ms=(time.perf_counter() - start) * 1000,
                        logical_json_chars=len(text),
                        utf8_bytes=len(text.encode()),
                        tokenizer_tokens=len(encoding.encode(text)),
                        result=data,
                    )
                )
                check(
                    bool(response.is_error) == error,
                    active + " expected result " + name + " " + str(args)[:90],
                )
                check(
                    isinstance(data, dict)
                    and data.get("build_id") == pointer["build_id"],
                    active + " coherent structured build",
                )
                if data:
                    check(
                        not list(
                            Draft202012Validator(
                                contract["tools"][name]["outputSchema"]
                            ).iter_errors(data)
                        ),
                        active + " envelope schema",
                    )
                    check(len(text) <= 32000, active + " response within total budget")
                    if data.get("record"):
                        read_ids.add(data["record"]["id"])
                    if name == "search_knowledge" and args.get("limit", 6) == 5:
                        check(len(text) <= 6000, active + " compact five hits")
                return data

            async def follow(hit):
                return await call(
                    hit["read_next_call"]["tool"], hit["read_next_call"]["arguments"]
                )

            async def begin(task):
                nonlocal active, read_ids
                active = task["id"]
                read_ids = set()
                start = len(trace)
                found = await call(
                    "search_knowledge", {"query": task["query"], "limit": 5}
                )
                initial[active] = found
                return found, start

            def finish(task, start, points):
                required = set(task["required_record_ids"])
                missing = required - read_ids
                count = len(trace) - start
                check(
                    not missing,
                    active + " mandatory records read " + str(sorted(missing)),
                )
                if task["target_max_calls"] is not None:
                    check(
                        count <= task["target_max_calls"],
                        active + " call target " + str(count),
                    )
                for label, value in points.items():
                    check(value, active + " " + label)
                ids = [h["id"] for h in initial.get(active, {}).get("hits", [])]
                rank = next((i + 1 for i, r in enumerate(ids) if r in required), None)
                results.append(
                    dict(
                        id=active,
                        query=task["query"],
                        status="passed"
                        if all(
                            c["passed"]
                            for c in checks
                            if c["check"].startswith(active + " ")
                        )
                        else "failed",
                        required_record_ids=sorted(required),
                        read_record_ids=sorted(read_ids),
                        missing=sorted(missing),
                        calls=count,
                        recall_at_5=len(required.intersection(ids)) / len(required)
                        if required
                        else None,
                        reciprocal_rank=1 / rank if rank else 0 if required else None,
                        logical_json_chars=sum(
                            t["logical_json_chars"] for t in trace[start:]
                        ),
                        utf8_bytes=sum(t["utf8_bytes"] for t in trace[start:]),
                        tokenizer_tokens=sum(
                            t["tokenizer_tokens"] for t in trace[start:]
                        ),
                        answer_evidence=points,
                    )
                )

            # T01: defaults, exact owner readers and measurement scope.
            task = tasks[0]
            found, start = await begin(task)
            v = next(
                h for h in found["hits"] if h["id"].endswith("SolverVBD:iterations")
            )
            m = next(h for h in found["hits"] if h["id"].endswith("mujoco:iterations"))
            k = next(h for h in found["hits"] if h.get("owner_solver") == "kamino")
            vp = await follow(v)
            mp = await follow(m)
            kd = await call(
                k["solver_next_call"]["tool"], k["solver_next_call"]["arguments"]
            )
            check(
                "config.padmm.max_iterations" in kd["text"],
                "T01 Kamino field discovered in returned solver document",
            )
            ks = await call(
                "search_knowledge",
                {
                    "query": "config.padmm.max_iterations",
                    "solver": "kamino",
                    "kind": "parameter",
                    "limit": 5,
                },
            )
            kp = await follow(ks["hits"][0])
            for hit in (v, m):
                await call(
                    hit["solver_next_call"]["tool"],
                    hit["solver_next_call"]["arguments"],
                )
            finish(
                task,
                start,
                {
                    "VBD default 10": vp["parameter"]["declared_default_expression"]
                    == "10",
                    "MuJoCo conditional None": mp["parameter"][
                        "declared_default_expression"
                    ]
                    == "None"
                    and bool(mp["parameter"].get("default_policy")),
                    "PADMM default 200": kp["parameter"]["declared_default_expression"]
                    == "200",
                    "distinct measurements": all(
                        response["experiment_status"]
                        == (
                            "measured"
                            if records[rid]["payload"].get("experiments")
                            else "no_measured_evidence"
                        )
                        for response, rid in [
                            (vp, v["id"]),
                            (mp, m["id"]),
                            (kp, ks["hits"][0]["id"]),
                        ]
                    ),
                },
            )
            task = tasks[1]
            found, start = await begin(task)
            p = await follow(
                next(h for h in found["hits"] if h["record_type"] == "parameter")
            )
            e = await follow(
                next(h for h in found["hits"] if h["record_type"] == "lab_experiment")
            )
            await follow(
                next(h for h in found["hits"] if h["id"] == "concept:collisions")
            )
            ref = p["record"]["source_next_call"]
            source = await call(ref["tool"], ref["arguments"])
            variants = e["experiment"]["variants"]
            finish(
                task,
                start,
                {
                    "CollisionPipeline owner and False": p["parameter"]["owner"]
                    == "newton.CollisionPipeline.__init__"
                    and p["parameter"]["declared_default_expression"] == "False",
                    "verified exact source": "enable_rigid_soft_full_surface_contact"
                    in source["text"]
                    and source["sha256"] == source["manifest_sha256"],
                    "measured finite penalty": variants[0]["metrics"][
                        "max_edge_face_records"
                    ]
                    == 0
                    and variants[1]["metrics"]["max_edge_face_records"] > 0
                    and abs(variants[1]["metrics"]["final"]) < 1,
                    # CR-004: known edge/face response limits must not regress to unknown.
                    "explicit full-surface response boundary": p["parameter"]["support_matrix"]["mujoco"]
                    == "unsupported"
                    and p["parameter"]["support_matrix"]["xpbd"] == "unsupported"
                    and p["parameter"]["support_matrix"]["vbd"] == "conditional"
                    and "proxy-particle" in p["parameter"]["support_conditions"]["vbd"],
                },
            )
            selections = {
                2: "recipe:ik-mujoco-contact",
                3: "recipe:coupled-rigid-deformable",
                4: "recipe:worlds-reset",
                5: "recipe:mujoco-native-contact",
                6: "topic:differentiable-simulation",
            }
            for index, rid in selections.items():
                task = tasks[index]
                found, start = await begin(task)
                seed = next((h for h in found["hits"] if h["id"] == rid), None) or next(
                    h for h in found["hits"] if h["id"] in task["required_record_ids"]
                )
                doc = await follow(seed)
                relation = await call(
                    "get_relations", {"node_id": doc["record"]["id"], "limit": 12}
                )
                docs = [doc]
                for required in task["required_record_ids"]:
                    if required not in read_ids:
                        neighbor = next(
                            (n for n in relation["neighbors"] if n["id"] == required),
                            None,
                        )
                        check(
                            neighbor is not None,
                            active + " required neighbor discovered " + required,
                        )
                        if neighbor:
                            docs.append(await follow(neighbor))
                body = "\n".join(d.get("text", "") for d in docs)
                terms = {
                    2: (
                        "ControllerDifferentialIK",
                        "joint_coord_count",
                        "joint_dof_count",
                        "use_coord_layout_targets",
                        "CONTACT_F",
                        "MuJoCo Warp",
                        "state_in",
                        "state_out",
                    ),
                    3: (
                        "ModelView",
                        "owned",
                        "Proxy",
                        "ADMM",
                        "substeps",
                        "attachment",
                        "ContactPair",
                        "PRISMATIC/DISTANCE/D6",
                        "不等同",
                    ),
                    4: (
                        "world_count+1",
                        "count_per_world",
                        "global",
                        "set_attribute",
                        "no-op",
                        "solver.reset",
                    ),
                    5: (
                        "冻结",
                        "contacts=contacts",
                        "get_max_contact_count",
                        "pipeline.collide",
                        "state_in",
                        "state_out",
                        "QFRC_ACTUATOR",
                        "use_mujoco_cpu=True",
                    ),
                    6: (
                        "SolverSemiImplicit",
                        "SolverFeatherstone",
                        "SolverVBD",
                        "SolverXPBD",
                        "requires_grad=True",
                        "tape.backward",
                        "没有",
                    ),
                }
                finish(task, start, {term: term in body for term in terms[index]})
            task = tasks[7]
            found, start = await begin(task)
            doc = await follow(
                next(h for h in found["hits"] if h["id"] == "solver:xpbd")
            )
            ref = next(
                r for r in doc["source_refs"] if r["path"].endswith("solver_xpbd.py")
            )
            source = await call(
                "get_source",
                {"path": ref["path"], "start_line": ref["line"], "max_lines": 100},
            )
            missing = await call(
                "get_parameter", {"name": "iterations", "solver": "xpbd"}
            )
            finish(
                task,
                start,
                {
                    "exact public class source": "SolverXPBD" in source["text"]
                    and source["sha256"] == source["manifest_sha256"],
                    "known but not curated": missing["status"] == "not_indexed"
                    and missing["known_declaration"]
                    and bool(missing["source_next_call"]),
                },
            )
            task = tasks[8]
            active = task["id"]
            read_ids = set()
            start = len(trace)
            found = await call(
                "search_knowledge",
                {"query": "ControllerDifferentialIK", "kind": "api", "limit": 5},
            )
            initial[active] = found
            await follow(
                next(h for h in found["hits"] if h["id"] == "module:controllers")
            )
            known = await call(
                "search_knowledge",
                {
                    "query": "newton.controllers.ControllerDifferentialIK",
                    "kind": "parameter",
                    "limit": 5,
                },
            )
            random = await call(
                "search_knowledge",
                {"query": "zzqv_never_a_newton_symbol_981237", "limit": 5},
            )
            finish(
                task,
                start,
                {
                    "known public export distinguished": known["status"]
                    == "not_indexed"
                    and bool(known["known_public_symbols"]),
                    "random no_match": random["status"] == "no_match"
                    and not random["hits"],
                },
            )
            task = tasks[9]
            active = task["id"]
            read_ids = set()
            start = len(trace)
            found = await call(
                "search_knowledge",
                {"query": "几何与碰撞工具", "kind": "api", "limit": 5},
            )
            initial[active] = found
            await follow(next(h for h in found["hits"] if h["id"] == "module:geometry"))
            bad = await call(
                "search_knowledge",
                {"query": "contact", "stage": "unsupported_stage"},
                True,
            )
            extra = await call(
                "search_knowledge", {"query": "contact", "extra_filter": True}, True
            )
            conflict = await call(
                "get_parameter", {"record_id": v["id"], "solver": "mujoco"}, True
            )
            scoped = await call(
                "search_knowledge",
                {
                    "query": "CONTACT_F",
                    "solver": "mujoco",
                    "include_shared": True,
                    "stage": "output",
                    "limit": 5,
                },
            )
            finish(
                task,
                start,
                {
                    "unknown fields and stage reject": bad["status"]
                    == extra["status"]
                    == "error",
                    "ID-solver conflict": conflict["error"]["code"] == "SCOPE_CONFLICT",
                    "filters really apply": scoped["applied_filters"]["stage"]
                    == "output"
                    and all(
                        "output" in h["stages"]
                        and (
                            h["owner_solver"] == "mujoco"
                            or "mujoco" in records[h["id"]]["applicable_solvers"]
                        )
                        for h in scoped["hits"]
                    ),
                },
            )
            task = tasks[10]
            active = task["id"]
            read_ids = set()
            start = len(trace)

            async def collect(
                tool, args, key, cursor_key="cursor", returned="next_cursor"
            ):
                ids = []
                cursor = None
                last = None
                while True:
                    last = await call(
                        tool, {**args, **({cursor_key: cursor} if cursor else {})}
                    )
                    ids.extend(x["id"] for x in last[key])
                    cursor = last[returned]
                    if not cursor:
                        break
                return ids, last

            ids, last = await collect(
                "search_knowledge", {"query": "newton", "limit": 20}, "hits"
            )
            check(len(ids) > 300, "T11 spans former 300-candidate limit")
            check(
                len(ids) == len(set(ids)) == last["total"],
                "T11 complete search no duplicates",
            )
            ids, last = await collect("get_document", {"limit": 7}, "items")
            check(
                len(ids) == len(set(ids)) == last["total"],
                "T11 complete document inventory",
            )
            neighbors = []
            edge_ids = []
            cursor = None
            while True:
                last = await call(
                    "get_relations",
                    {
                        "node_id": "module:controllers",
                        "limit": 5,
                        **({"edge_cursor": cursor} if cursor else {}),
                    },
                )
                neighbors.extend(n["id"] for n in last["neighbors"])
                edge_ids.extend(e["id"] for e in last["edges"])
                cursor = last["edge_cursor"]
                check(
                    all(n.get("read_next_call") for n in last["neighbors"])
                    and all(e.get("read_next_call") for e in last["edges"]),
                    "T11 graph exact readers",
                )
                if not cursor:
                    break
            expected = {
                e["id"]
                for e in graph["edges"]
                if "module:controllers" in (e["source"], e["target"])
            }
            check(
                set(edge_ids) == expected and len(edge_ids) == len(expected),
                "T11 complete edge stream",
            )
            check(
                len(neighbors) == len(set(neighbors)) == last["total_neighbors"],
                "T11 complete neighbor stream",
            )
            first = await call("search_knowledge", {"query": "iterations", "limit": 1})
            mismatch = await call(
                "search_knowledge",
                {"query": "contact", "limit": 1, "cursor": first["next_cursor"]},
                True,
            )
            previous = next(
                t
                for t in load("evaluations/p1-mcp-trace.json")
                if t["tool"] == "search_knowledge" and t["result"].get("next_cursor")
            )
            stale = await call(
                "search_knowledge",
                {**previous["arguments"], "cursor": previous["result"]["next_cursor"]},
                True,
            )
            finish(
                task,
                start,
                {
                    "query cursor mismatch": mismatch["error"]["code"]
                    == "CURSOR_QUERY_MISMATCH",
                    "real previous-build cursor invalidates": stale["error"]["code"]
                    == "STALE_CURSOR",
                },
            )
            task = tasks[11]
            active = task["id"]
            read_ids = set()
            start = len(trace)
            found = await call(
                "search_knowledge",
                {"query": "SolverMuJoCo", "kind": "solver", "limit": 5},
            )
            initial[active] = found
            await follow(next(h for h in found["hits"] if h["id"] == "solver:mujoco"))
            version = await call(
                "get_parameter",
                {"name": "iterations", "solver": "mujoco", "version": "9.9.9"},
            )
            absent = await call(
                "get_experiment", {"experiment_id": "full_surface", "solver": "mujoco"}
            )
            proposed = await call(
                "search_knowledge",
                {
                    "query": "iterations",
                    "kind": "diagnostic",
                    "solver": "mujoco",
                    "limit": 5,
                },
            )
            plan = await follow(proposed["hits"][0])
            finish(
                task,
                start,
                {
                    "version never falls back": version["status"]
                    == "unsupported_version",
                    "no borrowed measurement": absent["status"]
                    == "no_measured_evidence",
                    "proposed stays proposed": plan["record"]["evidence_type"]
                    == "proposed"
                    and not plan["record"]["coverage"]["experiment_validated"],
                },
            )
            active = "paths"
            for path in load("planning/p0/required-paths.json")["paths"]:
                required = set(path["required_records"])
                adj = {}
                provenance = []
                for rid in sorted(required):
                    doc = await call("get_document", {"record_id": rid, "max_lines": 8})
                    provenance.append(
                        doc["status"] == "ok" and bool(doc["source_refs"])
                    )
                    related = await call("get_relations", {"node_id": rid, "limit": 12})
                    for edge in related["edges"]:
                        adj.setdefault(edge["source"], set()).add(edge["target"])
                        adj.setdefault(edge["target"], set()).add(edge["source"])
                reached = set()
                pending = [next(iter(required))]
                while pending:
                    rid = pending.pop()
                    if rid in reached:
                        continue
                    reached.add(rid)
                    pending.extend(adj.get(rid, set()) - reached)
                check(
                    required <= reached and all(provenance),
                    path["id"] + " connected exact readers and pinned source refs",
                )
            active = "supplementary-lifecycle-tasks"
            for entry in load("knowledge/registry.json")["entries"]:
                if entry["target_depth"] != "T":
                    continue
                found = await call(
                    "search_knowledge",
                    {"query": entry["title"], "kind": entry["family"], "limit": 5},
                )
                hit = next((h for h in found["hits"] if h["id"] == entry["id"]), None)
                check(
                    hit is not None, "T-depth topic/recipe discoverable " + entry["id"]
                )
                if not hit:
                    continue
                doc = await follow(hit)
                check(
                    doc["status"] == "ok" and bool(doc["source_refs"]),
                    "T-depth exact source-backed explanation " + entry["id"],
                )
                if entry["family"] == "recipe":
                    check(
                        all(
                            s in doc["text"]
                            for s in (
                                "Setup",
                                "每仿真子步",
                                "每控制帧",
                                "每输出帧",
                                "Reset / Model 更新",
                            )
                        ),
                        "recipe five scheduling periods " + entry["id"],
                    )
                if entry["id"] == "recipe:solver-owned-collision":
                    check(
                        "SolverVBD(model, collision_pipeline=pipeline)" in doc["text"]
                        and "contacts=None" in doc["text"],
                        "concrete VBD owned-pipeline setup and step responsibility",
                    )
                ref = next(
                    (
                        r
                        for r in doc["source_refs"]
                        if r["path"].endswith(".py") and "/_src/" in r["path"]
                    ),
                    doc["source_refs"][0],
                )
                src = await call(
                    "get_source",
                    {"path": ref["path"], "start_line": ref["line"], "max_lines": 20},
                )
                check(
                    src["sha256"] == src["manifest_sha256"],
                    "recipe source hash verified " + entry["id"],
                )
                supplementary_reads.add(entry["id"])
            active = "boundaries"
            inventory = await call("get_document", {})
            check(
                inventory["status"] == "ok"
                and bool(inventory["items"])
                and bool(inventory["next_cursor"]),
                "legacy empty document inventory succeeds within budget",
            )
            for name in contract["tools"]:
                args = (
                    {"query": "contact"}
                    if name == "search_knowledge"
                    else {"experiment_id": "full_surface"}
                    if name == "get_experiment"
                    else {"node_id": "module:controllers"}
                    if name == "get_relations"
                    else {}
                )
                await call(name, {**args, "unknown_argument": True}, True)
            for path in (
                "../pyproject.toml",
                "C:/Windows/win.ini",
                "%2e%2e/pyproject.toml",
                ".git/config",
                "newton/not_tracked.py",
            ):
                await call("get_source", {"path": path}, True)
            short = await call(
                "get_document",
                {"record_id": "recipe:ik-mujoco-contact", "max_lines": 8},
            )
            more = await call(
                short["next_call"]["tool"], short["next_call"]["arguments"]
            )
            check(more["start_line"] == short["end_line"] + 1, "text exact next line")
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
                found = await call(
                    "search_knowledge",
                    {"query": "Solver", "solver": solver, "limit": 5},
                )
                check(
                    all(h["owner_solver"] == solver for h in found["hits"]),
                    "strict solver scope " + solver,
                )
            full = await call(
                "get_experiment", {"experiment_id": "full_surface", "detail": "full"}
            )
            summary = await call(
                "get_experiment", {"experiment_id": "full_surface", "detail": "summary"}
            )
            check(
                "initial_geometry" in full["experiment"]
                and "initial_geometry" not in summary["experiment"],
                "detail really controls bounded geometry",
            )
    failed = sum(not c["passed"] for c in checks)
    ranked = [t for t in results if t["recall_at_5"] is not None]
    report = dict(
        phase="P2",
        status="passed"
        if not failed and all(t["status"] == "passed" for t in results)
        else "failed",
        build_id=pointer["build_id"],
        passed=len(checks) - failed,
        failed=failed,
        calls=len(trace),
        tasks=results,
        checks=checks,
        metrics={
            "mean_recall_at_5": sum(t["recall_at_5"] for t in ranked) / len(ranked),
            "MRR": sum(t["reciprocal_rank"] for t in ranked) / len(ranked),
            "all_mandatory_records_read": all(not t["missing"] for t in results),
            "tokenizer": "tiktoken 0.12.0 / o200k_base",
            "token_measurement": "Exact token count of serialized tool JSON. Host hidden prompts/envelopes and actual LLM billing usage are not instrumented.",
            "actual_llm_usage_tokens": None,
            "total_tool_json_tokens": sum(t["tokenizer_tokens"] for t in trace),
        },
        validated_records=[
            {
                "id": rid,
                "body_sha256": hashlib.sha256(
                    records[rid]["body"].encode()
                ).hexdigest(),
            }
            for rid in sorted(
                supplementary_reads
                | {
                    r
                    for t in results
                    if t["status"] == "passed"
                    for r in t["read_record_ids"]
                    if r in records
                }
            )
        ],
    )
    for name, value in [
        ("p2-mcp-trace.json", trace),
        ("p2-mcp-validation.json", report),
    ]:
        (ROOT / "evaluations" / name).write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(
        compact(
            {
                k: v
                for k, v in report.items()
                if k not in ("checks", "tasks", "validated_records")
            }
        ),
        flush=True,
    )
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        (ROOT / "evaluations/p2-mcp-partial-trace.json").write_text(
            json.dumps(trace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        raise
