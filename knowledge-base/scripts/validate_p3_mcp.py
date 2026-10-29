"""Evaluate twelve independently frozen P3 scenarios through external stdio."""

import asyncio
import hashlib
import json
import re
import time
from pathlib import Path
import tiktoken
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
checks = []
trace = []
tasks_output = []
encoder = tiktoken.get_encoding("o200k_base")


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def check(value, label):
    checks.append({"check": label, "passed": bool(value)})
    if not value:
        print("FAILED: " + label, flush=True)


def serialized(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def assess(tid, body, source):
    joined = "\n".join(source.values())
    low = joined.lower()
    rules = {
        "X01": {
            "coordinate and DOF split": "joint_coord_count" in body
            and "joint_dof_count" in body
            and "joint_target_q_start" in body,
            "real clear implementation": "model.joint_target_q" in joined
            and "wp.copy" in joined
            and "zero_" in joined,
        },
        "X02": {
            "actual additive effort contract": "scatter-add" in low and "zero" in low,
            "schedule and double-drive explanation": "Delay" in body
            and "Clamping" in body
            and "重复计算" in body,
        },
        "X03": {
            "actual geometry API contract": all(
                s in joined
                for s in ("convex_hull", "raise_on_failure", "keep_visual_shapes")
            ),
            "candidate filtering distinct": "filter_pair" in body
            and "iterations" in body
            and "凹洞" in body,
        },
        "X04": {
            "actual allocation freeze": "Allocation freezes" in joined
            and "capacities" in joined,
            "capacity not iterations": "iterations" in body
            and "overflow" in body
            and "live contact count" in body,
        },
        "X05": {
            "narrow flags are distinct actual bits": bool(
                re.search(r"JOINT_DOF_PROPERTIES\s*=\s*1\s*<<\s*1\b", joined)
            )
            and bool(
                re.search(r"JOINT_DOF_INERTIAL_PROPERTIES\s*=\s*1\s*<<\s*10\b", joined)
            ),
            "specific notifications and graph boundaries": all(
                s in body
                for s in (
                    "BODY_INERTIAL_PROPERTIES",
                    "JOINT_DOF_FORCE_PROPERTIES",
                    "重新捕获",
                )
            )
            and "notify_model_changed" in joined,
        },
        "X06": {
            "actual reset mask shape": "world_count + 1" in joined,
            "global and public/private reset split": all(
                s in body for s in ("global", "StateFlags", "双缓冲", "no-op", "False")
            ),
        },
        "X07": {
            "actual backend acceleration difference": "step-average" in joined
            and "input body frames" in joined,
            "consumer distinction": all(
                s in body
                for s in ("BODY_QDD", "CONTACT_F", "QFRC_ACTUATOR", "state_in")
            ),
        },
        "X08": {
            "actual interface joint restrictions": "REVOLUTE" in joined
            and "Prismatic" in joined
            and "not yet" in joined,
            "attachment and owner boundaries": all(
                s in body
                for s in (
                    "未",
                    "owner",
                    "coupling:body_particle_attachment",
                    "ContactPair",
                    "夹爪",
                )
            ),
        },
        "X09": {
            "actual Tape example and state history": all(
                s in joined
                for s in ("self.states", "wp.Tape", "backward", "requires_grad")
            ),
            "backend limitation and no runtime claim": "XPBD/VBD 不支持" in body
            and "不宣称" in body,
        },
        "X10": {
            "actual numerical mapping and inverse-weight limit": "convert_solref"
            in joined
            and "refsafe" in joined
            and "not the full scalar contact effective mass" in joined,
            "no private-API or universal mass claim": all(
                s in body
                for s in ("SOLREF_MODE_*", "不是公开", "unit-mass", "不是任意")
            ),
        },
        "X11": {
            "actual dependent defaults": all(
                s in joined
                for s in ("__post_init__", "dynamics_solver", "preconditioning=False")
            ),
            "residuals not normalized and different definitions": "neither backend divides"
            in joined
            and "同单位不表示同一定义" in body
            and "N·s" in body,
        },
        "X12": {
            "actual DAT limits": all(
                s in low
                for s in (
                    "kinematic",
                    "not truncated",
                    "does not by itself guarantee",
                    "construction",
                )
            ),
            "owned resource and construction-time budget": all(
                s in body
                for s in (
                    "contacts=None",
                    "PRE_POST_INIT",
                    "构造时固定",
                    "experimental",
                )
            ),
        },
    }
    return rules[tid]


async def main():
    from maintenance import archive_file

    for name in ("p3-mcp-validation.json", "p3-mcp-trace.json"):
        archive_file(ROOT / "evaluations" / name, ROOT)
    pointer = load("knowledge/current.json")
    records = load(pointer["path"] + "/records.json")
    task_pack = load("planning/p3/tasks.json")
    check(
        hashlib.sha256((ROOT / "planning/p3/tasks.json").read_bytes()).hexdigest()
        == load("planning/p3/scope-lock.json")["tasks_sha256"],
        "P3 pre-content task pack unchanged",
    )
    config = load("mcp_service/configs/mcp.json")["mcpServers"]["newton_knowledge"]
    active = "handshake"
    async with stdio_client(StdioServerParameters(**config)) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=30) as client:
            await client.initialize()

            async def call(name, args):
                started = time.perf_counter()
                result = await client.call_tool(name, args)
                data = result.structured_content
                text = serialized(data)
                trace.append(
                    dict(
                        task=active,
                        tool=name,
                        arguments=args,
                        result=data,
                        is_error=bool(result.is_error),
                        latency_ms=(time.perf_counter() - started) * 1000,
                        logical_json_chars=len(text),
                        utf8_bytes=len(text.encode()),
                        tokenizer_tokens=len(encoder.encode(text)),
                    )
                )
                check(
                    not result.is_error and data["status"] == "ok",
                    active + " successful exact read " + name,
                )
                check(
                    data["build_id"] == pointer["build_id"],
                    active + " coherent snapshot",
                )
                check(len(text) <= 32000, active + " bounded tool response")
                return data

            for task in task_pack["tasks"]:
                active = task["id"]
                start = len(trace)
                query = task["query"]
                check(
                    query not in records[task["record_id"]]["body"]
                    and query not in records[task["record_id"]]["summary"],
                    active + " held-out question not copied into indexed prose",
                )
                # Query and public recipe category only; no grading path/ID enters this call.
                found = await call(
                    "search_knowledge", {"query": query, "kind": "recipe", "limit": 5}
                )
                hits = found["hits"]
                hit = next((h for h in hits if h["id"] == task["record_id"]), None)
                check(hit is not None, active + " relevant recipe discovered")
                if not hit:
                    continue
                read_call = hit["read_next_call"]
                document = await call(read_call["tool"], read_call["arguments"])
                body = document["text"]
                check(
                    document["record"]["id"] == task["record_id"]
                    and not document["truncated"],
                    active + " complete exact recipe read",
                )
                related = await call(
                    "get_relations", {"node_id": document["record"]["id"], "limit": 8}
                )
                neighbor = next(
                    (
                        n
                        for n in related["neighbors"]
                        if n["record_type"] == "source_symbol"
                    ),
                    None,
                )
                check(neighbor is not None, active + " related API is discoverable")
                if neighbor:
                    next_read = neighbor["read_next_call"]
                    await call(next_read["tool"], next_read["arguments"])
                # Source paths come only from document.source_refs, matched to rubric after discovery.
                actual_sources = {}
                for wanted in task["source_requirements"]:
                    refs = [r for r in document["source_refs"] if r["path"] == wanted]
                    check(
                        bool(refs),
                        active + " requested factual source returned " + wanted,
                    )
                    if not refs:
                        continue
                    ref = next(
                        (r for r in refs if r.get("role") == "behavior_excerpt"),
                        refs[0],
                    )
                    excerpt = await call(
                        "get_source",
                        {
                            "path": ref["path"],
                            "start_line": max(1, ref["line"] - 8),
                            "max_lines": 80,
                        },
                    )
                    check(
                        excerpt["sha256"] == excerpt["manifest_sha256"],
                        active + " source baseline hash verified " + wanted,
                    )
                    actual_sources[wanted] = excerpt["text"]
                points = assess(active, body, actual_sources)
                for name, passed in points.items():
                    check(passed, active + " source-and-answer rubric " + name)
                count = len(trace) - start
                check(count <= task["max_calls"], active + " call target " + str(count))
                rank = next(
                    i + 1 for i, h in enumerate(hits) if h["id"] == task["record_id"]
                )
                tasks_output.append(
                    dict(
                        id=active,
                        query=query,
                        record_id=task["record_id"],
                        status="passed"
                        if all(
                            c["passed"]
                            for c in checks
                            if c["check"].startswith(active + " ")
                        )
                        else "failed",
                        calls=count,
                        recall_at_5=1,
                        reciprocal_rank=1 / rank,
                        source_paths=list(actual_sources),
                        answer_evidence=points,
                        tokenizer_tokens=sum(
                            t["tokenizer_tokens"] for t in trace[start:]
                        ),
                        logical_json_chars=sum(
                            t["logical_json_chars"] for t in trace[start:]
                        ),
                        utf8_bytes=sum(t["utf8_bytes"] for t in trace[start:]),
                    )
                )
    failed = sum(not c["passed"] for c in checks)
    complete = len(tasks_output) == 12 and all(
        t["status"] == "passed" for t in tasks_output
    )
    report = dict(
        phase="P3",
        status="passed" if not failed and complete else "failed",
        build_id=pointer["build_id"],
        passed=len(checks) - failed,
        failed=failed + int(not complete),
        calls=len(trace),
        tasks=tasks_output,
        checks=checks,
        metrics={
            "recall_at_5": sum(t["recall_at_5"] for t in tasks_output) / 12,
            "MRR": sum(t["reciprocal_rank"] for t in tasks_output) / 12,
            "tokenizer": "tiktoken 0.12.0 / o200k_base",
            "actual_llm_usage_tokens": None,
            "measurement": "Exact token counts of serialized tools; deterministic evidence workflow, no free-form LLM or physical simulation claim.",
        },
        validated_records=[
            {
                "id": t["record_id"],
                "body_sha256": hashlib.sha256(
                    records[t["record_id"]]["body"].encode()
                ).hexdigest(),
            }
            for t in tasks_output
            if t["status"] == "passed"
        ],
    )
    for name, value in [
        ("p3-mcp-trace.json", trace),
        ("p3-mcp-validation.json", report),
    ]:
        (ROOT / "evaluations" / name).write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(
        serialized(
            {
                k: v
                for k, v in report.items()
                if k not in ("tasks", "checks", "validated_records")
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
        (ROOT / "evaluations/p3-mcp-partial-trace.json").write_text(
            json.dumps(trace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        raise
