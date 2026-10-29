"""Read saved Kamino scene evidence for outline replays; never import/run Newton.

The replay poses remain in the original report.  This adapter describes geometry
in each recorded body's local frame, with xyzw quaternions.  Authored boxes in the
four-bar scene have collision disabled.  Shape-free rotor experiments receive an
explicitly labelled visual-only glyph, not a claimed physical/collision surface.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDENTITY = [0.0, 0.0, 0.0, 1.0]
ZERO = [0.0, 0.0, 0.0]


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _source(root, path):
    return {"path": Path(path).relative_to(root).as_posix(), "sha256": _sha(path)}


def _shape(kind, body, label, role="physical", **dimensions):
    return {
        "type": kind, "body": body, "label": label,
        "position": list(ZERO), "quaternion": list(IDENTITY),
        "evidence_role": role, **dimensions,
    }


def _hinge():
    return {
        "kind": "revolute", "parent": -1, "child": 0,
        "parent_position": list(ZERO), "child_position": list(ZERO),
        "parent_quaternion": list(IDENTITY), "child_quaternion": list(IDENTITY),
        "axis": [0.0, 1.0, 0.0], "label": "Y 轴铰链",
    }


def _rotor_glyph(com):
    """A radial pointer makes orientation visible without inventing a solid model."""
    if com == [0.5, 0.0, 0.0]:
        # The .5 m COM offset is measured/configured; all widths/radii are visual.
        return [
            _shape("box", 0, "示意径向臂", "visual_only", position=[0.25, 0.0, 0.0], half_extents=[0.25, 0.025, 0.025]),
            _shape("cylinder", 0, "示意偏心质量盘", "visual_only", position=list(com), axis="y", radius=0.12, half_height=0.025),
            _shape("box", 0, "盘面方向标记", "visual_only", position=[0.56, -0.028, 0.0], half_extents=[0.06, 0.006, 0.012]),
        ]
    if com == [0.0, 0.0, 0.0]:
        return [
            _shape("cylinder", 0, "示意转盘", "visual_only", axis="y", radius=0.18, half_height=0.025),
            _shape("box", 0, "示意径向指针", "visual_only", position=[0.12, -0.031, 0.0], half_extents=[0.12, 0.009, 0.018]),
        ]
    raise ValueError("Unreviewed shape-free rotor COM; add an explicit visual-only design")


def geometry_for_case(case, root=ROOT):
    """Return ``{variant: geometry_spec}`` for the 15 mechanism/PD cases.

    Unknown cases return an empty mapping so another family adapter can handle
    them.  A supported case with missing or changed archived evidence fails.
    ``physical`` denotes original authored geometry, not automatically a collider.
    Explicit collision_enabled and the per-scene notes retain that distinction.
    """
    root = Path(root).resolve()
    cid = case["id"]
    supported = cid.startswith("kamino_fourbar_") or cid == "kamino_backend_guided_contact" or cid in {
        "kamino_drive_effort_paths", "kamino_reset_default_replay", "kamino_reset_preserve_replay",
    } or cid.startswith("kamino_pd_")
    if not supported:
        return {}
    output = {}
    for variant in case["variants"]:
        result_path = root / variant["result_file"]
        directory = result_path.parent
        result = _load(result_path)
        runner = directory / "runner.py"
        protocol_path = directory / "protocol.json"
        assert _sha(runner) == result.get("runner_sha256", result.get("program_sha256")), str(runner)
        assert _sha(protocol_path) == result["protocol_sha256"], str(protocol_path)
        sources = [_source(root, result_path), _source(root, runner), _source(root, protocol_path)]
        config_path = directory / "resolved-config.json"
        scene_path = directory / "scene.json"
        for path in (scene_path, config_path):
            if path.exists():
                expected = result.get("files_sha256", {}).get(path.name)
                if expected:
                    assert _sha(path) == expected, str(path)
                sources.append(_source(root, path))
        spec = {
            "schema_version": "1.0", "coordinate_frame": "body-local; world for body=-1; quaternion xyzw; metres",
            "shapes": [], "joints": [], "floor": None,
            "sources": sources, "notes": [],
        }
        if cid.startswith("kamino_fourbar_"):
            scene = _load(scene_path)
            assert len(scene["dimensions_xyz_m"]) == 4
            spec["shapes"] = [
                _shape("box", body, name, half_extents=[v / 2 for v in dim], collision_enabled=False)
                for body, (name, dim) in enumerate(zip(scene["body_names"], scene["dimensions_xyz_m"]))
            ]
            arrays = scene["model_arrays"]
            for i, (parent, child, xp, xc) in enumerate(zip(arrays["joint_parent"], arrays["joint_child"], arrays["joint_X_p"], arrays["joint_X_c"])):
                spec["joints"].append({
                    "kind": "fixed" if i == 0 else "revolute", "parent": parent, "child": child,
                    "parent_position": xp[:3], "child_position": xc[:3],
                    "parent_quaternion": xp[3:], "child_quaternion": xc[3:],
                    "axis": [0.0, 1.0, 0.0], "label": scene["joint_order"][i],
                })
            spec["notes"] = [
                "四根杆使用归档场景的真实 box 尺寸、局部姿态和 joint_X_p / joint_X_c 锚点；box 在本实验中禁用碰撞。",
                "A/B 的开链或闭环关节分别读取各自归档，不用闭环连线掩盖开链或约束误差。",
                "关节标记尺寸仅作可视提示；未新增地面或任何碰撞几何。",
            ]
        elif cid == "kamino_backend_guided_contact":
            scene = _load(scene_path)
            spec["shapes"] = [_shape("sphere", 0, "导向球", radius=scene["radius_m"], collision_enabled=True)]
            spec["floor"] = 0.0
            spec["joints"] = [{
                "kind": "prismatic", "parent": -1, "child": 0,
                "parent_position": scene["initial_position_m"], "child_position": list(ZERO),
                "parent_quaternion": list(IDENTITY), "child_quaternion": list(IDENTITY),
                "axis": scene["joint_axis"], "label": "斜向移动副",
            }]
            spec["notes"] = ["球半径及地面来自归档场景；导向关节轴来自实际 builder 配置，导轨标记不是碰撞几何。"]
        else:
            cfg = _load(config_path)
            com = [float(v) for v in cfg["body_com"][0]]
            assert len(cfg["body_com"]) == 1
            spec["shapes"] = _rotor_glyph(com)
            spec["joints"] = [_hinge()]
            spec["center_of_mass"] = [{"body": 0, "position": com}]
            spec["notes"] = [
                "本实验原模型没有 shape；转盘、径向臂和指针是明确标注的 visual-only 轮廓，尺寸不代表质量、惯量或碰撞半径。",
                "示意轮廓严格随保存的 body_q 平移与旋转；Y 轴关节锚点和质心位置来自归档 builder / resolved-config。",
                "没有地面、接触或隐藏的新增仿真；曲线与验收仍来自原始实验。",
            ]
        output[variant["variant"]] = spec
    return output


if __name__ == "__main__":
    # A read-only smoke check; the parent build script chooses output locations.
    count = 0
    for lab in ("kamino_mechanism_lab", "kamino_pd_lab"):
        data = _load(ROOT / "experiments" / lab / "report-data.json")
        for item in data["cases"]:
            geometries = geometry_for_case(item)
            assert set(geometries) == {v["variant"] for v in item["variants"]}
            assert all(g["shapes"] for g in geometries.values())
            count += len(geometries)
    print(json.dumps({"status": "passed", "case_variants": count, "physics_executed": False}))
