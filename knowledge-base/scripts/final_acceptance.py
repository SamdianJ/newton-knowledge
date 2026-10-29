"""Bind final reports and stage delivery to one published knowledge generation."""

import hashlib
import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen
from playwright.sync_api import sync_playwright
from knowledge_store import snapshot
from maintenance import archive_file

ROOT = Path(__file__).resolve().parents[1]


def main():
    archive_file(ROOT / "evaluations/delivery-validation.json", ROOT)
    store = snapshot()
    checks = []
    evidence = {}

    def check(value, name):
        checks.append({"name": name, "passed": bool(value)})

    names = [
        "p2-mcp-validation.json",
        "p3-mcp-validation.json",
        "p4-mcp-validation.json",
        "p5-mcp-validation.json",
        "p2-validation.json",
        "p3-validation.json",
        "p4-validation.json",
        "p5-validation.json",
        "p5-integrity-validation.json",
        "p4-physics-validation.json",
        "p0-validation.json",
    ]
    for name in names:
        file = ROOT / "evaluations" / name
        data = json.loads(file.read_text(encoding="utf-8"))
        check(data["status"] == "passed" and not data["failed"], "passed " + name)
        if data.get("build_id"):
            check(
                data["build_id"] == store.build_id, "same published generation " + name
            )
        evidence[name] = {
            "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
            "passed": data["passed"],
            "failed": data["failed"],
            "build_id": data.get("build_id"),
            "phase": data["phase"],
        }
    with urlopen("http://127.0.0.1:18448/api/health", timeout=20) as response:
        health = json.load(response)
    check(health["build_id"] == store.build_id, "live server generation")
    check(
        store.catalog["registry"]["counts"]
        == {"api": 12, "concept": 14, "solver": 8, "topic": 8, "stage": 7, "recipe": 6},
        "frozen independent scope denominators",
    )
    check(
        sum(r["coverage"]["task_validated"] for r in store.records.values()) == 41,
        "41 current exact-body/source receipts",
    )
    errors = []
    shots = ROOT / "site/screenshots/p5"
    shots.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1050})
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(
            "http://127.0.0.1:18448/#/record/"
            + quote("page:knowledge/pages/development/maintenance.md", safe=""),
            wait_until="domcontentloaded",
        )
        page.wait_for_selector(".doc-article")
        check(
            "版本差异" in page.locator("main h1").inner_text()
            and "maintain.py" in page.locator(".doc-article").inner_text(),
            "maintenance instructions readable on website",
        )
        page.screenshot(path=str(shots / "maintenance.png"))
        page.goto("http://127.0.0.1:18448/", wait_until="domcontentloaded")
        page.wait_for_selector('[data-solver-card="kamino"]')
        check(
            page.locator('[data-solver-card="mujoco"]').inner_text().find("2 组实测")
            >= 0
            and page.locator('[data-solver-card="vbd"]').inner_text().find("17 组实测")
            >= 0,
            "live solver cards show actual measured evidence",
        )
        page.screenshot(path=str(shots / "home.png"))
        browser.close()
    check(not errors, "final browser console " + str(errors))
    failed = sum(not c["passed"] for c in checks)
    report = {
        "phase": "P5",
        "status": "passed" if not failed else "failed",
        "build_id": store.build_id,
        "version": "1.7.0",
        "source_commit": store.catalog["commit"],
        "passed": len(checks) - failed,
        "failed": failed,
        "checks": checks,
        "evidence": evidence,
        "scope": {
            "API_modules": 12,
            "concepts": 14,
            "backends": 8,
            "cross_stage_topics": 8,
            "actual_stages": 7,
            "base_recipes": 6,
            "additional_recipes": 12,
            "documents": len(store.documents),
            "canonical_records": len(store.records),
            "task_validated_records": 41,
            "measured_pairs": {
                s: len(c["experiments"]) for s, c in store.catalog["solvers"].items()
            },
            "new_solver_primary_runs": 8,
            "new_solver_independent_reproduction_runs": 8,
            "not_claimed": [
                "GPU physical validation",
                "full upstream Newton suite",
                "free-form LLM task quality or actual billing tokens",
                "complete parameter experiments for all backends",
                "an actual additional Newton release",
            ],
        },
    }
    (ROOT / "evaluations/delivery-validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                k: v
                for k, v in report.items()
                if k not in ["checks", "evidence", "scope"]
            }
        )
    )
    if failed:
        print([c for c in checks if not c["passed"]])
        raise SystemExit(1)


if __name__ == "__main__":
    main()
