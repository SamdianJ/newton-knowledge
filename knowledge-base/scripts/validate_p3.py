"""P3 delivery acceptance: new scenarios, recipe UI and P2 regression."""

import hashlib
import json
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright
from urllib.parse import quote
from knowledge_store import snapshot

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:18448"
checks = []


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def check(value, label):
    checks.append({"check": label, "passed": bool(value)})
    if not value:
        print("FAILED: " + label, flush=True)


def main():
    from maintenance import archive_file

    archive_file(ROOT / "evaluations/p3-validation.json", ROOT)
    store = snapshot()
    current = load("evaluations/p3-mcp-validation.json")
    original = load("evaluations/p2-mcp-validation.json")
    check(
        current["status"] == "passed"
        and len(current["tasks"]) == 12
        and current["build_id"] == store.build_id,
        "twelve new scenarios passed on published build",
    )
    check(
        original["status"] == "passed"
        and len(original["tasks"]) == 12
        and original["build_id"] == store.build_id,
        "all original frozen tasks regress on same build",
    )
    baseline = load(
        "evaluations/history/e510a8e7d1685e1eb83b9f30/p2-mcp-validation.json"
    )
    old = {t["id"]: t for t in baseline["tasks"]}
    check(
        all(
            t["status"] == "passed"
            and not t["missing"]
            and (t["id"] == "T11" or t["calls"] <= old[t["id"]]["calls"])
            for t in original["tasks"]
        ),
        "no original task success or ordinary call-cost regression",
    )
    check(
        original["metrics"]["mean_recall_at_5"]
        >= baseline["metrics"]["mean_recall_at_5"],
        "original initial retrieval recall does not regress",
    )
    check(
        len(store.catalog["extensions"]) == 12
        and sum(e["family"] == "recipe" for e in store.catalog["registry"]["entries"])
        == 6,
        "new recipes separately counted from six frozen base recipes",
    )
    tasks = load("planning/p3/tasks.json")["tasks"]
    for task in tasks:
        r = store.records[task["record_id"]]
        check(
            r["coverage"]["task_validated"] and bool(r.get("validation_evidence")),
            "exact-body accepted task evidence " + task["id"],
        )
        check(
            r["evidence_type"] == "source_checked"
            and not r["coverage"]["experiment_validated"]
            and r["payload"]["runtime_status"] == "not_run",
            "source explanation not physical run " + task["id"],
        )
        check(
            task["query"] not in r["body"] and task["query"] not in r["summary"],
            "frozen task question kept out of indexed text " + task["id"],
        )
        check(
            set(task["source_requirements"]) <= {s["path"] for s in r["source_refs"]},
            "actual source coverage " + task["id"],
        )
        for ref in r["source_refs"]:
            check(
                hashlib.sha256(
                    (ROOT / "sources/newton-v1.7.0" / ref["path"]).read_bytes()
                ).hexdigest()
                == ref["sha256"],
                "source hash " + task["id"] + " " + ref["path"],
            )
    # Preserve the last website phase report before running current regression.
    previous = load("evaluations/p2-validation.json")
    saved = ROOT / "evaluations/history" / previous["build_id"] / "p2-validation.json"
    saved.parent.mkdir(parents=True, exist_ok=True)
    if not saved.exists():
        saved.write_bytes((ROOT / "evaluations/p2-validation.json").read_bytes())
    regression = subprocess.run(
        [
            str(ROOT / ".venv/Scripts/python.exe"),
            "-B",
            "-X",
            "utf8",
            str(ROOT / "scripts/validate_p2.py"),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
    )
    check(
        regression.returncode == 0,
        "full public-layer and website regression: " + regression.stdout[-1000:],
    )
    shots = ROOT / "site/screenshots/p3"
    shots.mkdir(parents=True, exist_ok=True)
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1512, "height": 1080})
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(BASE + "/#/modules", wait_until="domcontentloaded")
        page.wait_for_selector(".grid-3")
        for task in tasks:
            check(
                page.locator(
                    'main a[href="#/record/' + quote(task["record_id"], safe="") + '"]'
                ).count()
                > 0,
                "new recipe visible in library " + task["id"],
            )
        for i, task in enumerate(tasks):
            page.goto(
                BASE
                + "/?p3accept="
                + str(i)
                + "#/record/"
                + quote(task["record_id"], safe=""),
                wait_until="domcontentloaded",
            )
            page.wait_for_selector(".doc-article")
            check(
                "runtime_status=not_run" in page.locator(".doc-article").inner_text(),
                "recipe runtime scope visible " + task["id"],
            )
            check(
                page.locator('.record-source a[href^="#/source/"]').count() > 0,
                "recipe has exact local source navigation " + task["id"],
            )
            if task["id"] in ("X05", "X11", "X12"):
                solver = store.records[task["record_id"]]["owner_solver"]
                check(
                    page.locator("#solver-select").input_value() == solver,
                    "specialized recipe keeps owner solver " + task["id"],
                )
            if task["id"] in ("X05", "X10", "X11"):
                page.screenshot(path=str(shots / (task["id"] + ".png")))
        page.set_viewport_size({"width": 390, "height": 844})
        page.goto(
            BASE + "/?p3mobile=1#/record/" + quote(tasks[0]["record_id"], safe=""),
            wait_until="domcontentloaded",
        )
        page.wait_for_selector(".doc-article")
        check(
            page.evaluate("document.documentElement.scrollWidth<=innerWidth+1"),
            "new recipe mobile layout fits screen",
        )
        browser.close()
    check(not errors, "no new recipe browser errors " + str(errors))
    failed = sum(not c["passed"] for c in checks)
    report = dict(
        phase="P3",
        status="passed" if not failed else "failed",
        build_id=store.build_id,
        passed=len(checks) - failed,
        failed=failed,
        checks=checks,
        evidence=[
            "planning/p3/tasks.json",
            "evaluations/p3-mcp-validation.json",
            "evaluations/p3-mcp-trace.json",
            "evaluations/p2-mcp-validation.json",
            "evaluations/p2-validation.json",
            "site/screenshots/p3/",
        ],
    )
    (ROOT / "evaluations/p3-validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in report.items() if k != "checks"}), flush=True)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
