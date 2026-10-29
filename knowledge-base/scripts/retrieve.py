"""CLI adapter for the same immutable snapshot and scoped search as MCP/HTTP."""

import argparse
import json
from knowledge_store import VERSION, invoke, snapshot

ALIASES = {}


def retrieve(query, limit=8, version=VERSION, expand=True, solver="all", **filters):
    result = invoke(
        "search_knowledge",
        dict(
            query=query, limit=min(limit, 20), version=version, solver=solver, **filters
        ),
    )
    if expand and result["status"] == "ok":
        store = snapshot()
        ids = {h["id"] for h in result["hits"]}
        edges = [
            e for e in store.graph["edges"] if e["source"] in ids or e["target"] in ids
        ][:80]
        node_ids = {v for e in edges for v in (e["source"], e["target"])}
        result["graph_context"] = {
            "nodes": [store.nodes[n] for n in sorted(node_ids)],
            "edges": edges,
            "hops": 1,
            "max_edges": 80,
        }
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True)
    parser.add_argument("--limit", type=int, default=6)
    parser.add_argument("--version", default=VERSION)
    parser.add_argument("--solver", default="all")
    parser.add_argument("--domain", default="all")
    parser.add_argument("--stage", default="all")
    parser.add_argument("--include-shared", action="store_true")
    parser.add_argument("--cursor")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = retrieve(
        args.query,
        args.limit,
        args.version,
        solver=args.solver,
        domain=args.domain,
        stage=args.stage,
        include_shared=args.include_shared,
        cursor=args.cursor,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Newton {result['version']} / {result['build_id']} / {result['status']}")
        for hit in result.get("hits", []):
            print(
                hit["id"]
                + " ["
                + (hit["owner_solver"] or "shared")
                + "] "
                + hit["title"]
            )
            print(hit["summary"])
            print(json.dumps(hit["read_next_call"], ensure_ascii=False))
