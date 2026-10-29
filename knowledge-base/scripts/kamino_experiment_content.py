"""Generate scoped interpretation from frozen mechanism experiment results."""
from urllib.parse import quote


def experiment_sections(cases):
    measured = [c for c in cases if c.get("experiment_kind") == "mechanism"]
    if not measured:
        return "", ""
    passed = sum(c["physical_acceptance"] == "passed" for c in measured)
    brief = (
        "\n## 已保存的机制实验\n\n"
        f"已有 {len(measured)} 组 Kamino / CPU 机制对照，其中 {passed} 组满足各自事前物理门槛；"
        "未通过的对照也保留原始数据和失败条件，不能作为已验证的调参建议。"
        "场景、指标与门槛先冻结，每个设置由两个独立进程重复。"
        "实测覆盖四杆闭环/FK、PADMM–DVI 配置组、力限及 default/preserve reset；"
        "它们是指定场景的行为证据，不等于所有相关参数都完成了单因素扫描。"
        "详见 [机制实验与验收](experiments.md) 和 [原始数据与复现](../../experiments/kamino_mechanism_lab/README.md)。\n\n"
        "求解器的 `converged`、速度层残差、位置几何误差及重复性分开报告。"
        "残差定义随后端变化，触及迭代上限也不能被隐藏为成功收敛；"
        "同样，速度层收敛不能证明有限时间步下关节位置约束准确。\n"
    )
    drive = next((c for c in measured if c["id"] == "kamino_drive_effort_paths"), None)
    if drive:
        pd = next(v for v in drive["variants"] if v["variant"] == "B")["metrics"]
        brief += (
            f"\n**驱动场景的诊断限制：** 有界隐式 PD 的收敛标记比例为 {pd['status_converged_fraction']:.0%}，"
            f"最大迭代数达到 {pd['status_iterations_max']}；末步互补残差 `r_c` 为 {pd['terminal_residuals']['r_c']:.3g} J。"
            "在冻结的严格容差下，本组通过的是实际力矩和运动参考门槛，求解器收敛检查并未通过；"
            "没有放宽容差来改写该结果。\n"
        )
    full = "# Kamino · 机制实验与适用边界\n\nNewton 1.7.0；仅 CPU、单 world。\n" + brief
    full += "\n| 事前设计的场景 | 物理验收 | 保存结果 |\n|---|---|---|\n"
    for c in measured:
        status = "通过预设门槛" if c["physical_acceptance"] == "passed" else "未通过，保留负结果"
        full += f"| [{c['title']}](#/record/{quote(c['record_id'], safe='')}) | {status} | {c['observation'].replace('|', '/')} |\n"
    full += "\n## 如何使用这些结果\n\n"
    full += (
        "- FK 是目标姿态查询，不是动态跟踪。平行四边形解析参考只覆盖已测非奇异分支。\n"
        "- 拓扑对照和时间步细化是不同干预；原粗步长失败不被细步长成功替换。\n"
        "- PADMM 与 DVI 比较的是完整后端配置组，包括默认 Jacobian/线性求解器选择及 DVI 禁用预条件的强制条件；不按相同迭代数或收敛比例排名。\n"
        "- 力限场景检验正反饱和路径；不支持无饱和 PD 跟踪或任意关节/材料的调参结论。\n"
        "- reset 比较运行过的求解器和全新求解器，并明确恢复默认或保留 body 状态。外部 Control 由调用方重新下发，不因 reset 自动清空。\n"
        "- 原始 status 在首次 step 前尚未定义；初始占位不作为有效收敛样本。所有物理状态、实际力矩和后续 status 按协议复核。\n"
    )
    full += "\n## 本组仍未覆盖\n\n这八组机制实验本身不覆盖多 world 和 masked/flags/callback 部分 reset、FK 奇异位形及全局分支选择、复杂闭环接触、非饱和驱动跟踪、Moreau、稀疏动态/预条件/容差全面扫描、模型变更通知、材料分组分裂、GPU/graph 和长时间稳定性。后续 PD 诊断、跟踪和有限力限通知实验另列，不能用新增局部结果追认本组未测范围。论文映射仍是源码与机制解释，当前实验不是论文基准复现。\n"
    return brief, full


def link_mapping_evidence(mappings, cases):
    available = {c["id"]: c for c in cases if c.get("experiment_kind") == "mechanism"}
    links = {
        "map:kamino:padmm_projection_dual": (
            "kamino_drive_effort_paths",
            "单 revolute 的正反饱和力矩与有界 implicit PD 输出，记录实际路由及报告 effort",
            "未隔离证明投影 kernel 或论文算法；未验证无饱和跟踪、其他关节及所有停止容差",
        ),
        "map:kamino:physical_residuals_backend_boundary": (
            "kamino_backend_guided_contact",
            "同一倾斜导轨单接触场景的 PADMM/DVI 配置组、实际状态和各自残差时间序列",
            "同名残差和收敛率不能直接比较准确性；未覆盖稀疏动态、复杂接触、性能或论文基准",
        ),
    }
    for mapping in mappings:
        if mapping["id"] not in links:
            continue
        cid, scope, limitation = links[mapping["id"]]
        case = available.get(cid)
        if case:
            mapping["local_experiments"] = [{"record_id": case["record_id"], "scope": scope, "limitation": limitation}]
            mapping["unvalidated_scope"] = [limitation]
            mapping["validation_status"] = "partial_local_evidence"
