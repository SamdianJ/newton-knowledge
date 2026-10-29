"""Independently verify PD publication, provenance, raw arrays and real browser UI."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

import numpy as np
from playwright.sync_api import sync_playwright

from knowledge_store import snapshot
from maintenance import archive_file, verify_sources

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evaluations/kamino-pd-2026-10-29"
LAB = ROOT / "experiments/kamino_pd_lab"
BASE = "http://127.0.0.1:18448"
EXPECTED_PROTOCOLS = {
    "convergence": "79614e42dc3f2f954ce04fa54b03e828265f03ddc45e35ed0741ea70aa3da50a",
    "tracking": "42406443ed54c3562b9f4af4bca1ec9cf3e1dc22f6027ca097507296032286db",
    "limit_switch": "14094dfd45befa263e2fe7ac4e06d9437281ba0de1aeb6a97aa83d2d815bcb2e",
}


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    OUT.mkdir(exist_ok=True)
    archive_file(OUT / "validation.json", ROOT)
    checks, errors = [], []

    def check(value, name):
        checks.append({"check": name, "passed": bool(value)})
        if not value:
            print("FAILED: " + name, flush=True)

    store = snapshot()
    base = load(OUT / "baseline.json")
    check(len(base["historical_experiments"]) == 856, "856 previous experiment files frozen")
    check(all((ROOT / p).is_file() and sha(ROOT / p) == h for p, h in base["historical_experiments"].items()), "all previous experiment files unchanged")
    check(sha(ROOT / "manifests/source-lock.json") == base["source_lock_sha256"], "source lock unchanged")
    check(not verify_sources(ROOT / "sources/newton-v1.7.0", load(ROOT / "manifests/source-lock.json")), "all pinned Newton sources unchanged")
    old_pointer_path = OUT / "before/knowledge/current.json"
    check(sha(old_pointer_path) == base["files"]["knowledge/current.json"], "baseline pointer anchor")
    old_pointer = load(old_pointer_path)
    old_dir = ROOT / old_pointer["path"]
    check(sha(old_dir / "manifest.json") == old_pointer["manifest_sha256"], "baseline manifest anchor")
    check(all(sha(old_dir / p) == h for p, h in load(old_dir / "manifest.json")["files"].items()), "old immutable snapshot unchanged")
    for group, expected in EXPECTED_PROTOCOLS.items():
        check(sha(LAB / group / "protocol.json") == expected, "frozen protocol " + group)
        check(load(ROOT / "planning/kamino-pd-2026-10-29" / (group + "-freeze.json"))["sha256"] == expected, "freeze receipt " + group)
    catalog, report = load(LAB / "catalog.json"), load(LAB / "report-data.json")
    check(catalog["status"] == "passed" and all(c["passed"] for c in report["checks"]), "all aggregation evidence checks pass")
    check(sha(LAB / "report-data.json") == catalog["report_sha256"], "saved report fingerprint")
    check(sha(LAB / "analyze_experiments.py") == catalog["analyzer_sha256"], "aggregator fingerprint")
    check(all(sha(ROOT / p) == h for p, h in catalog["evidence_files"].items()), "all archived evidence fingerprints")
    cases = catalog["cases"]
    check(len(cases) == 7 and catalog["formal_runs"] == 22, "seven pairs and 22 unique formal runs")
    manifest = load(store.path / "manifest.json")
    for p in ("scripts/kamino_pd_content.py", "experiments/kamino_pd_lab/analyze_experiments.py", "experiments/kamino_pd_lab/viewer.js"):
        check(manifest["programs"].get(p) == sha(ROOT / p), "generator/renderer build fingerprint " + p)
    seen = set()
    for case in cases:
        cid = case["id"]
        record = store.records[case["record_id"]]
        check(record["owner_solver"] == "kamino" and record["payload"]["physical_acceptance"] == case["physical_acceptance"], "scoped published result " + cid)
        check(record["coverage"]["experiment_validated"] == (case["physical_acceptance"] == "passed"), "physical status controls evidence flag " + cid)
        if case.get("strict_convergence_acceptance"):
            check(record["payload"]["strict_convergence_acceptance"] == "failed_criteria", "strict failure preserved " + cid)
        check(case["association_relation"] == "measures_behavior_of" and bool(case["association_scope"]), "qualified field association " + cid)
        for variant in case["variants"]:
            check(variant["run_id"] != variant["reproduction"]["run_id"], "two independent runs " + cid + variant["variant"])
            samples = []
            for saved in (variant, variant["reproduction"]):
                seen.add(saved["run_id"])
                check(sha(ROOT / saved["raw_file"]) == saved["raw_sha256"], "raw fingerprint " + saved["run_id"])
                run = load(ROOT / saved["result_file"])
                check(run["protocol_sha256"] in EXPECTED_PROTOCOLS.values() and run["status"] == "completed", "formal frozen run " + saved["run_id"])
                with np.load(ROOT / saved["raw_file"], allow_pickle=False) as raw:
                    sample = {k: raw[k].copy() for k in ("body_q", "body_qd", "joint_q", "joint_qd")}
                    check(all(np.isfinite(a).all() for a in sample.values()), "finite physical arrays " + saved["run_id"])
                    samples.append(sample)
            check(all(np.allclose(samples[0][k], samples[1][k], atol=1e-4 if k.endswith("qd") else 1e-5, rtol=1e-5) for k in samples[0]), "independent physical repeat " + cid + variant["variant"])
        for ref in record["source_refs"]:
            check(sha(ROOT / "sources/newton-v1.7.0" / ref["path"]) == ref["sha256"], "exact source " + cid + ref["path"])
    check(len(seen) == 22, "baseline reused without inflating run count")
    path = "solvers/kamino/pd-experiments.md"
    text = store.documents[path]["text"]
    check(text == (ROOT / path).read_text(encoding="utf-8"), "generated PD document matches published body")
    check(all(word in text for word in ("1e-7", "互补", "未投影", "POSITION_VELOCITY", "notify_model_changed", "仍未覆盖")), "key mechanisms and limits are present")
    check(load(OUT / "mcp-validation.json")["build_id"] == store.build_id and load(OUT / "mcp-validation.json")["status"] == "passed", "MCP accepted on current build")
    with urlopen(BASE + "/api/health", timeout=10) as response:
        check(json.load(response)["build_id"] == store.build_id, "HTTP serves current build")
    shots = OUT / "screenshots"
    shots.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1080})
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(BASE + "/#/solvers/kamino/experiments", wait_until="domcontentloaded")
        page.wait_for_selector("#experiment-select")
        check(page.locator("#experiment-select option").count() == 18, "17 Kamino cases offered (2 original + 8 mechanism + 7 PD)")
        check(page.locator("iframe").count() == 3, "all three saved laboratory cohorts visible")
        for case in cases:
            cid = case["id"]
            page.goto(BASE + "/#/solvers/kamino/experiments?case=" + cid, wait_until="domcontentloaded")
            page.wait_for_selector('iframe[src*="kamino_pd_lab/"]')
            frame = page.frame_locator('iframe[src*="kamino_pd_lab/"]')
            row = frame.locator('[data-case="' + cid + '"]')
            row.locator("canvas").first.wait_for()
            check(frame.locator(".experiment").count() == 1 and row.locator("canvas").count() == 2, "isolated paired replay " + cid)
            row.locator(".plot").wait_for()
            check(row.locator(".plot").evaluate("e=>e.complete ? e.naturalWidth>0 : new Promise(resolve=>{e.addEventListener('load',()=>resolve(e.naturalWidth>0),{once:true});e.addEventListener('error',()=>resolve(false),{once:true});})"), "saved figure loaded " + cid)
            diagnostics = row.locator(".diagnostic").all_text_contents()
            check(len(diagnostics) == 2 and not any("见原始指标" in t for t in diagnostics), "both termination diagnostics visibly quantified " + cid)
            if case.get("strict_convergence_acceptance"):
                check(all("原 1e-7 标准 0%" in t for t in diagnostics), "strict zero visible separately from physical pass " + cid)
            if cid == "kamino_pd_complementarity_gate":
                check("配置收敛 100%" in diagnostics[1], "relaxed configured pass visible beside strict failure")
            before = row.locator("output").inner_text()
            slider = row.locator('input[type="range"]')
            slider.fill(str(int(slider.get_attribute("max")) // 2)); slider.dispatch_event("input")
            check(row.locator("output").inner_text() != before, "saved sample scrub " + cid)
            row.locator(".scope").scroll_into_view_if_needed()
            check(row.locator(".scope").is_visible(), "scoped interpretation visible " + cid)
            page.goto(BASE + case["viewer_url"], wait_until="domcontentloaded")
            page.wait_for_selector(".experiment canvas")
            page.locator(".plot").evaluate("e=>e.complete ? true : new Promise(resolve=>{e.addEventListener('load',()=>resolve(true),{once:true});e.addEventListener('error',()=>resolve(false),{once:true});})")
            page.screenshot(path=str(shots / (cid + ".png")), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        page.goto(BASE + cases[0]["viewer_url"], wait_until="domcontentloaded")
        page.wait_for_selector(".experiment canvas")
        check(page.evaluate("document.documentElement.scrollWidth<=innerWidth+1"), "mobile no horizontal overflow")
        page.screenshot(path=str(shots / "mobile.png"), full_page=True)
        browser.close()
    check(not errors, "no browser JavaScript errors")
    check(load(ROOT / "knowledge/current.json")["build_id"] == store.build_id, "same publication throughout validation")
    failed = sum(not c["passed"] for c in checks)
    result = {"status": "passed" if failed == 0 else "failed", "build_id": store.build_id, "passed": len(checks) - failed, "failed": failed, "checks": checks, "scope": "Evidence publication and UI; physical pass does not imply strict convergence. No simulation run by this validator."}
    (OUT / "validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "checks"}, ensure_ascii=False))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
