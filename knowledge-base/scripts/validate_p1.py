"""Migration acceptance for canonical data, local website and legacy routes."""

import hashlib
import json
import subprocess
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen
from playwright.sync_api import sync_playwright
from knowledge_store import snapshot

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:18448"
checks = []


def check(value, label):
    checks.append({"check": label, "passed": bool(value)})
    if not value:
        print("FAILED: " + label)


def get(path):
    with urlopen(BASE + path, timeout=20) as response:
        return json.load(response)


def main():
    store = snapshot()
    baseline = json.loads(
        (ROOT / "planning/p0/migration-baseline.json").read_text(encoding="utf-8")
    )
    check(
        len(store.catalog["solvers"]) == 8,
        "three deep solver templates and five index templates",
    )
    for old in baseline["search_records"]:
        check(
            store.resolve(old["id"]) in store.records,
            "old searchable ID retained or mapped: " + old["id"],
        )
    for old in baseline["documents"]:
        check(
            old["path"] in store.documents,
            "all 31 original docs remain readable: " + old["path"],
        )
    for rid in baseline["parameter_ids"]:
        check(
            rid in store.records and store.records[rid]["record_type"] == "parameter",
            "all 169 parameter IDs retained: " + rid,
        )
    for old in baseline["experiments"]:
        check(
            old["id"] in store.records, "original measured experiment ID " + old["id"]
        )
        for path, digest in old["files"].items():
            check(
                hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest,
                "original raw data unchanged " + path,
            )
    for rid in baseline["graph_ids"]:
        check(rid in store.nodes, "original graph ID retained " + rid)
    check(
        all(
            e["source"] in store.nodes and e["target"] in store.nodes
            for e in store.graph["edges"]
        ),
        "no dangling graph edges",
    )
    check(
        get("/api/health")["build_id"]
        == store.build_id
        == get("/api/catalog")["build_id"]
        == get("/api/graph")["build_id"],
        "HTTP catalog, graph, health and records share build",
    )
    check(
        store.catalog["total_counts"]["parameters"] == 171
        and store.catalog["total_counts"]["solver_parameters"] == 169,
        "shared and solver parameter counts explicit",
    )
    before = hashlib.sha256((store.path / "manifest.json").read_bytes()).hexdigest()
    build = subprocess.run(
        [
            str(ROOT / ".venv/Scripts/python.exe"),
            "-B",
            str(ROOT / "scripts/build_platform.py"),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=45,
    )
    check(
        build.returncode == 0 and '"reused": true' in build.stdout,
        "identical inputs reuse immutable snapshot",
    )
    check(
        hashlib.sha256((store.path / "manifest.json").read_bytes()).hexdigest()
        == before,
        "identical rebuild leaves manifest unchanged",
    )
    shots = ROOT / "site/screenshots/p1"
    shots.mkdir(parents=True, exist_ok=True)
    errors = []
    external = []
    failures = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
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
                BASE + "/?acceptance=" + str(visits) + route,
                wait_until="domcontentloaded",
            )
            page.wait_for_selector(selector)
            check(page.locator(".notice.error").count() == 0, "website route " + route)

        visit("#/")
        check(
            page.locator("[data-solver-card]").count() == 8,
            "Newton home includes eight solvers",
        )
        check(
            page.locator('nav a[href="#/solvers/vbd/parameters"]').count() == 0,
            "global navigation has no hidden VBD directory",
        )
        page.screenshot(path=str(shots / "home.png"), full_page=True)
        visit("#/workflow", "details.flow-stage")
        check(
            page.locator("details.flow-stage").count() == 7,
            "all five stages and three loop stages present without duplicate loop shell",
        )
        page.locator("details.flow-stage").first.locator("summary").click()
        check(
            page.locator("details.flow-stage").first.get_attribute("open") is not None,
            "flow stages expand",
        )
        page.screenshot(path=str(shots / "workflow.png"), full_page=True)
        for solver, count in [("vbd", 48), ("mujoco", 35), ("kamino", 86)]:
            visit("#/solvers/" + solver + "/parameters", "#parameter-rows tr")
            check(
                page.locator("#parameter-rows tr").count() == count,
                "correct current solver rows " + solver,
            )
            check(
                page.locator("#solver-select").input_value() == solver,
                "current solver shown " + solver,
            )
            first = store.catalog["solvers"][solver]["parameters"][1]["name"]
            page.locator("#parameter-filter").fill(first)
            page.locator("#parameter-rows a").filter(has_text=first).first.click()
            page.wait_for_selector(".kv")
            check(
                page.locator("h1").inner_text() == first,
                "parameter opens correct detail " + solver,
            )
            check(
                page.locator(".badge")
                .filter(
                    has_text=store.catalog["solvers"][solver]["parameters"][1].get(
                        "owner", ""
                    )
                )
                .count()
                > 0,
                "parameter owner visible " + solver,
            )
            page.screenshot(
                path=str(shots / (solver + "-parameter.png")), full_page=True
            )
        visit("#/solvers/vbd/parameters", "#parameter-rows")
        page.locator("#solver-select").select_option("mujoco")
        page.wait_for_selector("#parameter-rows tr")
        page.wait_for_timeout(100)
        check(
            "/mujoco/parameters" in page.url
            and page.locator("#parameter-rows tr").count() == 35,
            "solver switch preserves tab and changes context",
        )
        for solver in store.catalog["solvers"]:
            visit(
                "#/solvers/"
                + solver
                + "/experiments"
                + ("?case=iterations" if solver == "vbd" else ""),
                "iframe" if solver == "vbd" else ".empty,.notice.warm",
            )
            if solver != "vbd":
                check(
                    page.locator("iframe").count() == 0,
                    "no borrowed VBD experiment iframe " + solver,
                )
        for solver in (
            "featherstone",
            "implicit-mpm",
            "semi-implicit",
            "style3d",
            "xpbd",
        ):
            visit("#/solvers/" + solver)
            check(
                "源码索引级" in page.locator("main").inner_text(),
                "honest index coverage " + solver,
            )
        legacy = [
            ("#home", "#/"),
            ("#parameters", "#/solvers/vbd/parameters"),
            ("#solver/mujoco/parameters", "#/solvers/mujoco/parameters"),
            (
                "#solver/kamino/model/"
                + quote(store.catalog["solvers"]["kamino"]["model_inputs"][0]["field"]),
                "#/solvers/kamino/inputs/",
            ),
            ("#setting/full_surface", "#/solvers/shared/parameters/"),
            (
                "#doc/solvers/vbd/theory.md?section=some-preserved-anchor",
                "#/document/solvers/vbd/theory.md?section=some-preserved-anchor",
            ),
            (
                "#source/newton/_src/sim/collide.py?line=1338",
                "#/source/newton/_src/sim/collide.py?line=1338",
            ),
            ("#evidence/" + quote("c:dat"), "#/record/"),
        ]
        for old, new in legacy:
            visit(old)
            check(new in page.url, "legacy route semantic mapping " + old)
        visit("#doc/solvers/vbd/theory.md", ".doc-article .katex")
        page.wait_for_selector(".mermaid svg")
        check(page.locator(".katex").count() >= 4, "legacy theory math retained")
        page.screenshot(path=str(shots / "theory.png"), full_page=True)
        visit("#experiments?case=iterations&view=3d", "iframe")
        check(
            "case=iterations" in page.locator("iframe").get_attribute("src"),
            "legacy case and view query preserved",
        )
        frame = page.frame_locator("iframe")
        frame.locator(
            '#experiments tr:visible canvas[data-renderer="webgl"]'
        ).first.wait_for(timeout=30000)
        check(
            frame.locator("#experiments tr:visible").count() == 1,
            "real existing 3D A/B selected case renders",
        )
        page.screenshot(path=str(shots / "experiment-3d.png"), full_page=True)
        visit("#/search?q=iterations&solver=mujoco", ".search-result")
        check(
            all(
                s == "mujoco"
                for s in page.locator(
                    ".search-result .badge:first-child"
                ).all_text_contents()
            ),
            "HTTP search scope applied",
        )
        page.set_viewport_size({"width": 390, "height": 844})
        visit("#/")
        check(
            page.evaluate("document.documentElement.scrollWidth<=innerWidth+1"),
            "mobile homepage fits viewport",
        )
        page.locator("#menu").click()
        check(page.locator("#sidebar").is_visible(), "mobile navigation available")
        page.screenshot(path=str(shots / "mobile.png"), full_page=True)
        browser.close()
    check(not errors, "no browser JavaScript errors: " + str(errors))
    check(not external, "no external requests required: " + str(external))
    check(not failures, "no failed UI network responses: " + str(failures))
    mcp = json.loads(
        (ROOT / "evaluations/p1-mcp-validation.json").read_text(encoding="utf-8")
    )
    check(
        mcp["status"] == "passed" and mcp["build_id"] == store.build_id,
        "external stdio migration acceptance shares build",
    )
    failed = sum(not c["passed"] for c in checks)
    report = {
        "phase": "P1",
        "status": "passed" if not failed else "failed",
        "build_id": store.build_id,
        "passed": len(checks) - failed,
        "failed": failed,
        "checks": checks,
        "evidence": [
            "evaluations/p1-mcp-validation.json",
            "evaluations/p1-mcp-trace.json",
            "site/screenshots/p1/",
        ],
    }
    (ROOT / "evaluations/p1-validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in report.items() if k != "checks"}))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
