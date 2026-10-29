"""Aggregate frozen Kamino evidence without rerunning physics or changing gates."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["svg.hashsalt"] = "kamino-mechanisms-2026-10-29"
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
COMMIT = "7e75abe28b8d69522bc0b34837aaed2c303dff5a"
GROUPS = [
    ("loop_fk/analysis.json", "loop_fk/analyze_experiments.py", "loop_fk/protocol.json", "loop"),
    ("loop_fk/refinement-analysis.json", "loop_fk/analyze_refinement.py", "loop_fk/protocol-refinement.json", "loop"),
    ("backends/analysis.json", "backends/analyze.py", "backends/protocol.json", "backend"),
    ("drive_reset/analysis.json", "drive_reset/analyze.py", "drive_reset/protocol.json", "drive"),
]


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path):
    return Path(path).relative_to(ROOT).as_posix()


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def require(condition, label, checks):
    checks.append({"check": label, "passed": bool(condition)})
    if not condition:
        raise ValueError(label)


def normalized_runs(case, kind):
    if kind == "loop":
        return case["runs"]
    if kind == "backend":
        return [{**r, "run": str(Path(r["result_file"]).parent).replace("\\", "/")} for r in case["variants"]]
    return [{**r, "variant": v["variant"]} for v in case["variants"] for r in v["runs"]]


def spec_for(protocol, case_id):
    return next((c for c in protocol.get("cases", []) if c["id"] == case_id), protocol)


def tolerance(protocol, field):
    t = protocol.get("repeats", protocol.get("common_run", {}).get("repeat_tolerance", protocol.get("acceptance", {}).get("repeat_tolerance", {})))
    return t.get(field + "_atol", t.get("velocity_atol" if field.endswith("qd") else "pose_atol", 1e-4 if field.endswith("qd") else 1e-5)), t.get("rtol", 1e-5)


def environment_summary(value):
    return {"python": value.get("python", "").split()[0], "platform": value.get("platform", ""), "device": value.get("device", "cpu"), "packages": value.get("packages", value.get("dependencies", {})), "source_commit": COMMIT}


def compact_config(config, treatment, path):
    solver = config.get("solver", config)
    selected = {k: solver[k] for k in ("dynamics_solver", "integrator", "sparse_jacobian", "sparse_dynamics", "use_fk_solver", "use_collision_detector") if k in solver}
    for section, names in {"dynamics": ("preconditioning", "linear_solver_type"), "padmm": ("max_iterations", "warmstart_mode", "use_acceleration"), "dvi": ("max_alternating_iterations", "inequality_sweeps_per_iteration"), "fk": ("reset_state", "tolerance"), "constraints": ("alpha", "gamma")}.items():
        if isinstance(solver.get(section), dict):
            selected[section] = {k: solver[section][k] for k in names if k in solver[section]}
    for name in ("drive", "dof_act_paths", "joint_effort_limit", "joint_target_ke", "joint_target_kd"):
        if name in config:
            selected[name] = config[name]
    return {"treatment": treatment, "resolved": selected, "full_config_file": rel(path), "full_config_field": "resolved_config" if path.name == "result.json" else None}


def associations(case_id, parameter_ids, model_ids):
    if case_id == "kamino_fourbar_fk":
        names = ["config.use_fk_solver", "config.fk.reset_state", "reset.body_poses"]
        scope = "直接比较 fk.reset_state 初值策略；其余仅为 FK/reset 机制关联，不构成逐参数干预验证。"
    elif "fourbar_loop" in case_id:
        names = ["config.constraints.alpha", "config.integrator"]
        scope = "直接改变闭环拓扑；跨三组改变 dt。alpha 与 integrator 在组内固定，仅为行为关联，不计其单参数覆盖。"
    elif case_id == "kamino_backend_guided_contact":
        names = ["config.dynamics_solver", "config.sparse_jacobian", "config.dynamics.preconditioning", "config.dynamics.linear_solver_type"]
        scope = "后端及三个依赖默认字段共同变化，属于配置组比较，不是四个独立单参数实验。"
    elif case_id == "kamino_drive_effort_paths":
        return [model_ids[n] for n in ("joint_target_ke", "joint_target_kd", "joint_effort_limit")], "驱动路径/目标模式/增益共同变化，力限固定为 1 N·m；不构成 ke、kd 或力限的独立扫描。"
    else:
        names = ["reset.body_poses", "reset.body_velocities", "config.padmm.warmstart_mode"]
        scope = "比较有历史与新求解器的 reset/replay；warmstart=internal 固定，不构成各暖启动模式的独立比较。"
    return [parameter_ids[n] for n in names], scope


def text_observation(case, kind, metrics):
    a, b = metrics["A"], metrics["B"]
    cid = case["id"]
    if cid == "kamino_fourbar_fk":
        return f"6 个非奇异主动角目标下，两种 FK 初值策略均通过；A/B 最大解析位置误差 {a['max_analytic_position_error_m']:.4g}/{b['max_analytic_position_error_m']:.4g} m。被动关节与闭环锚点重建符合事前门槛。该数据是有序姿态查询，不是动力学跟踪。"
    if "fourbar_loop" in cid:
        accepted = "通过" if case["status"] == "passed" else "未通过，保留失败"
        return f"开链 A/闭环 B 保留关节最大间隙 {a['max_retained_joint_gap_m']*1000:.4f}/{b['max_retained_joint_gap_m']*1000:.4f} mm；虚拟/真实闭环最大间隙 {a['max_loop_or_virtual_gap_m']*1000:.4f}/{b['max_loop_or_virtual_gap_m']*1000:.4f} mm。本步长的完整拓扑对照{accepted}。alpha 和积分器固定，仅改变拓扑；跨组 dt 细化不能覆盖原失败或证明收敛阶。"
    if kind == "backend":
        m = case["metrics"]
        return f"同一倾斜导轨单接触中，两配置组通过物理门槛；尾段位置最大差 {m['tail_position_difference_max_m']:.4g} m。PADMM/DVI 收敛标记比例 {a['converged_fraction']:.2%}/{b['converged_fraction']:.2%}，但定义和停止准则不同，不能用来排名物理准确性或性能。"
    if cid == "kamino_drive_effort_paths":
        return f"显式 effort 与有界隐式 PD 的正反饱和响应均符合 1 N·m 力限；速度解析参考最大误差 A/B 为 {a['joint_velocity_reference_max_abs_rad_s']:.4g}/{b['joint_velocity_reference_max_abs_rad_s']:.4g} rad/s。实际路由不同，均通过事前门槛；未测试非饱和跟踪或力限切换。"
    pairs = [c['max_abs'] for p in case.get('paired_checks', []) for c in p['fields'].values()]
    if cid == "kamino_reset_default_replay":
        return f"有非零历史的求解器默认 reset 后，与新求解器同初态重放通过；body/joint 各位置或速度字段的配对最大绝对差至多 {max(pairs, default=0):.4g}（按各字段单位）。力、加速度、内部时间/步数按协议清除，外部 Control 保持不变。"
    return f"preserve reset 保持输入 body 姿态/速度并清除历史量后，老求解器与只接收 body 状态的新求解器重放通过；各字段配对最大绝对差至多 {max(pairs, default=0):.4g}（按各字段单位）。只测试一致状态、单 world 和 internal 暖启动。"


def plot_case(case_id, arrays, scene, labels, sample_kind):
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.7), constrained_layout=True)
    for variant, data in arrays.items():
        t = data["time"]
        q = data["joint_q"]
        qd = data["joint_qd"]
        if "fourbar" in case_id:
            poses = data["body_q"].astype(float)
            quat = poses[...,3:]
            quat /= np.linalg.norm(quat,axis=-1,keepdims=True)
            centers, anchors = np.asarray(scene["body_centers_m"]), np.asarray(scene["hinge_positions_m"])
            def point(body, local):
                xyz, w = quat[:,body,:3], quat[:,body,3:]
                return poses[:,body,:3] + local + 2*np.cross(xyz,np.cross(xyz,local)+w*local)
            gaps = np.column_stack([np.linalg.norm(point(p,anchor-centers[p])-point(c,anchor-centers[c]),axis=1) for p,c,anchor in zip((0,1,2,3),(1,2,3,0),anchors)])
            retained = gaps if sample_kind=="targets" or variant=="B" else gaps[:,:3]
            axes[0].plot(t,q[:,0],label=labels[variant])
            fixed_base_gap = np.linalg.norm(poses[:,0,:3]-centers[0],axis=1)
            axes[1].plot(t,np.maximum(np.max(retained,axis=1),fixed_base_gap)*1000,label=labels[variant])
            axes[2].plot(t,gaps[:,-1]*1000,label=labels[variant])
            units = ("active hinge angle [rad]","max retained anchor gap [mm]","closure / virtual closure gap [mm]")
        elif case_id == "kamino_backend_guided_contact":
            position = data["body_q"][:,0,:3]
            displacement = position-np.asarray(scene["initial_position_m"])
            axis = np.asarray(scene["joint_axis"])
            off_axis = np.linalg.norm(displacement-np.outer(displacement@axis,axis),axis=1)
            axes[0].plot(t,position[:,2],label=labels[variant])
            axes[1].plot(t,np.linalg.norm(data["body_qd"][:,0,:3],axis=1),label=labels[variant])
            axes[2].plot(t,off_axis*1e6,label=labels[variant])
            units = ("sphere center z [m]","linear speed [m/s]","guide deviation [micrometers]")
        else:
            axes[0].plot(t,q[:,0],label=labels[variant])
            axes[1].plot(t,qd[:,0],label=labels[variant])
            axes[2].plot(t,data["applied_body_wrench"][:,0,4],label=labels[variant])
            units = ("hinge angle [rad]","hinge velocity [rad/s]","applied torque Y [N m]")
    for ax, unit in zip(axes,units):
        ax.set_ylabel(unit)
    for ax in axes:
        ax.set_xlabel("target query index (not seconds)" if sample_kind == "targets" else "time [s]")
        ax.legend(fontsize=8)
        ax.grid(alpha=.25)
    fig.suptitle(case_id + " | saved trajectories and independent diagnostics", fontsize=10)
    fig.savefig(HERE / (case_id + ".svg"), metadata={"Date": None})
    fig.savefig(HERE / (case_id + ".png"), dpi=130)
    plt.close(fig)


def main():
    checks, evidence, all_cases, report_cases, excluded = [], {}, [], [], []
    params = read(ROOT / "solvers/kamino/parameters.json")["records"]
    models = read(ROOT / "solvers/kamino/model-inputs.json")
    pids = {r["name"]: r["id"] for r in params}
    mids = {r["field"]: r["id"] for r in models}
    valid_ids = set(pids.values()) | set(mids.values())
    adopted_directories = set()
    for analysis_name, analyzer_name, protocol_name, kind in GROUPS:
        analysis, protocol = read(HERE / analysis_name), read(HERE / protocol_name)
        require(analysis.get("status") != "incomplete", "complete subgroup " + analysis_name, checks)
        require(analysis["analyzer_sha256"] == sha(HERE / analyzer_name), "analyzer hash " + analysis_name, checks)
        if "protocol_sha256" in analysis:
            require(analysis["protocol_sha256"] == sha(HERE / protocol_name), "analysis protocol " + analysis_name, checks)
        for name in (analysis_name, analyzer_name, protocol_name):
            evidence[rel(HERE / name)] = sha(HERE / name)
        excluded.extend(analysis.get("excluded_runs", []))
        excluded.extend(analysis.get("failed_runs_preserved", []))
        if kind == "backend":
            require(all(c["passed"] for c in analysis["checks"]), "backend evidence checks", checks)
        for case in analysis["cases"]:
            cid = case["id"]
            runs = normalized_runs(case, kind)
            require(len(runs) == 4 and {(r["variant"],r["repeat"]) for r in runs} == {(v,n) for v in ("A","B") for n in (1,2)}, "four unique formal runs " + cid, checks)
            spec = spec_for(protocol, cid)
            loaded, results, paths = {}, {}, {}
            for r in runs:
                path = ROOT / r["run"]
                result = read(path / "result.json")
                raw = path / "trajectory.npz"
                require(result["status"] == "completed", "run completed " + path.name, checks)
                require(result["protocol_sha256"] == sha(path / "protocol.json") == sha(HERE / protocol_name), "frozen run protocol " + path.name, checks)
                require(result["runner_sha256"] == sha(path / "runner.py"), "archived runner hash " + path.name, checks)
                require(r["raw_sha256"] == sha(raw) == result.get("raw_sha256", result.get("trajectory_sha256")), "raw hash " + path.name, checks)
                if "files_sha256" in result:
                    require(all(sha(path/k) == h for k,h in result["files_sha256"].items()), "all archived file hashes " + path.name, checks)
                with np.load(raw, allow_pickle=False) as archive:
                    data = {k: archive[k].copy() for k in archive.files}
                for field in ("time", "body_q", "body_qd", "joint_q", "joint_qd"):
                    require(bool(np.isfinite(data[field]).all()), "finite physical array " + path.name + "/" + field, checks)
                for field, value in data.items():
                    checked = value[1:] if kind == "drive" and field.startswith("status_") else value
                    require(bool(np.isfinite(checked).all()), "finite defined array " + path.name + "/" + field, checks)
                if kind == "drive":
                    required = {"file hashes", "installed pinned Python sources", "all raw trajectory floats finite", "samples", "full physical model mass"}
                    supplied = {c["name"]: c["passed"] for c in r["checks"]}
                    require(required <= supplied.keys() and all(supplied[n] for n in required), "drive evidence checks " + path.name, checks)
                if kind == "loop":
                    require(all(r["criteria"][k] for k in ("protocol_hash","runner_hash","raw_hash","all_arrays_finite")), "loop evidence checks " + path.name, checks)
                if kind == "backend":
                    require(r["evidence_passed"], "backend run evidence " + path.name, checks)
                key = (r["variant"], r["repeat"])
                loaded[key], results[key], paths[key] = data, result, path
                adopted_directories.add(rel(path))
                for file in sorted(path.iterdir()):
                    if file.is_file():
                        evidence[rel(file)] = sha(file)
            repeat_checks = []
            for v in ("A","B"):
                for field in ("body_q", "body_qd", "joint_q", "joint_qd"):
                    aa, bb = loaded[(v,1)][field], loaded[(v,2)][field]
                    atol, rtol = tolerance(protocol, field)
                    require(aa.shape == bb.shape and bool(np.allclose(aa,bb,atol=atol,rtol=rtol)), "independent repeat " + cid + "/" + v + "/" + field, checks)
                    repeat_checks.append({"variant":v,"field":field,"atol":atol,"rtol":rtol,"max_abs_difference":float(np.max(np.abs(aa-bb))),"passed":True})
            variants, replay, initial, metrics, selected_arrays, labels = [], [], [], {}, {}, {}
            sample_kind = "targets" if cid == "kamino_fourbar_fk" else "time"
            for v in ("A","B"):
                primary = next(r for r in runs if r["variant"] == v and r["repeat"] == 1)
                path, result, data = paths[(v,1)], results[(v,1)], loaded[(v,1)]
                second_path, second = paths[(v,2)], results[(v,2)]
                config_path = path / "resolved-config.json"
                config = read(config_path) if config_path.exists() else result["resolved_config"]
                if not config_path.exists():
                    config_path = path / "result.json"
                treatment = spec.get("variants", {}).get(v, {})
                if isinstance(treatment, dict):
                    treatment = {**treatment, **({"dt_s":spec["dt_s"]} if "dt_s" in spec else {})}
                env = read(path / "environment.json")
                metrics[v] = primary["metrics"]
                variants.append({"variant":v,"run_id":result.get("run_id",path.name),"metrics":primary["metrics"],"raw_file":rel(path/"trajectory.npz"),"raw_sha256":sha(path/"trajectory.npz"),"program_sha256":result["runner_sha256"],"protocol_sha256":result["protocol_sha256"],"scene_sha256":sha(path/"scene.json"),"environment":environment_summary(env),"config":compact_config(config,treatment,config_path),"result_file":rel(path/"result.json"),"reproduction":{"result_file":rel(second_path/"result.json"),"run_id":second.get("run_id",second_path.name),"raw_file":rel(second_path/"trajectory.npz"),"raw_sha256":sha(second_path/"trajectory.npz"),"program_sha256":second["runner_sha256"],"protocol_sha256":second["protocol_sha256"],"tolerances":{field: {"atol":tolerance(protocol,field)[0],"rtol":tolerance(protocol,field)[1]} for field in ("body_q","body_qd","joint_q","joint_qd")}}})
                names = protocol["scene"].get("body_names", ["rotor"] if kind == "drive" else ["guided_sphere"])
                labels[v] = ("A: open chain" if v=="A" else "B: closed loop") if "fourbar_loop" in cid else ("A: PADMM" if v=="A" else "B: DVI") if kind=="backend" else "Variant " + v
                replay.append({"variant":v,"label":labels[v],"times":data["time"].tolist(),"body_q":data["body_q"].tolist(),"body_names":names,"sample_kind":sample_kind})
                initial.append({"variant":v,"body_q":data["body_q"][0].tolist(),"body_count":data["body_q"].shape[1],"particle_count":0,"truncated":False,"sample_kind":sample_kind})
                selected_arrays[v] = data
            physical = "passed" if (case.get("physical_criteria_passed", False) and case["metrics"]["narrow_tail_agreement_passed"] if kind=="backend" else case.get("status")=="passed") else "failed_criteria"
            refs = [{**r,"commit":COMMIT,"sha256":sha(ROOT/"sources/newton-v1.7.0"/r["path"]),"url":f"https://github.com/newton-physics/newton/blob/{COMMIT}/{r['path']}#L{r['line']}"} for r in case["source_refs"]]
            assoc, assoc_scope = associations(cid,pids,mids)
            require(set(assoc) <= valid_ids, "actual parameter/model-input IDs " + cid, checks)
            limitations = "；".join(case["limitations"]) + "。" + assoc_scope + " 初始未求解 status 在驱动/reset 原始数据中可为未定义占位；物理状态数组必须全部有限。"
            item = {"id":cid,"record_id":"lab:"+cid,"solver":"kamino","title":case["title"],"parameter":" ".join(n.removeprefix("newton:1.7.0:kamino:") for n in assoc),"observation":text_observation(case,kind,metrics),"associations":assoc,"association_relation":"measures_behavior_of","association_scope":assoc_scope,"experiment_kind":"mechanism","variants":variants,"source_refs":refs,"limitations":limitations,"initial_geometry":initial,"artifact_root":"experiments/kamino_mechanism_lab/","curve_file":rel(HERE/(cid+".svg")),"runner_file":rel(paths[("A",1)]/"runner.py"),"protocol_file":rel(paths[("A",1)]/"protocol.json"),"viewer_url":"/files/experiments/kamino_mechanism_lab/index.html?case="+cid,"program_source_call":{"tool":"get_source","arguments":{"scope":"experiment","path":rel(paths[("A",1)]/"runner.py").removeprefix("experiments/"),"max_lines":100}},"physical_acceptance":physical,"evidence_valid":True,"sample_kind":sample_kind}
            plot_case(cid,selected_arrays,protocol["scene"],labels,sample_kind)
            evidence[item["curve_file"]] = sha(ROOT/item["curve_file"])
            all_cases.append(item)
            report_cases.append({**item,"replay":replay,"plot":cid+".svg","acceptance_results":{"subgroup_case":case,"independent_aggregate_repeat_checks":repeat_checks}})
    require(len(all_cases)==8 and len(adopted_directories)==32,"8 cases and 32 formal runs",checks)
    # Preserve provenance for excluded harness attempts too, without promoting them.
    for path in sorted(HERE.glob("*/harness-revisions.json")):
        evidence[rel(path)] = sha(path)
    for path in sorted(HERE.glob("*/runs/*/result.json")):
        if rel(path.parent) not in adopted_directories:
            for file in sorted(path.parent.iterdir()):
                if file.is_file():
                    evidence[rel(file)] = sha(file)
    excluded = list({Path(r.get("run", r.get("run_id", ""))).name: r for r in excluded}.values())
    report = {"schema_version":"1.0","version":"1.7.0","commit":COMMIT,"status":"passed","status_meaning":"Evidence integrity and completeness only. Per-case physical_acceptance records all frozen physical failures.","cases":report_cases,"checks":checks,"excluded_harness_attempts":excluded,"formal_runs":32,"limitations":"CPU only. Two deterministic repetitions do not establish cross-hardware determinism or statistical significance. No GPU, multiworld, masked reset, contact-rich or general FK branch coverage."}
    write(HERE/"report-data.json",report)
    catalog = {"schema_version":"1.0","phase":"kamino-mechanisms","status":"passed","status_meaning":report["status_meaning"],"cases":all_cases,"formal_runs":32,"analyzer_sha256":sha(Path(__file__)),"report_sha256":sha(HERE/"report-data.json"),"evidence_files":evidence,"physical_acceptance_counts":{s:sum(c["physical_acceptance"]==s for c in all_cases) for s in ("passed","failed_criteria")}}
    write(HERE/"catalog.json",catalog)
    lines = ["# Kamino 机制实验与适用边界", "", "固定 Newton 1.7.0，commit `"+COMMIT+"`。先冻结场景、指标与门槛，再运行；所有原始尝试均保留。", "", "本轮 8 个机制案例、32 个正式独立进程运行。catalog 的 passed 仅表示证据完整性通过；物理失败案例仍显示 failed_criteria，不会因被收录而变成已验证。", "", "| 案例 | 物理验收 | 观察 |", "|---|---|---|"]
    lines += [f"| [{c['id']}]({c['id']}.svg) | {c['physical_acceptance']} | {c['observation']} |" for c in all_cases]
    lines += ["", "## 证据与复现", "", "[机器可读目录](catalog.json)、[完整回放/门槛报告](report-data.json)。原始 NPZ 包括每个保存时刻的 body/joint 状态；交互回放仅画 X-Z 投影中的 body 坐标系和轨迹，不伪造模型外观。FK 的横轴是有序目标查询编号，不能解读为物理时间。", "", "```powershell", ".\\experiments\\.venv_multisolver\\Scripts\\python.exe -B -X utf8 experiments/kamino_mechanism_lab/analyze_experiments.py", "```", "", "此聚合命令只重新分析已保存证据，不运行物理。各正式 run 包含冻结 protocol.json 与 runner.py，result.json 保存设置与程序指纹；重复原实验需遵循各子目录 DESIGN/REPRODUCE 及归档程序的 CLI。重跑应创建新 run 目录，不能覆盖已有原始结果。", "", "## 失败与排除账本", "", "原开链 dt=1/240 的关节漂移和后续步长下仍失败的标准保留为物理负结果。另有安装路径假设、源验证/懒分配观测列等 harness 修正；其较早尝试没有计入 32 个正式运行，见 [loop 修正记录](loop_fk/harness-revisions.json) 和 [drive/reset 修正记录](drive_reset/harness-revisions.json)。逐次排除理由在 report-data.json 中，所有旧 run 与哈希继续保存。", "", "## 未覆盖范围", "", "GPU、多 world、masked reset、接触历史匹配、复杂接触/闭环组合、非饱和 PD 跟踪、力限切换、多 DoF 混合驱动、奇异/多分支 FK 和长期稳定性仍未验证。PADMM/DVI 的残差同名但定义不同，不用收敛标记或迭代次数排名性能/准确性。关联参数表示 measures_behavior_of，固定的 alpha/integrator 等不计为新增单参数 A/B 覆盖。"]
    (HERE/"README.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps({"cases":8,"formal_runs":32,"physical_acceptance":catalog["physical_acceptance_counts"],"evidence_files":len(evidence),"checks":len(checks)},ensure_ascii=False))


if __name__ == "__main__":
    main()
