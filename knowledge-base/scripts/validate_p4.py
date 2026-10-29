"""P4 physical, interface and actual replay acceptance."""

import hashlib
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from knowledge_store import snapshot

ROOT = Path(__file__).resolve().parents[1]


def main():
    from maintenance import archive_file

    archive_file(ROOT / "evaluations/p4-validation.json", ROOT)
    checks = []

    def check(value, name):
        checks.append({"name": name, "passed": bool(value)})

    def load(path):
        return json.loads((ROOT / path).read_text(encoding="utf-8"))

    store = snapshot()
    physics = load("evaluations/p4-physics-validation.json")
    mcp = load("evaluations/p4-mcp-validation.json")
    check(
        physics["status"] == "passed" and physics["pairs"] == 4,
        "four independently verified physical pairs",
    )
    check(
        mcp["status"] == "passed" and mcp["build_id"] == store.build_id,
        "real stdio on current generation",
    )
    for solver in ["mujoco", "kamino"]:
        original_ids = {c["id"] for c in load("experiments/solver_parameter_lab/catalog.json")["cases"] if c["solver"] == solver}
        check(
            len(original_ids) == 2 and original_ids <= {c["id"] for c in store.catalog["solvers"][solver]["experiments"]},
            "two original P4 valid pairs retained " + solver,
        )
    baseline = load("planning/p0/migration-baseline.json")
    for case in baseline["experiments"]:
        for path, expected in case["files"].items():
            check(
                hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected,
                "original VBD raw unchanged " + path,
            )
    check(
        hashlib.sha256(
            (ROOT / "experiments/vbd_parameter_lab/run_lab.py").read_bytes()
        ).hexdigest()
        == "2449d08a6b410b91fd9efa4e6547f0f5ba8949814be05d6fab14369a3d0e978a",
        "original VBD runner unchanged",
    )
    shots = ROOT / "site/screenshots/p4"
    shots.mkdir(parents=True, exist_ok=True)
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1050})
        page.on("pageerror", lambda e: errors.append(str(e)))
        for solver in ["mujoco", "kamino"]:
            page.goto(
                "http://127.0.0.1:18448/#/solvers/" + solver + "/experiments",
                wait_until="domcontentloaded",
            )
            page.wait_for_selector("iframe")
            frame = page.frame_locator('iframe[src*="solver_parameter_lab/index.html"]')
            frame.locator(".experiment").first.wait_for()
            check(
                frame.locator(".experiment").count() == 2,
                "only scoped cases rendered " + solver,
            )
            check(
                frame.locator("canvas").count() == 4,
                "two pairs actual 3D canvases " + solver,
            )
            for case in store.catalog["solvers"][solver]["experiments"]:
                if case.get("artifact_root"):
                    continue  # Separately accepted by validate_kamino_mechanisms.py.
                row = frame.locator('[data-case="' + case["id"] + '"]')
                slider = row.locator("input")
                slider.fill(str(int(slider.get_attribute("max")) // 2))
                slider.dispatch_event("input")
                check(
                    row.locator("output").inner_text() != "0.000 s",
                    "scrub measured time " + case["id"],
                )
                check(
                    row.locator("img").evaluate("(e)=>e.complete&&e.naturalWidth>0"),
                    "complete measured curve " + case["id"],
                )
                row.locator(".fit").click()
                row.locator(".reset").click()
                canvas = row.locator("canvas").first
                box = canvas.bounding_box()
                page.mouse.move(box["x"] + 100, box["y"] + 100)
                page.mouse.down()
                page.mouse.move(box["x"] + 160, box["y"] + 120)
                page.mouse.up()
                row.screenshot(path=str(shots / (case["id"] + ".png")))
                check(
                    row.locator('a[href$=".npz"]').count() == 2,
                    "download raw A/B " + case["id"],
                )
            page.screenshot(path=str(shots / (solver + ".png")))
        page.set_viewport_size({"width": 390, "height": 844})
        page.goto(
            "http://127.0.0.1:18448/files/experiments/solver_parameter_lab/index.html?solver=kamino&case=kamino_contact_stabilization"
        )
        page.wait_for_selector("canvas")
        check(page.locator(".experiment").count() == 1, "case deep link isolated")
        check(
            page.evaluate("document.documentElement.scrollWidth<=innerWidth+1"),
            "mobile lab no horizontal overflow",
        )
        page.screenshot(path=str(shots / "mobile.png"), full_page=True)
        browser.close()
    check(not errors, "browser errors " + str(errors))
    failed = sum(not c["passed"] for c in checks)
    report = {
        "phase": "P4",
        "status": "passed" if not failed else "failed",
        "build_id": store.build_id,
        "passed": len(checks) - failed,
        "failed": failed,
        "checks": checks,
        "evidence": [
            "evaluations/p4-physics-validation.json",
            "evaluations/p4-mcp-validation.json",
            "evaluations/p4-mcp-trace.json",
            "site/screenshots/p4/",
        ],
    }
    (ROOT / "evaluations/p4-validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in report.items() if k != "checks"}))
    if failed:
        print([c for c in checks if not c["passed"]])
        raise SystemExit(1)


if __name__ == "__main__":
    main()
