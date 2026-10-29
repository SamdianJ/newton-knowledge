"""Source/API/default audit and immutable build upkeep. Never runs simulation."""

from __future__ import annotations
import argparse
import ast
import copy
import hashlib
import json
import subprocess
import tomllib
from pathlib import Path

import plan_p0
import source_api
from maintenance import archive_file, sha, verify_sources

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def release_inventory(source):
    source = source.resolve()
    registry = copy.deepcopy(load(ROOT / "knowledge/registry.json"))
    old_src, old_api_src = plan_p0.SRC, source_api.SRC
    try:
        plan_p0.SRC = source
        source_api.SRC = source
        source_api.tree.cache_clear()
        for entry in registry["entries"]:
            if entry["family"] == "api":
                entry["public_exports"] = (
                    plan_p0.exports(entry["source_path"])
                    if (source / entry["source_path"]).is_file()
                    else []
                )
        public = source_api.inventory(registry)
    finally:
        plan_p0.SRC = old_src
        source_api.SRC = old_api_src
        source_api.tree.cache_clear()
    defaults = {}

    def walk(nodes, path, prefix=""):
        for node in nodes:
            if isinstance(node, ast.ClassDef):
                qual = prefix + node.name + "."
                for item in node.body:
                    if (
                        isinstance(item, ast.AnnAssign)
                        and isinstance(item.target, ast.Name)
                        and item.value is not None
                    ):
                        defaults[path + "::" + qual + item.target.id] = ast.unparse(
                            item.value
                        )
                walk(node.body, path, qual)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = node.args.posonlyargs + node.args.args
                for arg, value in zip(
                    args[len(args) - len(node.args.defaults) :], node.args.defaults
                ):
                    defaults[path + "::" + prefix + node.name + "." + arg.arg] = (
                        ast.unparse(value)
                    )
                for arg, value in zip(node.args.kwonlyargs, node.args.kw_defaults):
                    if value is not None:
                        defaults[path + "::" + prefix + node.name + "." + arg.arg] = (
                            ast.unparse(value)
                        )

    git_root = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    own_git = (
        git_root.returncode == 0 and Path(git_root.stdout.strip()).resolve() == source
    )
    tracked = (
        subprocess.run(
            ["git", "-C", str(source), "ls-files", "-z"], capture_output=True, text=True
        )
        if own_git
        else None
    )
    paths = (
        [source / p for p in tracked.stdout.split("\0") if p]
        if tracked is not None
        else sorted(source.rglob("*"))
    )
    files = {}
    for path in paths:
        if not path.is_file() or any(
            part in {".git", ".venv", "__pycache__", ".pytest_cache", "build", "dist"}
            for part in path.relative_to(source).parts
        ):
            continue
        relative = path.relative_to(source).as_posix()
        files[relative] = sha(path)
        if relative.startswith("newton/") and path.suffix == ".py":
            walk(ast.parse(path.read_text(encoding="utf-8")).body, relative)
    metadata = tomllib.loads((source / "pyproject.toml").read_text(encoding="utf-8"))
    git = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"], capture_output=True, text=True
    )
    return {
        "version": metadata.get("project", {}).get("version", "unknown"),
        "commit": git.stdout.strip() if own_git and git.returncode == 0 else None,
        "source_root": str(source),
        "files": files,
        "api": {
            p["public_name"]: {
                k: p.get(k) for k in ["symbol_kind", "signature", "path", "resolution"]
            }
            for p in public
        },
        "defaults": defaults,
        "default_semantics": "AST declaration expressions, not finalized runtime/backend defaults. Physical model/state allocation None is not a physical constant.",
        "physical_evidence_inherited": False,
    }


def diff_inventory(before, after):
    def differences(key):
        a, b = before[key], after[key]
        return {
            "added": {k: b[k] for k in sorted(set(b) - set(a))},
            "removed": {k: a[k] for k in sorted(set(a) - set(b))},
            "changed": {
                k: {"before": a[k], "after": b[k]}
                for k in sorted(set(a) & set(b))
                if a[k] != b[k]
            },
        }

    return {
        "baseline_version": before["version"],
        "candidate_version": after["version"],
        "baseline_commit": before["commit"],
        "candidate_commit": after["commit"],
        "api": differences("api"),
        "defaults": differences("defaults"),
        "files": differences("files"),
        "may_publish": False,
        "physical_evidence_inherited": False,
        "required_actions": [
            "Assign an independent version/source lock and version-scoped IDs.",
            "Review changed declarations against backend resolution and ownership.",
            "Invalidate body/source-dependent task and physical evidence.",
            "Curate and pass contracts, frozen tasks and physical reproduction for the new version before publication.",
        ],
        "scope": "Static comparison; this is not support or physical validation of the candidate.",
    }


