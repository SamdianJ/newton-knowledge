"""Independently verify saved-data solid replays, geometry transforms and UI.

This validator does not import the geometry generators or run physics. It uses
archived report poses, independent quaternion math, rendered mesh bounds and
canvas pixels, then exercises the user controls in an isolated browser.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import traceback
from pathlib import Path
from urllib.request import urlopen

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

from knowledge_store import snapshot
from maintenance import archive_file, verify_sources

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evaluations/solid-replays-2026-10-29"
LABS = ("solver_parameter_lab", "kamino_mechanism_lab", "kamino_pd_lab", "mujoco_joint_contact_lab")
BASE = "http://127.0.0.1:18448"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rotation(q):
    """Independent XYZW -> rotation matrix, allowing float32 quaternion roundoff."""
    q = np.asarray(q, dtype=float)
    q = q / np.linalg.norm(q)
    x, y, z, w = q
    return np.array([[1 - 2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                     [2*(x*y+z*w), 1 - 2*(x*x+z*z), 2*(y*z-x*w)],
                     [2*(x*z-y*w), 2*(y*z+x*w), 1 - 2*(x*x+y*y)]])


def expected_bounds(scene, poses):
    """Analytic solid bounds, independent of renderer triangulation."""
    lows, highs, curved = [], [], 0.0
    for shape in scene["shapes"]:
        idx = int(shape["body"])
        body = np.asarray(poses[idx], float) if idx >= 0 else np.array([0, 0, 0, 0, 0, 0, 1.])
        rb = rotation(body[3:]); rs = rotation(shape.get("quaternion", [0, 0, 0, 1]))
        center = body[:3] + rb @ np.asarray(shape.get("position", [0, 0, 0]), float)
        orient = rb @ rs
        kind = shape["type"]
        if kind == "box":
            half = np.asarray(shape["half_extents"], float)
            radius = np.abs(orient) @ half
        elif kind == "sphere":
            radius = np.ones(3) * shape["radius"]
            curved = max(curved, shape["radius"])
        elif kind == "cylinder":
            axis = {"x": 0, "y": 1, "z": 2}.get(shape.get("axis", "z"), 2)
            direction = orient[:, axis]
            radius = np.abs(direction)*shape["half_height"] + shape["radius"]*np.sqrt(np.maximum(0, 1-direction*direction))
            curved = max(curved, shape["radius"])
        else:
            raise ValueError("Unsupported independent shape oracle: " + kind)
        lows.append(center-radius); highs.append(center+radius)
    return np.min(lows, axis=0), np.max(highs, axis=0), curved


def observed_bounds(value):
    if isinstance(value, dict):
        return np.asarray(value.get("lo", value.get("min"))), np.asarray(value.get("hi", value.get("max")))
    return np.asarray(value[0]), np.asarray(value[1])


def colored_pixels(png):
    rgb = np.asarray(Image.open(io.BytesIO(png)).convert("RGB"), dtype=float)/255
    chroma = rgb.max(axis=2)-rgb.min(axis=2)
    return int(np.count_nonzero((chroma > .18) & (rgb.min(axis=2) < .8)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--static-only", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    output = OUT/("static-validation.json" if args.static_only else "validation.json")
    archive_file(output, ROOT)
    checks, errors, seen, screenshots = [], [], [], []
    build_id = load(ROOT/"knowledge/current.json")["build_id"]

    def check(value, name, detail=None):
        item = {"check": name, "passed": bool(value)}
        if detail is not None:
            item["detail"] = detail
        checks.append(item)
        if not value:
            print("FAILED: " + name, flush=True)

    try:
        baseline = load(OUT/"baseline.json")
        allowed = set(baseline["allowed_changes"])
        frozen = {p:h for p,h in baseline["files"].items() if p not in allowed}
        changed = [p for p,h in frozen.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h]
        check(not changed, "all archived physics, reports, plots and VBD files unchanged", changed)
        check(len(baseline["files"]) == 1863 and len(allowed) == 4, "baseline covers 1863 existing experiment files with four index exceptions")
        check(not verify_sources(ROOT/"sources/newton-v1.7.0", load(ROOT/"manifests/source-lock.json")), "pinned Newton implementation unchanged")
        geometry = load(ROOT/"experiments/solid_replay/geometry.json")
        check(all((ROOT/p).is_file() and sha(ROOT/p) == h for p,h in geometry["source_hashes"].items()), "geometry source hashes still match archived evidence")
        all_cases = []
        for lab in LABS:
            report = load(ROOT/"experiments"/lab/"report-data.json")
            for case in report["cases"]:
                key = lab+"/"+case["id"]
                all_cases.append((lab, case, geometry["cases"][key]))
                for replay in case["replay"]:
                    scene = geometry["cases"][key]["variants"][replay["variant"]]
                    check(bool(scene["shapes"]), "visible body shapes " + key+"/"+replay["variant"])
                    for sh in scene["shapes"]:
                        check(-1 <= sh["body"] < len(replay["body_q"][0]), "valid recorded body association " + key)
                        check(sh.get("evidence_role") in ("physical", "visual_only"), "explicit physical versus illustrative geometry " + key)
                        check(np.isfinite(sh.get("position", [0,0,0])).all() and abs(np.linalg.norm(sh.get("quaternion", [0,0,0,1]))-1) < 1e-5, "finite local pose and XYZW orientation " + key)
                        dim = sh.get("half_extents", [sh.get("radius", 1), sh.get("half_height", 1)])
                        check(all(float(x)>0 for x in dim), "positive primitive dimensions " + key)
                    for i in (0, len(replay["body_q"])//2, len(replay["body_q"])-1):
                        lo, hi, _ = expected_bounds(scene, replay["body_q"][i])
                        check(np.isfinite([lo,hi]).all() and np.all(hi > lo), "finite independent solid bounds " + key+"/"+str(i))
        check(len(all_cases) == 31 and len(geometry["cases"]) == 31, "all 31 MuJoCo and Kamino cases have explicit scene geometry")
        check(sum(c["solver"] == "mujoco" for _,c,_ in all_cases) == 14 and sum(c["solver"] == "kamino" for _,c,_ in all_cases) == 17, "14 MuJoCo and 17 Kamino cases")
        check(sum(c.get("physical_acceptance") == "failed_criteria" for _,c,_ in all_cases) == 6, "six physical negative cases retained")
        if args.static_only:
            return
        store = snapshot()
        with urlopen(BASE+"/api/health", timeout=10) as response:
            check(json.load(response)["build_id"] == store.build_id, "website serves current publication")
        with urlopen(BASE+"/files/experiments/solid_replay/geometry.json", timeout=10) as response:
            check(hashlib.sha256(response.read()).hexdigest() == sha(ROOT/"experiments/solid_replay/geometry.json"), "HTTP serves the generated geometry bytes")
        shots = OUT/"screenshots"; shots.mkdir(exist_ok=True)
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=1)
            page.on("pageerror", lambda e: errors.append(str(e)))
            for lab, case, geocase in all_cases:
                cid = case["id"]
                page.goto(BASE+f"/files/experiments/{lab}/index.html?case={cid}", wait_until="domcontentloaded")
                row = page.locator(f'.experiment[data-case="{cid}"]')
                row.locator('canvas[data-renderer="webgl"]').first.wait_for(timeout=30000)
                canvas = row.locator("canvas")
                check(page.locator(".experiment").count() == 1 and canvas.count() == 2, "isolated paired solid scene " + cid)
                check(row.locator(".verdict.failed").count() == int(case.get("physical_acceptance") == "failed_criteria"), "preserved physical result badge " + cid)
                if lab == "kamino_pd_lab":
                    diagnostic_texts = row.locator(".diagnostic").all_text_contents()
                    check(len(diagnostic_texts) == 2 and not any("见原始指标" in t for t in diagnostic_texts), "both PD termination diagnostics remain quantified " + cid)
                    if case.get("strict_convergence_acceptance"):
                        check(all("原 1e-7 标准 0%" in t for t in diagnostic_texts), "strict zero is visible separately from physical pass " + cid)
                    if cid == "kamino_pd_complementarity_gate":
                        check("配置收敛 100%" in diagnostic_texts[1], "relaxed configured pass visible beside strict failure")
                for variant in case["variants"]:
                    metrics = variant.get("metrics", {})
                    configured = next((v for v in (metrics.get("configured_converged_fraction"), metrics.get("status_converged_fraction"), variant.get("solver_diagnostics", {}).get("converged_fraction"), metrics.get("converged_mean")) if v is not None), None)
                    if configured is not None:
                        text = next((t for t in row.locator(".diagnostic").all_text_contents() if t.startswith(variant["variant"]+" ")), "")
                        values = re.findall(r"配置收敛 ([0-9.eE+\-]+)%", text)
                        expected = 100*configured
                        check(bool(values) and abs(float(values[0])-expected) <= max(1e-5, abs(expected)*5e-5), "published configured convergence agrees with saved metric " + cid+"/"+variant["variant"])
                check(row.locator(".plot").evaluate("e => e.complete ? e.naturalWidth > 0 : new Promise(resolve=>{e.onload=()=>resolve(e.naturalWidth>0);e.onerror=()=>resolve(false)})"), "original measured plot visible " + cid)
                slider = row.locator('input[type="range"]').first
                indices = [0, int(slider.get_attribute("max"))//2, int(slider.get_attribute("max"))]
                for frame in indices:
                    slider.fill(str(frame)); slider.dispatch_event("input")
                    for j, replay in enumerate(case["replay"]):
                        metadata = canvas.nth(j).evaluate("e=>({...e.dataset})")
                        i = min(frame, len(replay["body_q"])-1)
                        scene = geocase["variants"][replay["variant"]]
                        check(metadata.get("renderer") == "webgl" and int(metadata["triangleCount"]) >= 12 and int(metadata["shapeCount"]) == len(scene["shapes"]), "filled meshes rendered " + cid+f"/{j}/{frame}")
                        check(int(metadata["frameIndex"]) == i and np.allclose(json.loads(metadata["poses"]), replay["body_q"][i], rtol=0, atol=1e-12), "render uses exact archived pose sample " + cid+f"/{j}/{frame}")
                        expected_lo, expected_hi, curve_radius = expected_bounds(scene, replay["body_q"][i])
                        actual_lo, actual_hi = observed_bounds(json.loads(metadata["worldBounds"]))
                        # Sphere/cylinder vertices approximate their analytic curved hull;
                        # boxes must match exactly. The tolerance is 8% of a curved radius,
                        # never 8% of the scene or trajectory extent.
                        tolerance = 1e-6 + .08*curve_radius
                        check(np.allclose(actual_lo, expected_lo, atol=tolerance, rtol=1e-6) and np.allclose(actual_hi, expected_hi, atol=tolerance, rtol=1e-6), "independent dimensions/local transform/rotation agree " + cid+f"/{j}/{frame}", {"tolerance": tolerance})
                slider.fill(str(indices[1])); slider.dispatch_event("input")
                # User-visible controls must change the actual rendered picture and be
                # synchronized between A/B, not merely change their button labels.
                preset = row.locator("select.camera-preset")
                pictures = []
                for view in ("3d", "xz", "yz", "xy"):
                    preset.select_option(view)
                    cameras = canvas.evaluate_all("els=>els.map(e=>JSON.parse(e.dataset.camera))")
                    check(cameras[0] == cameras[1], "A/B camera synchronized " + cid+"/"+view)
                    pictures.append(hashlib.sha256(canvas.first.screenshot()).hexdigest())
                check(len(set(pictures)) >= 3, "front side top and 3D show different solid projections " + cid)
                preset.select_option("3d")
                before = canvas.first.get_attribute("data-camera")
                row.locator(".zoom-in").click()
                after = canvas.first.get_attribute("data-camera")
                check(before != after, "zoom changes shared camera " + cid)
                row.locator(".camera-reset").click()
                check(canvas.first.get_attribute("data-camera") == before, "camera reset restores default " + cid)
                check(colored_pixels(canvas.first.screenshot()) > 100, "solid surfaces visibly occupy canvas " + cid)
                virtual = any(sh["evidence_role"] == "visual_only" for scene in geocase["variants"].values() for sh in scene["shapes"])
                if virtual:
                    check("示意" in row.inner_text(), "unmodeled rotor outlines explicitly illustrative " + cid)
                path = shots/(cid+".png"); row.screenshot(path=str(path)); screenshots.append(str(path.relative_to(ROOT)))
                seen.append(cid)
            # Drag interaction and zoom-out on representative articulated and primitive
            # scenes; this is a shared renderer, so do not duplicate 31 identical drags.
            for lab, cid in [("kamino_mechanism_lab", "kamino_fourbar_fk"), ("mujoco_joint_contact_lab", "mujoco_joint_passive_damping")]:
                page.goto(BASE+f"/files/experiments/{lab}/index.html?case={cid}", wait_until="domcontentloaded")
                row=page.locator(".experiment"); canvas=row.locator('canvas[data-renderer="webgl"]');canvas.first.wait_for()
                before=canvas.first.get_attribute("data-camera"); box=canvas.first.bounding_box()
                page.mouse.move(box["x"]+box["width"]*.5, box["y"]+box["height"]*.5);page.mouse.down();page.mouse.move(box["x"]+box["width"]*.6, box["y"]+box["height"]*.6, steps=5);page.mouse.up()
                check(canvas.first.get_attribute("data-camera") != before and canvas.first.get_attribute("data-camera") == canvas.nth(1).get_attribute("data-camera"), "drag rotates synchronized scene " + cid)
                before=canvas.first.get_attribute("data-camera");row.locator(".zoom-out").click();check(canvas.first.get_attribute("data-camera") != before, "zoom out works " + cid)
                row.locator(".fit").click();check(canvas.first.get_attribute("data-renderer") == "webgl", "fit retains rendered scene " + cid)
                row.locator(".expand").click();check(page.locator("dialog[open]").count() == 1, "expanded comparison opens " + cid);page.keyboard.press("Escape")
                timeline=row.locator('input[type="range"]').first
                timeline.fill("0");timeline.dispatch_event("input")
                row.locator(".play").click()
                page.wait_for_function("document.querySelector('.experiment canvas').dataset.frameIndex !== '0'",timeout=4000)
                row.locator(".play").click()
                check(int(canvas.first.get_attribute("data-frame-index")) > 0 and row.locator(".play").inner_text() == "播放", "play advances recorded frames and pauses " + cid)
            for solver, count, frames in [("mujoco", 14, 2), ("kamino", 17, 3)]:
                page.goto(BASE+f"/#/solvers/{solver}/experiments",wait_until="domcontentloaded")
                page.wait_for_selector("#experiment-select")
                check(page.locator("#experiment-select option").count() == count+1 and page.locator("iframe").count() == frames, "all laboratory cohorts accessible " + solver)
            page.set_viewport_size({"width":390,"height":844})
            for lab,cid in [("mujoco_joint_contact_lab","mujoco_joint_passive_damping"),("kamino_mechanism_lab","kamino_fourbar_fk")]:
                page.goto(BASE+f"/files/experiments/{lab}/index.html?case={cid}",wait_until="domcontentloaded");page.locator('canvas[data-renderer="webgl"]').first.wait_for()
                check(page.evaluate("document.documentElement.scrollWidth<=innerWidth+1"), "mobile scene has no horizontal overflow " + cid)
                page.screenshot(path=str(shots/(cid+"-mobile.png")),full_page=True)
            browser.close()
        check(not errors, "no browser JavaScript errors", errors)
        check(len(seen) == 31, "all 31 actual solid replays exercised")
        check(load(ROOT/"knowledge/current.json")["build_id"] == store.build_id, "same publication throughout validation")
    except Exception:
        errors.append(traceback.format_exc())
        check(False, "validation completed without unexpected exception", errors[-1])
    finally:
        failed=sum(not x["passed"] for x in checks)
        result={"status":"passed" if failed==0 else "failed","build_id":build_id,"passed":len(checks)-failed,"failed":failed,"checks":checks,"browser_errors":errors,"cases_exercised":seen,"screenshots":screenshots,"scope":"Read-only geometry, archived pose, visual controls and frozen evidence validation; no physics is executed."}
        output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({k:v for k,v in result.items() if k not in ("checks","browser_errors","cases_exercised","screenshots")},ensure_ascii=False))
        if failed:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
