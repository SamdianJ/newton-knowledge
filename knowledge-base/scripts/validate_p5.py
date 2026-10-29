"""Maintenance failure fixtures, immutable rebuild and current capability checks."""

from __future__ import annotations
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from maintenance import archive_file, promote, sha, validate_receipt, verify_sources
from maintain import diff_inventory, release_inventory
from knowledge_store import KnowledgeError, Snapshot, snapshot

ROOT = Path(__file__).resolve().parents[1]


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    checks = []

    def check(value, name):
        checks.append({"name": name, "passed": bool(value)})
        if not value:
            print("FAILED " + name, flush=True)

    archive_file(ROOT / "evaluations/p5-validation.json", ROOT)
    store = snapshot()
    before = sha(store.path / "manifest.json")
    stats = {p.name: p.stat().st_mtime_ns for p in store.path.iterdir() if p.is_file()}
    rebuilt = subprocess.run(
        [sys.executable, "-B", "-X", "utf8", str(ROOT / "scripts/build_platform.py")],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    check(
        rebuilt.returncode == 0 and '"reused": true' in rebuilt.stdout,
        "identical-input rebuild reuses complete snapshot " + rebuilt.stderr[-500:],
    )
    check(
        before == sha(store.path / "manifest.json")
        and stats
        == {p.name: p.stat().st_mtime_ns for p in store.path.iterdir() if p.is_file()},
        "immutable snapshots and timestamps unchanged on reuse",
    )
    for r in store.records.values():
        if not r["coverage"]["task_validated"]:
            continue
        receipt = r["validation_evidence"]
        check(
            validate_receipt(r["body"], receipt, ROOT, r["source_refs"]),
            "unchanged body/source retains task validation " + r["id"],
        )
        changed_refs = [dict(ref) for ref in r["source_refs"]]
        if changed_refs:
            changed_refs[0]["sha256"] = "0" * 64
            check(
                not validate_receipt(r["body"], receipt, ROOT, changed_refs),
                "changed source loses task validation " + r["id"],
            )
        check(
            not validate_receipt(r["body"] + "\nchanged", receipt, ROOT),
            "changed body loses task validation " + r["id"],
        )
        doc = store.invoke(
            "get_document", {"record_id": receipt["report_record_id"], "max_lines": 10}
        )
        check(
            doc["status"] == "ok"
            and doc["record"]["record_type"] == "validation_report",
            "MCP can read immutable validation report " + r["id"],
        )
    with tempfile.TemporaryDirectory(prefix="newton-kb-maintenance-") as temp:
        temp = Path(temp)
        fixture_a = temp / "release-a"
        fixture_b = temp / "release-b"
        for root, version, definition in [
            (
                fixture_a,
                "1.7.0-fixture",
                'class Model:\n    gain: float = 1.0\n    def __init__(self, dt=0.01): pass\nclass Foo: pass\n__all__=["Model","Foo"]\n',
            ),
            (
                fixture_b,
                "1.8.0-fixture",
                'class Model:\n    gain: float = 2.0\n    def __init__(self, dt=0.02): pass\nclass Bar: pass\n__all__=["Model","Bar"]\n',
            ),
        ]:
            (root / "newton").mkdir(parents=True)
            (root / "newton/__init__.py").write_text(definition, encoding="utf-8")
            (root / "pyproject.toml").write_text(
                '[project]\nname="fixture"\nversion="' + version + '"\n',
                encoding="utf-8",
            )
        a, b = release_inventory(fixture_a), release_inventory(fixture_b)
        diff = diff_inventory(a, b)
        check(
            "newton.Bar" in diff["api"]["added"]
            and "newton.Foo" in diff["api"]["removed"],
            "added and removed public API detected in disposable releases",
        )
        check(
            "newton.Model" in diff["api"]["changed"],
            "public constructor signature difference detected",
        )
        check(
            any(k.endswith("Model.__init__.dt") for k in diff["defaults"]["changed"])
            and any(k.endswith("Model.gain") for k in diff["defaults"]["changed"]),
            "constructor and configuration declaration defaults compared",
        )
        check(
            not diff["may_publish"] and not diff["physical_evidence_inherited"],
            "new-version proposal cannot inherit physical evidence or publish automatically",
        )
        diff["fixture_only"] = True
        save(ROOT / "evaluations/p5-version-diff-fixture.json", diff)
        source = fixture_a / "newton/__init__.py"
        lock = {"files": {"newton/__init__.py": sha(source)}}
        check(not verify_sources(fixture_a, lock), "clean source fixture accepted")
        source.write_text(source.read_text() + "\n# changed", encoding="utf-8")
        check(
            bool(verify_sources(fixture_a, lock)),
            "source mutation detected before regeneration",
        )
        report = temp / "receipt.json"
        save(report, {"status": "passed"})
        receipt = {
            "report": "receipt.json",
            "report_sha256": sha(report),
            "body_sha256": hashlib.sha256(b"body").hexdigest(),
        }
        check(validate_receipt("body", receipt, temp), "valid report receipt accepted")
        save(report, {"status": "tampered"})
        try:
            validate_receipt("body", receipt, temp)
            rejected = False
        except ValueError:
            rejected = True
        check(rejected, "tampered validation report rejected")
        workspace = temp / "knowledge"
        stage = workspace / "staging/incomplete"
        dest = workspace / "builds/incomplete"
        stage.mkdir(parents=True)
        save(workspace / "current.json", {"build_id": "old"})
        save(stage / "manifest.json", {"files": {}})
        try:
            promote(stage, dest)
            rejected = False
        except ValueError:
            rejected = True
        check(
            rejected
            and not dest.exists()
            and json.loads((workspace / "current.json").read_text())["build_id"]
            == "old",
            "interrupted/incomplete staging cannot replace current build",
        )
        complete = workspace / "staging/complete"
        complete.mkdir()
        names = [
            "catalog.json",
            "records.json",
            "graph.json",
            "documents.json",
            "knowledge.sqlite",
        ]
        [(complete / n).write_text("{}") for n in names]
        save(
            complete / "manifest.json", {"files": {n: sha(complete / n) for n in names}}
        )
        promote(complete, workspace / "builds/complete")
        check(
            (workspace / "builds/complete/manifest.json").is_file()
            and not complete.exists(),
            "complete staging promoted atomically within workspace",
        )
        # Copy only immutable metadata/files into a disposable root; never edit real artifacts.
        fixture = temp / "snapshot"
        fixture.mkdir()
        rel = "builds/fixture"
        target = fixture / rel
        target.mkdir(parents=True)
        manifest = json.loads((store.path / "manifest.json").read_text())
        manifest["programs"] = {}
        for name in manifest["files"]:
            (target / name).write_bytes((store.path / name).read_bytes())
        manifest["files"]["records.json"] = "0" * 64
        save(target / "manifest.json", manifest)
        import knowledge_store

        original_root = knowledge_store.ROOT
        knowledge_store.ROOT = fixture
        try:
            try:
                Snapshot(
                    {
                        "path": rel,
                        "build_id": store.build_id,
                        "manifest_sha256": sha(target / "manifest.json"),
                    }
                )
                code = None
            except KnowledgeError as exc:
                code = exc.code
        finally:
            knowledge_store.ROOT = original_root
        check(
            code == "SNAPSHOT_INTEGRITY",
            "mixed/tampered snapshot rejected before reading",
        )
        clean_manifest = json.loads((store.path / "manifest.json").read_text())
        clean_manifest["programs"] = {"fixture_program.py": "0" * 64}
        (fixture / "fixture_program.py").write_text("changed")
        save(target / "manifest.json", clean_manifest)
        knowledge_store.ROOT = fixture
        try:
            try:
                Snapshot(
                    {
                        "path": rel,
                        "build_id": store.build_id,
                        "manifest_sha256": sha(target / "manifest.json"),
                    }
                )
                code = None
            except KnowledgeError as exc:
                code = exc.code
        finally:
            knowledge_store.ROOT = original_root
        check(code == "PROGRAM_MISMATCH", "changed runtime program rejected")
        clean_manifest["programs"] = {}
        for relative in [
            "manifests/source-lock.json",
            "manifests/experiment-programs.json",
            "planning/p0/mcp-contract.json",
        ]:
            copy = fixture / relative
            copy.parent.mkdir(parents=True, exist_ok=True)
            copy.write_bytes((ROOT / relative).read_bytes())
        contract = fixture / "planning/p0/mcp-contract.json"
        contract.write_text(contract.read_text() + "\n ")
        save(target / "manifest.json", clean_manifest)
        knowledge_store.ROOT = fixture
        try:
            try:
                Snapshot(
                    {
                        "path": rel,
                        "build_id": store.build_id,
                        "manifest_sha256": sha(target / "manifest.json"),
                    }
                )
                code = None
            except KnowledgeError as exc:
                code = exc.code
        finally:
            knowledge_store.ROOT = original_root
        check(
            code == "CONTRACT_MISMATCH",
            "changed contract rejected before tools can use mixed schemas",
        )
        # Cursor is bound to the immutable generation independently of source paths.
        old = store.build_id
        cursor = store.cursor("search", {"x": 1}, 1)
        store.build_id = "fixture-new-build"
        try:
            try:
                store.offset(cursor, "search", {"x": 1})
                code = None
            except KnowledgeError as exc:
                code = exc.code
        finally:
            store.build_id = old
        check(code == "STALE_CURSOR", "stale pagination rejected across generations")
        file = temp / "report.json"
        save(file, {"build_id": "fixture", "status": "passed"})
        first = archive_file(file, temp)
        save(file, {"build_id": "fixture", "status": "passed", "rerun": True})
        second = archive_file(file, temp)
        check(
            first != second and first.exists() and second.exists(),
            "same-build regression reports retained by content hash",
        )
    # Physical evidence remains per solver, shared ownership stays explicit.
    # Preserve original cohorts while accepting separately audited additions.
    pd_catalog = ROOT / "experiments/kamino_pd_lab/catalog.json"
    pd_count = len(json.loads(pd_catalog.read_text(encoding="utf-8"))["cases"]) if pd_catalog.exists() else 0
    mujoco_catalog = ROOT / "experiments/mujoco_joint_contact_lab/catalog.json"
    mujoco_count = len(json.loads(mujoco_catalog.read_text(encoding="utf-8"))["cases"]) if mujoco_catalog.exists() else 0
    for solver, count in [("vbd", 17), ("mujoco", 2 + mujoco_count), ("kamino", 10 + pd_count)]:
        check(
            len(store.catalog["solvers"][solver]["experiments"]) == count,
            "current measured pairs " + solver,
        )
    unknown = store.invoke(
        "get_experiment", {"experiment_id": "full_surface", "solver": "mujoco"}
    )
    check(
        unknown["status"] == "no_measured_evidence",
        "no cross-solver experiment borrowing",
    )
    failed = sum(not c["passed"] for c in checks)
    report = {
        "phase": "P5",
        "status": "passed" if not failed else "failed",
        "build_id": store.build_id,
        "passed": len(checks) - failed,
        "failed": failed,
        "checks": checks,
        "fixture_scope": "Synthetic releases and corrupt files existed only under a temporary directory; pinned Newton and real experiment arrays were untouched.",
    }
    save(ROOT / "evaluations/p5-validation.json", report)
    print(json.dumps({k: v for k, v in report.items() if k != "checks"}))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
