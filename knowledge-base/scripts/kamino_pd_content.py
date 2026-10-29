"""Generate bounded-PD documentation from archived, separately judged experiments."""
from urllib.parse import quote


def pd_experiment_sections(cases):
    measured = [c for c in cases if c.get("experiment_kind") == "pd_diagnostics"]
    if not measured:
        return "", ""
    runs = {v["run_id"] for c in measured for v in c["variants"]}
    runs |= {v["reproduction"]["run_id"] for c in measured for v in c["variants"]}
    passed = sum(c["physical_acceptance"] == "passed" for c in measured)
    brief = (
        "\n## 有界 PD 后续诊断与跟踪实测\n\n"
        f"新增 {len(measured)} 组配对案例、{len(runs)} 次唯一正式运行，{passed} 组达到事前物理门槛。"
        "诊断配对复用同一严格基线，运行数不重复计数。实验分别检查观测一致性、"
        "配置停止条件、原始严格停止条件和实际运动误差。"
        "详见 [PD 收敛、非饱和跟踪与力限切换](pd-experiments.md)。"
        "原饱和驱动 0% 收敛记录保持不变；后续实验不能将旧结果追认成收敛。\n"
    )
    full = "# Kamino · 有界 PD 收敛、跟踪与力限切换\n\nNewton 1.7.0；CPU、单 world。\n" + brief
    full += "\n## 场景与保存结果\n\n| 场景 | 物理门槛 | 实测结果 |\n|---|---|---|\n"
    for c in measured:
        outcome = "通过" if c["physical_acceptance"] == "passed" else "未通过，保留负结果"
        full += f"| [{c['title']}](#/record/{quote(c['record_id'], safe='')}) | {outcome} | {c['observation'].replace('|', '/')} |\n"
    diagnosis = next((c.get("diagnosis_evidence") for c in measured if c["id"] == "kamino_pd_iteration_budget"), None)
    if diagnosis:
        full += "\n## 本轮对 0% 标记的解释\n\n"
        full += diagnosis["interpretation"] + "\n\n"
        full += (
            "旧有效步中只有互补残差未达标；新基线与旧轨迹和有效终止 status 一致，独立重算也匹配源停止规则。"
            "因此旧 0% 结果不是初始占位或统计读取错误。当前证据支持这个饱和场景的有限精度停滞；"
            "严格要求本身未被修复。互补容差对照的唯一配置改动是停止容差，提前停止产生细小轨迹变化，"
            "实际运动仍满足物理门槛，不能称为原严格要求已经通过。\n"
        )
    full += (
        "\n## 观测、容差与求解器行为如何区分\n\n"
        "1. 观测检查只读原始数组，排除首次 step 前未定义 status；将保存的内迭代变量独立重算为残差与停止布尔值，且新基线与旧基线比较。CPU `.numpy()` 可能返回共享视图，跨迭代快照必须复制；测试程序修正及被排除尝试单列留档。\n"
        "2. 严格基线的 primal/dual/complementarity 容差均为 `1e-7`、预算为 200。只将互补容差改为 `1e-6` 的案例仍同时按原 `1e-7` 重新评分；配置停止通过不能当作原精度要求已解决。\n"
        "3. 增加预算、关闭加速、关闭预条件分别是独立干预。内迭代停滞、ULP 与残差乘积可支持有限精度敏感性的解释；没有同等 float64 求解实现，不证明通用精度下限或所有场景的算法缺陷。\n"
        "\n有界行互补残差按 `abs((x-lower)*max(z,0)+(upper-x)*max(-z,0))` 计算，使用未投影 `x` 和更新后的 `z`；"
        "预条件缩放在乘积中相消，单位为 J。实际投影力矩达到限值，并不保证该残差通过。停止还要求迭代数大于 1，且三类残差分别低于各自阈值。\n"
        "\n## 非饱和跟踪的独立参考\n\n"
        "对 COM 位于转轴的单轴转子，惯量 `I=1 kg·m²`，无外力时使用双精度标量递推：\n\n"
        "```text\nv_next = (I*v + h*(kp*(qref-q) + kd*vref_used)) / (I + h*kd + h*h*kp)\nq_next = q + h*v_next\ntau = I*(v_next-v)/h\n```\n\n"
        "POSITION 模式仍含阻尼，但 `vref_used=0`；POSITION_VELOCITY 使用给定速度目标。"
        "非饱和参考不裁剪力矩，实际与参考都必须保持冻结的限值裕量。"
        "阶跃反向检查全瞬态、终值、镜像与能量；正弦检查指定频率下的跟踪和模式语义。"
        "这不是任意带宽、增益或步长的调参结论。\n"
        "\n## 力限切换的公开契约\n\n"
        "仅测试已有有界 PD 行的有限正值力限修改：更新 `Model.joint_effort_limit` 后，"
        "在下一步前调用 `notify_model_changed(JOINT_DOF_FORCE_PROPERTIES)`。"
        "新一步组装的冲量界应为 `dt*limit`；通知本身不得跳变姿态或速度。"
        "实验分别核对正/负饱和、释放、重新饱和及第一次使用新力限的步。"
        "零、无穷、增删约束行或模式/增益变化不在这个合同内。\n"
    )
    full += "\n## 每组适用边界\n\n"
    for c in measured:
        full += f"- **{c['title']}**：{c['limitations']}\n"
    full += "\n## 仍未覆盖\n\n多关节与复杂接触、GPU/graph、多 world、不同幅值/频率/增益/时间步扫描、结构性力限变化、长时间稳定性和论文基准复现。当前结果不直接建议修改 Newton 默认配置。\n\n[原始证据、冻结协议与复现](../../experiments/kamino_pd_lab/README.md)。\n"
    return brief, full
