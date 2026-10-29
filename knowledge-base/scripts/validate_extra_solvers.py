"""Audit additional solver coverage, source/paper integrity, graph and generated references."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "sources/newton-v1.7.0"
CHECKS = []


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def check(condition, label):
    CHECKS.append({"check": label, "passed": bool(condition)})
    if not condition:
        print("FAILED:", label)


def main():
    manifest = load("manifests/extra-solvers-1.7.0.json")
    head = subprocess.check_output(["git", "-C", str(SOURCE), "rev-parse", "HEAD"], text=True).strip()
    check(head == manifest["commit"], "official source HEAD is still the pinned release")
    check(
        not subprocess.check_output(["git", "-C", str(SOURCE), "status", "--porcelain"], text=True).strip(),
        "official source snapshot has no edits",
    )
    for item in manifest["inspected_files"]:
        check(
            hashlib.sha256((SOURCE / item["path"]).read_bytes()).hexdigest() == item["sha256"],
            "inspected source hash: " + item["path"],
        )
    for paper in load("manifests/extra-papers.json"):
        p = ROOT / paper["local_path"]
        check(
            p.read_bytes().startswith(b"%PDF") and hashlib.sha256(p.read_bytes()).hexdigest() == paper["sha256"],
            "original paper hash: " + paper["id"],
        )
        text = (ROOT / paper["text_path"]).read_text(encoding="utf-8")
        check(
            text.count("--- PAGE ") == paper["pages"] and len(text) > 5000,
            "per-page paper text available: " + paper["id"],
        )
    for solver, clsname in [("mujoco", "SolverMuJoCo"), ("kamino", "SolverKamino")]:
        c = load(f"solvers/{solver}/catalog.json")
        path = SOURCE / f"newton/_src/solvers/{solver}/solver_{solver}.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == clsname)
        init = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__")
        names = [a.arg for a in init.args.args[1:] + init.args.kwonlyargs]
        check(
            names == [p["name"] for p in c["parameters"] if p["layer"] == "solver_constructor"],
            "complete constructor signature: " + solver,
        )
        if solver == "kamino":
            config_tree = ast.parse((SOURCE / "newton/_src/solvers/kamino/config.py").read_text(encoding="utf-8"))
            configs = [("Config", "config", tree), ("ResetConfig", "reset", tree)] + [
                (cls, "config." + prefix, config_tree)
                for cls, prefix in [
                    ("CollisionDetectorConfig", "collision_detector"),
                    ("ConstraintStabilizationConfig", "constraints"),
                    ("ConstrainedDynamicsConfig", "dynamics"),
                    ("PADMMSolverConfig", "padmm"),
                    ("DVISolverConfig", "dvi"),
                    ("ForwardKinematicsSolverConfig", "fk"),
                    ("MaterialManagerConfig", "materials"),
                ]
            ]
            expected = []
            for name, prefix, owner in configs:
                config = next(n for n in ast.walk(owner) if isinstance(n, ast.ClassDef) and n.name == name)
                expected.extend(
                    prefix + "." + ast.unparse(n.target) for n in config.body if isinstance(n, ast.AnnAssign)
                )
            actual = [p["name"] for p in c["parameters"] if p["layer"] != "solver_constructor"]
            check(actual == expected, "all public Kamino config and reset dataclass fields included in source order")
        check(
            not c["experiments"] and all(not p["experiments"] for p in c["parameters"] + c["model_inputs"]),
            "no invented measured evidence: " + solver,
        )
        check(
            all(d["evidence_type"] == "proposed" and d["status"] == "not_run" for d in c["diagnostics"]),
            "diagnostic plans explicitly proposed: " + solver,
        )
        for file in (ROOT / "solvers" / solver).glob("*.md"):
            text = file.read_text(encoding="utf-8")
            check(
                not re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", text),
                "no escaped math control characters: " + file.name + " " + solver,
            )
            check(
                all(
                    (file.parent / url.split("#")[0]).exists()
                    for url in re.findall(r"\]\(([^)]+)\)", text)
                    if "://" not in url and not url.startswith("#")
                ),
                "local references resolve: " + file.name + " " + solver,
            )

        def visit(value):
            if isinstance(value, dict):
                if {"path", "line", "commit", "url"} <= value.keys():
                    lines = (SOURCE / value["path"]).read_text(encoding="utf-8").splitlines()
                    check(
                        1 <= value["line"] <= len(lines) and manifest["commit"] in value["url"],
                        "valid pinned source anchor: " + solver + " " + value["path"] + ":" + str(value["line"]),
                    )
                for item in value.values():
                    visit(item)
            elif isinstance(value, list):
                for item in value:
                    visit(item)

        visit(c)
    graph = load("site/dist/graph.json")
    ids = [n["id"] for n in graph["nodes"]]
    idset = set(ids)
    check(len(ids) == len(idset), "combined graph IDs are unique")
    check(
        all(e["source"] in idset and e["target"] in idset for e in graph["edges"]),
        "combined graph has no dangling relations",
    )
    result = {
        "passed": sum(c["passed"] for c in CHECKS),
        "failed": sum(not c["passed"] for c in CHECKS),
        "checks": CHECKS,
    }
    (ROOT / "evaluations/extra-solvers-validation.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in result.items() if k != "checks"}))
    if result["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
