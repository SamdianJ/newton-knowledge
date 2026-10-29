"""Common-layer coverage, version integrity and browser acceptance for P2."""

import hashlib
import json
import subprocess
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import quote
from playwright.sync_api import sync_playwright
from knowledge_store import snapshot

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:18448"
checks = []


def check(value, label):
    checks.append({"check": label, "passed": bool(value)})
    if not value:
        print("FAILED: " + label, flush=True)


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def get(path):
    with urlopen(BASE + path, timeout=20) as response:
        return json.load(response)


def main():
    from maintenance import archive_file

    archive_file(ROOT / "evaluations/p2-validation.json", ROOT)
    store = snapshot()
    entries = store.catalog["registry"]["entries"]
    mcp = load("evaluations/p2-mcp-validation.json")
    check(
        mcp["status"] == "passed" and mcp["build_id"] == store.build_id,
        "real stdio acceptance uses published generation",
    )
    check(
        len(mcp["tasks"]) == 12
        and all(t["status"] == "passed" and not t["missing"] for t in mcp["tasks"]),
        "every frozen task passes independently",
    )
    for family, count in [
        ("api", 12),
        ("concept", 14),
        ("solver", 8),
        ("topic", 8),
        ("stage", 7),
        ("recipe", 6),
    ]:
        check(
            sum(e["family"] == family for e in entries) == count,
            "separate coverage denominator " + family,
        )
    paths = {}
    for entry in entries:
        r = store.records[entry["id"]]
        coverage = r["coverage"]
        check(
            r["content_status"] == "published"
            and coverage["indexed"]
            and "待建设" not in r["body"],
            "actual authored content " + entry["id"],
        )
        if entry["target_depth"] != "I":
            check(coverage["explained"], "explained coverage " + entry["id"])
        if entry["target_depth"] == "T":
            check(
                coverage["task_validated"] and r.get("validation_evidence"),
                "body-specific accepted task receipt " + entry["id"],
            )
        check(
            bool(r["source_refs"]) and COMMIT_IN_BODY(r["body"]),
            "pinned provenance " + entry["id"],
        )
        for ref in r["source_refs"]:
            paths[ref["path"]] = ref["sha256"]
        if entry["family"] == "stage":
            check(
                bool(entry["official_url"])
                and bool(entry["summary"])
                and bool(entry["description"]),
                "stage summary and official reading link " + entry["id"],
            )
        if entry["family"] == "recipe":
            check(
                all(
                    s in r["body"]
                    for s in (
                        "Setup",
                        "每仿真子步",
                        "每控制帧",
                        "每输出帧",
                        "Reset / Model 更新",
                    )
                ),
                "recipe scheduling contract " + entry["id"],
            )
    for path, expected in paths.items():
        check(
            hashlib.sha256(
                (ROOT / "sources/newton-v1.7.0" / path).read_bytes()
            ).hexdigest()
            == expected,
            "referenced source hash " + path,
        )
    baseline = load("planning/p0/migration-baseline.json")
    for old in baseline["search_records"]:
        check(
            store.resolve(old["id"]) in store.records,
            "legacy ID still resolves " + old["id"],
        )
    for e in baseline["experiments"]:
        for path, expected in e["files"].items():
            check(
                hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected,
                "saved VBD raw unchanged " + path,
            )
    check(
        get("/api/health")["build_id"]
        == get("/api/catalog")["build_id"]
        == get("/api/graph")["build_id"]
        == store.build_id,
        "HTTP data and index generation coherent",
    )
    cli = subprocess.run(
        [
            str(ROOT / ".venv/Scripts/python.exe"),
            "-B",
            "-X",
            "utf8",
            str(ROOT / "scripts/retrieve.py"),
            "--query",
            "SensorContact",
            "--solver",
            "shared",
            "--limit",
            "3",
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
    )
    check(
        cli.returncode == 0 and json.loads(cli.stdout)["build_id"] == store.build_id,
        "CLI uses same canonical build",
    )
    shots = ROOT / "site/screenshots/p2"
    shots.mkdir(parents=True, exist_ok=True)
    errors = []
    external = []
    failures = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1512, "height": 1080})
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on(
            "request",
            lambda r: (
                external.append(r.url)
                if r.url.startswith("http") and not r.url.startswith(BASE)
                else None
            ),
        )
        page.on(
            "response",
            lambda r: failures.append((r.status, r.url)) if r.status >= 400 else None,
        )
        visits = 0

        def visit(route, selector="h1"):
            nonlocal visits
            visits += 1
            page.goto(
                BASE + "/?p2accept=" + str(visits) + route,
                wait_until="domcontentloaded",
            )
            page.wait_for_selector(selector)
            check(not page.locator(".notice.error").count(), "UI route " + route)

        visit("#/")
        check(
            page.locator("[data-solver-card]").count() == 8,
            "all backends visible at root",
        )
        check(
            "Coding style" in page.locator("main").inner_text()
            and "Newton test" in page.locator("main").inner_text(),
            "root contains coding and test summaries",
        )
        page.screenshot(path=str(shots / "home.png"), full_page=True)
        visit("#/workflow", "details.flow-stage")
        check(
            page.locator("details.flow-stage").count() == 5
            and page.locator("details.loop-stage").count() == 3,
            "five stages with three nested loop phases",
        )
        page.locator("details.flow-stage").first.locator("summary").click()
        check(
            "输入：原语/URDF/MJCF/USD"
            in page.locator("details.flow-stage").first.inner_text()
            and "输出：ModelBuilder"
            in page.locator("details.flow-stage").first.inner_text(),
            "expanded stage gives input/output summary",
        )
        check(
            page.locator("details.flow-stage")
            .first.locator('a[href^="https://newton-physics.github.io"]')
            .count()
            > 0,
            "expanded stage links official Newton docs",
        )
        page.screenshot(path=str(shots / "workflow.png"), full_page=True)
        for entry in entries:
            visit("#/record/" + quote(entry["id"], safe=""), ".doc-article")
            check(
                "待建设" not in page.locator(".badges").inner_text(),
                "no planned placeholder for " + entry["id"],
            )
            if entry["family"] in ("stage", "recipe", "api", "topic", "concept"):
                check(
                    page.locator(".source-summary").count() > 0,
                    "public knowledge source panel " + entry["id"],
                )
        visit("#/record/" + quote("recipe:ik-mujoco-contact", safe=""), ".doc-article")
        check(
            "MuJoCo Warp" in page.locator(".doc-article").inner_text()
            and "joint_coord_count" in page.locator(".doc-article").inner_text(),
            "recipe displays actual backend and layout conditions",
        )
        page.locator("#load-relations").click()
        page.wait_for_selector("#relations .related-item")
        check(
            page.locator("#relations .related-item").count() > 0,
            "readable graph relationships in UI",
        )
        page.evaluate("scrollTo(0,0)")
        page.screenshot(path=str(shots / "recipe.png"))
        for solver, count in [("vbd", 48), ("mujoco", 35), ("kamino", 86)]:
            visit("#/solvers/" + solver + "/parameters", "#parameter-rows tr")
            check(
                page.locator("#parameter-rows tr").count() == count,
                "scoped parameter count " + solver,
            )
        visit("#/solvers/vbd/parameters", "#parameter-rows tr")
        page.locator("#solver-select").select_option("mujoco")
        page.wait_for_timeout(250)
        check(
            page.locator("#solver-select").input_value() == "mujoco"
            and page.locator("#parameter-rows tr").count() == 35,
            "changing solver changes dataset and retains section",
        )
        visit("#setting/full_surface", ".kv")
        check(
            "shared" in page.locator(".badges").inner_text()
            and "碰撞检测" in page.locator("#crumb").inner_text(),
            "shared pipeline owner and breadcrumb",
        )
        visit("#experiments?case=full_surface&view=3d", "iframe")
        frame = page.frame_locator("iframe")
        frame.locator(
            '#experiments tr:visible canvas[data-renderer="webgl"]'
        ).first.wait_for(timeout=30000)
        check(
            frame.locator("#experiments tr:visible").count() == 1,
            "existing real VBD 3D replay preserved",
        )
        page.screenshot(path=str(shots / "full-surface.png"), full_page=True)
        for solver in ("mujoco", "kamino"):
            if store.catalog["solvers"][solver]["experiments"]:
                visit("#/solvers/" + solver + "/experiments", "iframe")
                check(
                    "solver_parameter_lab"
                    in page.locator('iframe[src*="solver_parameter_lab/index.html"]').get_attribute("src")
                    and ("solver=" + solver)
                    in page.locator('iframe[src*="solver_parameter_lab/index.html"]').get_attribute("src"),
                    "scoped measured lab, no VBD fallback " + solver,
                )
            else:
                visit("#/solvers/" + solver + "/experiments", ".empty")
                check(
                    not page.locator("iframe").count(),
                    "measurement empty state no VBD fallback " + solver,
                )
        visit(
            "#/search?q=CONTACT_F&solver=mujoco&include_shared=true&stage=output",
            ".search-result",
        )
        check(
            all(
                s in ("shared", "mujoco")
                for s in page.locator(
                    ".search-result .badge:first-child"
                ).all_text_contents()
            ),
            "cross-module scoped search UI",
        )
        visit("#/document/solvers/vbd/theory.md", ".katex")
        page.wait_for_selector(".mermaid svg")
        check(
            page.locator(".katex").count() >= 4,
            "math and source-backed legacy theory remains renderable",
        )
        for doc in baseline["documents"]:
            check(
                bool(get("/api/document?path=" + quote(doc["path"]))["html"]),
                "all original document routes " + doc["path"],
            )
        page.set_viewport_size({"width": 390, "height": 844})
        visit("#/workflow", "details.flow-stage")
        check(
            page.evaluate("document.documentElement.scrollWidth<=innerWidth+1"),
            "mobile workflow fits screen",
        )
        page.screenshot(path=str(shots / "mobile.png"), full_page=True)
        browser.close()
    check(not errors, "no browser errors " + str(errors))
    check(not failures, "no failed UI requests " + str(failures))
    check(not external, "offline UI has no external requests " + str(external))
    failed = sum(not c["passed"] for c in checks)
    report = dict(
        phase="P2",
        status="passed" if not failed else "failed",
        build_id=store.build_id,
        passed=len(checks) - failed,
        failed=failed,
        checks=checks,
        evidence=[
            "evaluations/p2-mcp-validation.json",
            "evaluations/p2-mcp-trace.json",
            "site/screenshots/p2/",
            "knowledge/validation-receipts.json",
        ],
        scope="Coverage, provenance, website/CLI/MCP and frozen knowledge tasks. No upstream full test or new physical experiment is claimed.",
    )
    (ROOT / "evaluations/p2-validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in report.items() if k != "checks"}), flush=True)
    if failed:
        raise SystemExit(1)


def COMMIT_IN_BODY(body):
    return "7e75abe28b8d69522bc0b34837aaed2c303dff5a" in body


if __name__ == "__main__":
    main()
