"""Verify MuJoCo joint/contact publication, provenance, arrays and browser UI."""
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
OUT = ROOT / "evaluations/mujoco-joint-contact-2026-10-29"
LAB = ROOT / "experiments/mujoco_joint_contact_lab"
BASE = "http://127.0.0.1:18448"
EXPECTED_PROTOCOLS = {
    "joints": "36ffb87df53457e8cefd36324a8d95fdf4bd49d915d495a28639b6372f90b77c",
    "friction": "50c8d2ac17f5ffd8c698e684712342f3f6712975e2903430f26930d510847f9b",
    "contact": "8acf6051cc232801a4414bbb7aea41b429f50c36ee621f408be368cf517ff7dc",
    "friction_stable": "0205504e415b5942cfc98a286841597ddd10b9d42c62fc06c0eb347b97865cfb",
    "friction_low_regime": "7136df96193e18891909fbface417912db6bc724121f092cf328be9958dc272a",
}
ORIGINAL_FRICTION_CASES = {"mujoco_sliding_friction_mu", "mujoco_torsional_friction_condim"}
NEGATIVE_CASES = ORIGINAL_FRICTION_CASES | {cid + "_stable" for cid in ORIGINAL_FRICTION_CASES}


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
    check(len(base["historical_experiments"]) == 1147, "1147 previous experiment files frozen")
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
        check(load(ROOT / "planning/mujoco-joint-contact-2026-10-29" / (group + "-freeze.json"))["sha256"] == expected, "freeze receipt " + group)
    catalog, report = load(LAB / "catalog.json"), load(LAB / "report-data.json")
    check(catalog["status"] == "passed" and all(c["passed"] for c in report["checks"]), "all aggregation evidence checks pass")
    check(sha(LAB / "report-data.json") == catalog["report_sha256"], "saved report fingerprint")
    check(sha(LAB / "analyze_experiments.py") == catalog["analyzer_sha256"], "aggregator fingerprint")
    check(all(sha(ROOT / p) == h for p, h in catalog["evidence_files"].items()), "all archived evidence fingerprints")
    cases = catalog["cases"]
    check(len(EXPECTED_PROTOCOLS) == 5, "all five protocol fingerprints pinned before validation")
    check(len(cases) == 12 and catalog["formal_runs"] == 48, "twelve pairs and 48 unique formal runs")
    outcomes = {case["id"]: case["physical_acceptance"] for case in cases}
    check(all(outcomes.get(cid) == "failed_criteria" for cid in NEGATIVE_CASES), "all four original and high-impratio friction negative results retained as formal cases")
    check(sum(status == "passed" for status in outcomes.values()) <= 8, "evidence completeness does not imply all physical criteria passed")
    manifest = load(store.path / "manifest.json")
    for p in ("scripts/mujoco_experiment_content.py", "experiments/mujoco_joint_contact_lab/analyze_experiments.py", "experiments/mujoco_joint_contact_lab/viewer.js"):
        check(manifest["programs"].get(p) == sha(ROOT / p), "generator/renderer build fingerprint " + p)
    seen = set()
    for case in cases:
        cid = case["id"]
        record = store.records[case["record_id"]]
        check(record["owner_solver"] == "mujoco" and record["payload"]["physical_acceptance"] == case["physical_acceptance"], "scoped published result " + cid)
        check(record["coverage"]["experiment_validated"] == (case["physical_acceptance"] == "passed"), "physical status controls evidence flag " + cid)
        check(case["association_relation"] == "measures_behavior_of" and bool(case["association_scope"]), "qualified field association " + cid)
        for variant in case["variants"]:
            check(variant["run_id"] != variant["reproduction"]["run_id"], "two independent runs " + cid + variant["variant"])
            published_variant = next(v for v in record["payload"]["variants"] if v["variant"] == variant["variant"])
            check(published_variant["config"] == variant["config"], "native configuration and sampling phase preserved " + cid + variant["variant"])
            check((ROOT / variant["config"]["full_config_file"]).is_file(), "full native configuration accessible " + cid + variant["variant"])
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
    check(len(seen) == 48, "48 unique formal runs without duplicate inflation")
    path = "solvers/mujoco/experiments.md"
    text = store.documents[path]["text"]
    check(text == (ROOT / path).read_text(encoding="utf-8"), "generated joint/contact document matches published body")
    check(all(word in text for word in ("阻尼", "armature", "摩擦", "限位")), "key mechanisms and limits are present")
    check(load(OUT / "mcp-validation.json")["build_id"] == store.build_id and load(OUT / "mcp-validation.json")["status"] == "passed", "MCP accepted on current build")
    with urlopen(BASE + "/api/health", timeout=10) as response:
        check(json.load(response)["build_id"] == store.build_id, "HTTP serves current build")
    shots = OUT / "screenshots"
    shots.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1080})
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(BASE + "/#/solvers/mujoco/inputs", wait_until="domcontentloaded")
        page.wait_for_selector("#parameter-rows")
        check(page.locator("#parameter-rows tr").count() == 20, "20 MuJoCo model inputs include five newly exposed fields")
        for field in ("joint_damping", "shape_material_mu_torsional", "shape_material_mu_rolling", "shape_margin", "shape_gap"):
            page.locator("#parameter-filter").fill(field)
            check(page.locator("#parameter-rows tr").count() >= 1, "new model input discoverable " + field)
        page.locator("#parameter-filter").fill("")
        page.goto(BASE + "/#/solvers/mujoco/experiments", wait_until="domcontentloaded")
        page.wait_for_selector("#experiment-select")
        check(page.locator("#experiment-select option").count() == 15, "14 MuJoCo cases offered (2 original + 12 joint/contact)")
        check(page.locator("iframe").count() == 2, "both saved laboratory cohorts visible")
        for case in cases:
            cid = case["id"]
            page.goto(BASE + "/#/solvers/mujoco/experiments?case=" + cid, wait_until="domcontentloaded")
            page.wait_for_selector('iframe[src*="mujoco_joint_contact_lab/"]')
            frame = page.frame_locator('iframe[src*="mujoco_joint_contact_lab/"]')
            row = frame.locator('[data-case="' + cid + '"]')
            row.locator("canvas").first.wait_for()
            check(frame.locator(".experiment").count() == 1 and row.locator("canvas").count() == 2, "isolated paired replay " + cid)
            check(row.locator(".verdict.failed").count() == int(case["physical_acceptance"] != "passed"), "physical outcome visibly distinguished " + cid)
            row.locator(".plot").wait_for()
            check(row.locator(".plot").evaluate("e=>e.complete ? e.naturalWidth>0 : new Promise(resolve=>{e.addEventListener('load',()=>resolve(e.naturalWidth>0),{once:true});e.addEventListener('error',()=>resolve(false),{once:true});})"), "saved figure loaded " + cid)
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
    result = {"status": "passed" if failed == 0 else "failed", "build_id": store.build_id, "passed": len(checks) - failed, "failed": failed, "checks": checks, "scope": "Evidence publication and UI; parameter effects retain their frozen acceptance and explicit scope. No simulation run by this validator."}
    (OUT / "validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "checks"}, ensure_ascii=False))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