def check_platform():
    from knowledge_store import snapshot

    store = snapshot()
    errors = verify_sources(plan_p0.SRC, load(ROOT / "manifests/source-lock.json"))
    checks = []

    def check(value, name):
        checks.append({"name": name, "passed": bool(value)})

    check(not errors, "all pinned source hashes " + str(errors[:5]))
    for edge in store.graph["edges"]:
        check(
            edge["source"] in store.nodes and edge["target"] in store.nodes,
            "edge endpoints " + edge["source"] + " " + edge["target"],
        )
    for r in store.records.values():
        call = store.next_call(r)
        try:
            result = store.invoke(call["tool"], call["arguments"])
            ok = result["status"] == "ok"
        except Exception as exc:
            ok = False
            result = {"error": str(exc)}
        check(
            ok,
            "executable exact reader "
            + r["id"]
            + " "
            + (str(result.get("error", "")) if not ok else ""),
        )
        check(
            (r["record_scope"] == "shared") == (r["owner_solver"] is None),
            "owner/scope " + r["id"],
        )
        if r["coverage"]["task_validated"]:
            receipt = r["validation_evidence"]
            check(
                receipt["body_sha256"]
                == hashlib.sha256(r["body"].encode()).hexdigest(),
                "validated exact body " + r["id"],
            )
            check(
                receipt["report_record_id"] in store.records,
                "validation provenance reader " + r["id"],
            )
    matrix = []
    for e in store.catalog["registry"]["entries"] + store.catalog["extensions"]:
        r = store.records[e["id"]]
        matrix.append(
            {
                "id": r["id"],
                "family": e["family"],
                "target_depth": e["target_depth"],
                "coverage": r["coverage"],
                "deferred": e.get("deferred"),
                "source_count": len(r["source_refs"]),
            }
        )
    save(
        ROOT / "evaluations/coverage-matrix.json",
        {
            "version": store.catalog["version"],
            "build_id": store.build_id,
            "denominators": store.catalog["registry"]["counts"],
            "entries": matrix,
            "solvers": [
                {
                    "id": s,
                    "coverage_level": c["coverage_level"],
                    "parameter_records": len(c["parameters"]),
                    "measured_pairs": len(c["experiments"]),
                }
                for s, c in store.catalog["solvers"].items()
            ],
        },
    )
    failed = sum(not c["passed"] for c in checks)
    report = {
        "phase": "P5",
        "status": "failed" if failed else "passed",
        "build_id": store.build_id,
        "passed": len(checks) - failed,
        "failed": failed,
        "checks": checks,
        "source_files": len(store.source_lock["files"]),
    }
    save(ROOT / "evaluations/p5-integrity-validation.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    inv = sub.add_parser("inventory")
    inv.add_argument("--source", type=Path, default=plan_p0.SRC)
    inv.add_argument("--out", type=Path, required=True)
    diff = sub.add_parser("compare")
    diff.add_argument("--baseline", type=Path, required=True)
    diff.add_argument("--candidate", type=Path, required=True)
    diff.add_argument("--out", type=Path, required=True)
    archive = sub.add_parser("archive")
    archive.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    if args.command == "inventory":
        data = release_inventory(args.source)
        save(args.out, data)
        print(
            json.dumps(
                {
                    "version": data["version"],
                    "api": len(data["api"]),
                    "defaults": len(data["defaults"]),
                    "out": str(args.out),
                }
            )
        )
    elif args.command == "compare":
        data = diff_inventory(load(args.baseline), release_inventory(args.candidate))
        save(args.out, data)
        print(
            json.dumps(
                {
                    k: {a: len(b) for a, b in v.items()}
                    for k, v in data.items()
                    if k in ["api", "defaults", "files"]
                }
            )
        )
    elif args.command == "archive":
        for path in args.paths:
            print(archive_file(path, ROOT))
    else:
        report = check_platform()
        print(json.dumps({k: v for k, v in report.items() if k != "checks"}))
        raise SystemExit(bool(report["failed"]))


if __name__ == "__main__":
    main()
