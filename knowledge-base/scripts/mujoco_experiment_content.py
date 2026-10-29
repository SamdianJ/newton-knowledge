"""Generate measured MuJoCo joint/contact interpretations without running physics."""
from urllib.parse import quote


def mujoco_experiment_sections(cases):
    measured = [c for c in cases if c.get("experiment_kind") == "mujoco_joint_contact"]
    if not measured:
        return "", ""
    run_ids = {v["run_id"] for c in measured for v in c["variants"]} | {v["reproduction"]["run_id"] for c in measured for v in c["variants"]}
    passed = sum(c["physical_acceptance"] == "passed" for c in measured)
    brief = (
        "\n## 关节、摩擦与接触的新增实测\n\n"
        f"已新增 {len(measured)} 组 native CPU 配对实验，{len(run_ids)} 次独立运行；"
        f"{passed} 组通过各自事前物理门槛。原两组迭代预算/ke-kd 接触响应实验继续保留。"
        "新增结果同时检查 Newton 输入、编译后的 MuJoCo 模型字段和实际响应，"
        "每设置独立进程重复两次。详见 [关节与碰撞实验](experiments.md)。\n"
    )
    full = "# MuJoCo · 关节、摩擦与接触参数实验\n\n固定 Newton 1.7.0 / native MuJoCo 3.15.0 / CPU、单 world。\n" + brief
    full += "\n## 场景与效果\n\n| 参数机制 | 物理验收 | 保存结果 |\n|---|---|---|\n"
    for c in measured:
        outcome = "通过" if c["physical_acceptance"] == "passed" else "未通过，保留负结果"
        full += f"| [{c['title']}](#/record/{quote(c['record_id'], safe='')}) | {outcome} | {c['observation'].replace('|', '/')} |\n"
    full += (
        "\n## 关节参数应怎样区分\n\n"
        "- `joint_damping` 是被动黏性阻尼，直接导出到 `dof_damping`；它不需要 PD 驱动。"
        "本组 Euler 参考将被动阻尼隐式积分，同时验证实际被动力与能量衰减。\n"
        "- `joint_armature` 增加广义惯量，保持 body 质量及惯量不变；同一力矩下加速度变化有独立惯量参考。它不是耗散项。\n"
        "- `joint_target_kd` 在位置驱动中改变速度反馈。实验固定 kp、只改变 kd，核对 actuator gain/bias；"
        "不能把该结果称为 kp 扫描。明确选择 Euler 后，驱动阻尼按本组离散公式验收，不能套用 Kamino 的全隐式 PD 公式。\n"
        "- `joint_limit_upper` 改变运动范围和到达时刻；MuJoCo 限位是软约束。实验检查实际范围、约束反力、有限超限与末态平衡，不假设硬裁剪或零穿透。\n"
        "\n## 摩擦需要同时检查什么\n\n"
        "滑动摩擦不仅取决于单个 shape 的 `mu`，还要核对两侧材质混合后的实际 contact friction、"
        "接触维度和法向力。每个滑动案例分别检查独立冲量平衡、持续承载和恒载荷运动参考；摩擦减速方向正确，不等于整组物理验收通过。\n\n"
        "`condim=3` 含法向和两方向切向响应；`condim=4` 还允许法线轴上的扭转摩擦。"
        "扭转案例固定扭转系数，只改变接触维度，检查自旋制动及实际接触力矩。"
        "`mu_torsional` 和 `mu_rolling` 的尺度单位是 m，不能与无量纲滑动 mu 混用。"
        "本轮扭转实验不构成 `condim=6` 滚动摩擦验证。\n\n"
        "原始较高摩擦/速度场景出现间歇承载，仍作为正式负结果保留；仅提高 `impratio` 的假设也单列检验，"
        "不能凭其名称或参数值认定接触已稳定。较低摩擦/速度区域是另行冻结的场景，不覆盖或修复原失败条件。"
        "是否通过以各案例的事前门槛为准；动能上升还需结合势能和外力判断，不能直接等同于能量注入。\n\n"
        "原生 MuJoCo 的 contact force 读取属于本实验的后端诊断，不能由此宣称 Newton 的 native CPU `CONTACT_F` 接口已受支持。\n"
        "\n## 接触响应与碰撞检测的边界\n\n"
        "正值 `solref` 的时间常数和阻尼比共同决定接触响应；固定时间常数只改阻尼比也会影响等效刚度，"
        "因此这类回弹对照不是独立 penalty 阻尼系数扫描。需同时记录实际 solref/solimp、refsafe 和时间步。\n\n"
        "接触候选生成、活动约束和实际接触力是不同事件。margin/gap 案例依据固定后端版本的语义，"
        "分别记录候选出现和约束激活时刻，并检查 Newton 导出后的实际参数及 CCD 标志；"
        "不能把检测到候选直接当作已经产生力。\n"
        "\n## 每组适用边界\n\n"
    )
    for c in measured:
        full += f"- **{c['title']}**：{c['limitations']}\n"
    full += "\n## 仍未覆盖\n\nMuJoCo Warp/GPU、复杂多关节耦合、多 world、滚动摩擦参数扫描、各向异性/复杂接触、所有增益/步长/容差组合、长时间稳定性和论文基准。案例演示的效果只在已保存场景成立，不直接生成通用推荐参数。\n\n[原始证据、冻结协议与复现](../../experiments/mujoco_joint_contact_lab/README.md)。\n"
    return brief, full
