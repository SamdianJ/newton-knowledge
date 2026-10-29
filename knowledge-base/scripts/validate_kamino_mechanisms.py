"""Independently accept Kamino evidence publication and the real browser surface."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

from playwright.sync_api import sync_playwright

from knowledge_store import snapshot
from maintenance import archive_file, verify_sources

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evaluations/kamino-mechanisms-2026-10-29"
LAB = ROOT / "experiments/kamino_mechanism_lab"
BASE = "http://127.0.0.1:18448"
EXPECTED_PROTOCOLS = {
    "experiments/kamino_mechanism_lab/loop_fk/protocol.json": "9f84bd8d778405f698db1bb1a08dba90666ecce6e6458f4a35ecaa2fec28b13a",
    "experiments/kamino_mechanism_lab/backends/protocol.json": "b6cac2aa44540efe13d6961f559714dcbb3c74807c073b78049896bfdd81dbaa",
    "experiments/kamino_mechanism_lab/drive_reset/protocol.json": "9b4c235d475b1cb915714acebd078a4d0d5155736e8a300b0da52d02fa6dff74",
    "experiments/kamino_mechanism_lab/loop_fk/protocol-refinement.json": "9cdc6a4e7d276036d6b6edbf4e70cee12705d39805824ba63336438471056e04",
}


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    archive_file(OUT / "validation.json", ROOT)
    checks, errors = [], []

    def check(value, name, detail=None):
        item = {"check": name, "passed": bool(value)}
        if detail is not None:
            item["detail"] = detail
        checks.append(item)
        if not value:
            print("FAILED: " + name, flush=True)

    store = snapshot()
    baseline = load(OUT / "baseline.json")
    historical = baseline["historical_experiments"]
    check(len(historical) == 323, "all 323 historical experiment files are enumerated")
    changed_old = [p for p, h in historical.items() if not (ROOT / p).is_file() or sha(ROOT / p) != h]
    check(not changed_old, "historical experiment bytes unchanged", changed_old)
    check(sha(ROOT / "manifests/source-lock.json") == baseline["source_lock"], "source lock unchanged")
    lock = load(ROOT / "manifests/source-lock.json")
    source_failures = verify_sources(ROOT / "sources/newton-v1.7.0", lock)
    check(not source_failures, "all pinned Newton source files unchanged", source_failures)
    old_dir = ROOT / "knowledge/builds" / baseline["build"]
    old_pointer_path = OUT / "before/knowledge__current.json"
    check(sha(old_pointer_path) == baseline["files"]["knowledge/current.json"], "archived baseline pointer unchanged")
    old_pointer = load(old_pointer_path)
    check(sha(old_dir / "manifest.json") == old_pointer["manifest_sha256"], "baseline immutable manifest unchanged")
    old_manifest = load(old_dir / "manifest.json")
    check(all(sha(old_dir / name) == h for name, h in old_manifest["files"].items()), "baseline immutable snapshot files unchanged")
    freeze = load(ROOT / "planning/kamino-mechanisms/freeze.json")
    refinement = load(ROOT / "planning/kamino-mechanisms/refinement-freeze.json")
    declared = {p["path"]: p["sha256"] for p in freeze["protocols"]}
    declared[refinement["protocol_file"]] = refinement["sha256"]
    check(declared == EXPECTED_PROTOCOLS, "original and refinement preregistration hashes preserved")
    for path, expected in EXPECTED_PROTOCOLS.items():
        check(sha(ROOT / path) == expected, "frozen protocol unchanged " + path)
    measured = load(LAB / "catalog.json")
    cases = measured["cases"]
    check(measured["status"] == "passed", "catalog evidence validation passed (not all physics)")
    check(measured["report_sha256"] == sha(LAB / "report-data.json"), "replay report fingerprint")
    check(measured["analyzer_sha256"] == sha(LAB / "analyze_experiments.py"), "aggregator fingerprint")
    bad_evidence = [p for p, h in measured["evidence_files"].items() if not (ROOT / p).is_file() or sha(ROOT / p) != h]
    check(bool(measured["evidence_files"]) and not bad_evidence, "all catalog evidence files match", bad_evidence)
    check(len(cases) == 8 and len({c["id"] for c in cases}) == 8, "eight unique new mechanism cases")
    check(sum(c["physical_acceptance"] == "passed" for c in cases) == 6, "six cases meet physical gates")
    check(sum(c["physical_acceptance"] == "failed_criteria" for c in cases) == 2, "two failed loop cases remain explicit")
    manifest = load(store.path / "manifest.json")
    for program in ("scripts/kamino_experiment_content.py", "experiments/kamino_mechanism_lab/viewer.js", "experiments/kamino_mechanism_lab/viewer.css"):
        check(manifest["programs"].get(program) == sha(ROOT / program), "generator/renderer in build fingerprint " + program)
    programs = load(ROOT / "manifests/experiment-programs.json")["files"]
    graph = load(store.path / "graph.json")
    run_ids = set()
    for case in cases:
        cid = case["id"]
        record = store.records[case["record_id"]]
        check(record["owner_solver"] == "kamino" and record["record_type"] == "lab_experiment", "published scoped experiment " + cid)
        check(record["payload"]["physical_acceptance"] == case["physical_acceptance"], "published physical outcome " + cid)
        check(record["coverage"]["experiment_validated"] == (case["physical_acceptance"] == "passed"), "failed case cannot be promoted " + cid)
        check(case["association_relation"] == "measures_behavior_of" and bool(case.get("association_scope")), "association distinguishes mechanism evidence from direct parameter A/B " + cid)
        related = [e for e in graph["edges"] if e["source"] == case["record_id"] and e["target"] in case["associations"]]
        check({e["target"] for e in related} == set(case["associations"]) and all(e["relation"] == "measures_behavior_of" for e in related), "parameter association graph roles " + cid)
        check(len(case["variants"]) == 2, "two variants " + cid)
        for variant in case["variants"]:
            reproduction = variant["reproduction"]
            check(variant["run_id"] != reproduction["run_id"], "independent repeated run " + cid + variant["variant"])
            for run in (variant, reproduction):
                run_ids.add(run["run_id"])
                check(sha(ROOT / run["raw_file"]) == run["raw_sha256"], "raw trajectory hash " + run["run_id"])
                check(run["protocol_sha256"] in EXPECTED_PROTOCOLS.values(), "run uses preregistered protocol " + run["run_id"])
                result = load(ROOT / run["result_file"])
                check(result["status"] == "completed", "execution completed independently of physical acceptance " + run["run_id"])
        call = case["program_source_call"]
        check(call["tool"] == "get_source" and call["arguments"]["scope"] == "experiment", "archived runner source call " + cid)
        source_path = call["arguments"]["path"]
        check(programs.get(source_path) == case["variants"][0]["program_sha256"] and sha(ROOT / "experiments" / source_path) == programs.get(source_path), "source call resolves exact runner " + cid)
        for ref in record["source_refs"]:
            file = ROOT / "sources/newton-v1.7.0" / ref["path"]
            line_count = len(file.read_text(encoding="utf-8").splitlines())
            check(ref["sha256"] == lock["files"][ref["path"]] and 1 <= ref["line"] <= ref.get("end_line", ref["line"]) <= line_count, "valid fixed source reference " + cid + " " + ref["path"])
    check(len(run_ids) == 32, "32 distinct formal run IDs represented")
    for rid in ("map:kamino:padmm_projection_dual", "map:kamino:physical_residuals_backend_boundary"):
        record = store.records[rid]
        local = record["payload"].get("local_experiments", [])
        check(len(local) == 1 and not record["coverage"]["experiment_validated"], "mapping remains partly evidenced " + rid)
        for evidence in local:
            check(any(e["source"] == rid and e["target"] == evidence["record_id"] and e["relation"] == "partial_local_evidence" and e.get("scope") == evidence["scope"] and e.get("limitation") == evidence["limitation"] for e in graph["edges"]), "qualified mapping evidence edge " + rid)
    docs = load(store.path / "documents.json")
    path = "solvers/kamino/experiments.md"
    check(docs[path]["text"] == (ROOT / path).read_text(encoding="utf-8"), "generated experiment page matches publication")
    check(all(c["record_id"] in docs[path]["text"] or quote(c["record_id"], safe="") in docs[path]["text"] for c in cases), "all eight case links appear in experiment page")
    with urlopen(BASE + "/api/health", timeout=10) as response:
        check(json.load(response)["build_id"] == store.build_id, "HTTP serves current build")
    mcp = load(OUT / "mcp-validation.json")
    check(mcp["status"] == "passed" and mcp["build_id"] == store.build_id, "external MCP accepted on current build")
    original_ids = {c["id"] for c in load(ROOT / "experiments/solver_parameter_lab/catalog.json")["cases"] if c["solver"] == "kamino"}
    current_ids = {c["id"] for c in store.catalog["solvers"]["kamino"]["experiments"]}
    check(len(original_ids) == 2 and original_ids | {c["id"] for c in cases} <= current_ids, "Kamino retains original two plus eight mechanism cases")
    shots = OUT / "screenshots"
    shots.mkdir(exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1080})
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        screenshot_page = browser.new_page(viewport={"width": 1440, "height": 1080})
        screenshot_page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.goto(BASE + "/#/solvers/kamino/experiments", wait_until="domcontentloaded")
        page.wait_for_selector("#experiment-select")
        check(page.locator("#experiment-select option").count() == len(current_ids) + 1, "browser offers every saved Kamino case")
        old_frame = page.frame_locator('iframe[src*="solver_parameter_lab/"]')
        new_frame = page.frame_locator('iframe[src*="kamino_mechanism_lab/"]')
        old_frame.locator(".experiment").first.wait_for()
        new_frame.locator(".experiment").first.wait_for()
        check(old_frame.locator(".experiment").count() == 2 and new_frame.locator(".experiment").count() == 8, "both original and new labs render")
        page.screenshot(path=str(shots / "all-kamino-experiments.png"), full_page=True)
        for case in cases:
            cid = case["id"]
            page.locator("#experiment-select").select_option(cid)
            page.wait_for_selector('iframe[src*="kamino_mechanism_lab/"][src*="case=' + cid + '"]')
            frame = page.frame_locator('iframe[src*="kamino_mechanism_lab/"]')
            row = frame.locator('[data-case="' + cid + '"]')
            row.wait_for()
            check(frame.locator(".experiment").count() == 1 and row.locator("canvas").count() == 2, "selected case has actual A/B replay canvases " + cid)
            check(row.locator("canvas").first.evaluate("e=>e.width>0&&e.height>0&&e.getContext('2d').getImageData(0,0,e.width,e.height).data.some((x,i)=>i%4===3&&x>0)"), "canvas contains rendered data " + cid)
            loaded = row.locator("img.plot").evaluate("e=>e.complete?e.naturalWidth>0:new Promise(resolve=>{e.addEventListener('load',()=>resolve(e.naturalWidth>0),{once:true});e.addEventListener('error',()=>resolve(false),{once:true});})")
            check(loaded, "measured curve loads " + cid)
            scope = row.locator(".scope").inner_text()
            check(row.locator(".scope").is_visible() and "适用边界" in scope and len(scope) > 20, "limits visibly stated " + cid)
            row.locator(".scope").scroll_into_view_if_needed()
            check(row.locator(".scope").evaluate("e=>{const r=e.getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight+1;}"), "limits actually reachable inside iframe viewport " + cid)
            failed = case["physical_acceptance"] != "passed"
            check(row.locator(".verdict.failed").count() == int(failed), "visible outcome matches physical acceptance " + cid)
            if failed:
                check("未通过" in row.locator(".verdict").inner_text(), "negative result labeled as failed " + cid)
            initial = row.locator("output").inner_text()
            slider = row.locator('input[type="range"]')
            slider.fill(str(int(slider.get_attribute("max")) // 2))
            slider.dispatch_event("input")
            check(row.locator("output").inner_text() != initial, "replay scrub uses saved samples " + cid)
            screenshot_page.goto(BASE + case["viewer_url"], wait_until="domcontentloaded")
            screenshot_page.wait_for_selector(".experiment canvas")
            screenshot_page.locator("img.plot").evaluate("e=>e.complete?e.naturalWidth>0:new Promise(resolve=>{e.addEventListener('load',()=>resolve(true),{once:true});e.addEventListener('error',()=>resolve(false),{once:true});})")
            screenshot_page.screenshot(path=str(shots / (cid + ".png")), full_page=True)
        page.goto(BASE + "/#/record/" + quote("model:kamino:joint_effort_limit", safe=""), wait_until="domcontentloaded")
        page.wait_for_selector(".doc-article")
        parameter_links = page.locator('.detail-panel .actions a[href*="/experiments?case="]')
        hrefs = parameter_links.evaluate_all("els=>els.map(e=>e.getAttribute('href'))")
        check(bool(hrefs) and all("/solvers/kamino/experiments?case=" in href for href in hrefs), "Kamino effort-limit experiment buttons keep Kamino scope", hrefs)
        page.set_viewport_size({"width": 390, "height": 844})
        mobile_case = next(c for c in cases if c["physical_acceptance"] != "passed")
        page.goto(BASE + mobile_case["viewer_url"], wait_until="domcontentloaded")
        page.wait_for_selector(".experiment canvas")
        check(page.locator(".experiment").count() == 1, "mobile deep link isolates one case")
        check(page.evaluate("document.documentElement.scrollWidth<=innerWidth+1"), "mobile mechanism lab has no horizontal overflow")
        check(page.locator(".verdict.failed").count() == 1 and page.locator(".scope").is_visible(), "mobile failure and boundaries visible")
        page.screenshot(path=str(shots / "mobile-negative-case.png"), full_page=True)
        browser.close()
    check(not errors, "no browser JavaScript errors", errors)
    check(load(ROOT / "knowledge/current.json")["build_id"] == store.build_id, "publication did not change during acceptance")
    failed = sum(not c["passed"] for c in checks)
    report = {"status": "passed" if not failed else "failed", "build_id": store.build_id, "passed": len(checks) - failed, "failed": failed, "checks": checks, "scope": "Publication/provenance/UI acceptance; 6 physics-passing and 2 physics-failing cases are intentionally retained. No simulation executed by this validator."}
    (OUT / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "checks"}, ensure_ascii=False))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
