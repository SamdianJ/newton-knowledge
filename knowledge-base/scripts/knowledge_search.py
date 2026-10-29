"""Compatibility adapter to canonical scoped search. Prefer knowledge_store.invoke."""

from knowledge_store import snapshot


def search_records(query, limit=30, kinds=None, solver="all"):
    store = snapshot()
    results = []
    cursor = None
    while len(results) < min(50, limit):
        page = store.search(
            query, solver=solver, limit=min(20, limit - len(results)), cursor=cursor
        )
        results.extend(
            {**r, "kind": r["record_type"], "solver": r["owner_solver"] or "shared"}
            for r in page["hits"]
            if not kinds or r["record_type"] in kinds
        )
        cursor = page["next_cursor"]
        if not cursor:
            break
    return results[:limit]
