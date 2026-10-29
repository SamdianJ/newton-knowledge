"""Pure verification primitives for build publication and maintenance fixtures."""

from __future__ import annotations
import hashlib
import json


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_sources(base, lock):
    base = base.resolve()
    errors = []
    for relative, expected in lock["files"].items():
        path = (base / relative).resolve()
        if not path.is_relative_to(base) or not path.is_file():
            errors.append({"path": relative, "error": "missing_or_outside_root"})
        elif sha(path) != expected:
            errors.append({"path": relative, "error": "hash_changed"})
    return errors


def source_fingerprint(refs):
    values = sorted(
        (r["path"], r.get("line", 1), r.get("sha256"), r.get("commit")) for r in refs
    )
    return hashlib.sha256(
        json.dumps(values, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def validate_receipt(body, receipt, root, source_refs=None):
    if sha(root / receipt["report"]) != receipt["report_sha256"]:
        raise ValueError("Validation report hash changed: " + receipt["report"])
    return (
        source_refs is None
        or receipt.get("source_refs_sha256") == source_fingerprint(source_refs)
    ) and hashlib.sha256(body.encode()).hexdigest() == receipt["body_sha256"]


def promote(staging, destination):
    """Only complete, verified staging directories can become immutable builds."""
    manifest = json.loads((staging / "manifest.json").read_text(encoding="utf-8"))
    if staging.resolve() == destination.resolve():
        raise ValueError("Staging must be distinct")
    workspace = staging.parent.parent.resolve()
    if not staging.resolve().is_relative_to(
        workspace
    ) or not destination.resolve().is_relative_to(workspace):
        raise ValueError("Promotion must stay inside its knowledge workspace")
    required = {
        "catalog.json",
        "records.json",
        "graph.json",
        "documents.json",
        "knowledge.sqlite",
    }
    if not required <= set(manifest["files"]):
        raise ValueError("Incomplete staging manifest")
    for name, expected in manifest["files"].items():
        path = (staging / name).resolve()
        if (
            not path.is_relative_to(staging.resolve())
            or not path.is_file()
            or sha(path) != expected
        ):
            raise ValueError("Staging integrity failure: " + name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging.rename(destination)


def archive_file(path, root):
    """Archive each original report/trace before overwrite, including same-build reruns."""
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    build = data.get("build_id") if isinstance(data, dict) else None
    if not build and isinstance(data, list) and data:
        for item in data:
            payload = (
                item.get("result") or item.get("response") or item.get("data") or {}
            )
            if isinstance(payload, dict) and payload.get("build_id"):
                build = payload["build_id"]
                break
    build = build or "unbound"
    target = (
        root
        / "evaluations/history"
        / build
        / (path.stem + "-" + sha(path)[:16] + path.suffix)
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and sha(target) != sha(path):
        raise ValueError("Archive conflict")
    if not target.exists():
        target.write_bytes(path.read_bytes())
    return target
