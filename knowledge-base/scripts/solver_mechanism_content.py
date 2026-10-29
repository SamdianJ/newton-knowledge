"""Reviewed solver concepts and paper correspondences; no generation side effects.

Source anchors are resolved against extend_solvers' immutable Newton snapshot.
PDF page numbers are physical PDF pages in the local evidence copies.
"""

MU = "newton/_src/solvers/mujoco/solver_mujoco.py"
KA = "newton/_src/solvers/kamino/solver_kamino.py"
CONV = "newton/_src/solvers/kamino/_src/core/conversions.py"
PAD = "newton/_src/solvers/kamino/_src/solvers/padmm/solver.py"
KERNELS = "newton/_src/solvers/kamino/_src/solvers/padmm/kernels.py"
DVI = "newton/_src/solvers/kamino/_src/solvers/dvi/solver.py"
EXTRA_SOURCE_FILES = [KERNELS]


def paper(key, page, locator):
    return f"[{key} · PDF p.{page} · {locator}](../../sources/papers/{key}/paper.pdf#page={page})"


def mechanism_records(solver, byname, ref):
    """Additional mappings, separate from the retained implementation-fact IDs."""
    specs = {
        "mujoco": [
            (
                "compiled_model", "模型编译层次与广义坐标前向动力学的职责划分",
                ["mujoco-2012", "mujoco-2014"],
                paper("mujoco-2012", 6, "III-A，模型三级表示") + "；" + paper("mujoco-2014", 2, "II-A/B，式(1)–(3)"),
                "2012 论文把建模描述、运行时模型和编译后动力学结构分层；2014 式(3)把质量矩阵、外力、约束冲量连接到速度更新。Newton 的 SolverMuJoCo._convert_to_mjc 将 Model 映射到现代 MjSpec 并调用 spec.compile()；step 将控制/状态交给 mj_step 或 _mujoco_warp_step。质量矩阵、偏置力、约束动力学和积分由 MuJoCo / MuJoCo Warp 后端执行。",
                "2012 的 C++ 建模 API 不是当前 MjSpec 的逐行说明；Newton 包装层没有自行实现论文中的 CRB/RNE/质量矩阵分解。2014 模型的数学角色用于解释数据流，具体积分器和支持能力以锁定包装层及实际后端版本为准。",
                ["use_mujoco_cpu", "integrator"],
                [(MU, "def _convert_to_mjc(", "SolverMuJoCo._convert_to_mjc"), (MU, "self.mj_model = spec.compile()", "MjSpec.compile call site"), (MU, "def step(", "SolverMuJoCo.step")],
            ),
            (
                "soft_constraint_regularization", "软约束正则化与包装层材料/限位参数转换",
                ["mujoco-2014"], paper("mujoco-2014", 2, "II-C，式(4)；p.3 式(5)–(7)") + "；" + paper("mujoco-2014", 4, "II-E，式(10)–(11)"),
                "软化的 Gauss 原理通过正则化允许有限约束偏差；接触目标中 R 与参考速度影响响应。Newton 的 _update_solref_from_invweight0 把关节限位 force-space ke/kd 按 dof_invweight0 与 solimp 的 dmax 换算为后端 solref；_convert_contacts_to_mjwarp 负责外部接触转换。正则化约束系统的组装和求解由后端完成。",
                "论文 R、参考速度与现代 solref/solimp 只有机制层对应，不能把论文 R 直接当成 Newton ke。关节限位换算与逐接触 force-space 修正不同；后者只适用于 Warp + Newton contacts，native CPU 不消费外部 contacts。保留 raw authored solreflimit、隐式导入默认和 refsafety 的现代分支，均不是论文逐项指定。",
                ["use_mujoco_contacts", "use_mujoco_cpu", "impratio"],
                [(MU, "def _update_solref_from_invweight0(", "SolverMuJoCo._update_solref_from_invweight0"), (MU, "def _convert_contacts_to_mjwarp(", "SolverMuJoCo._convert_contacts_to_mjwarp")],
            ),
            (
                "friction_cone_optimization", "接触空间、摩擦锥与正则化凸优化",
                ["mujoco-2014"], paper("mujoco-2014", 3, "II-D，式(8)–(9)") + "；" + paper("mujoco-2014", 4, "II-E，式(10)–(11)"),
                "式(8)用接触空间矩阵 A=J Mhat^-1 J^T 连接冲量与接触速度，式(9)规定摩擦可行域，式(11)在该域中最小化正则化二次目标。Newton 的 _convert_to_mjc 传递 cone、solver、iterations、tolerance 等选项；_mujoco_warp_step / step 调用实际后端求解。condim 决定切向、扭转和滚动分量，cone 决定后端采用的锥近似。",
                "Newton 没有在此包装类内实现式(11)的优化器。2014 论文的 GPGS 不等同于现代后端提供的 CG/Newton 等选项；不能由论文推定两后端能力、收敛速度或结果相同。论文 III 节的解析逆动力学也不是 SolverMuJoCo.step 的对外能力承诺。",
                ["cone", "solver", "iterations", "tolerance"],
                [(MU, "def _convert_to_mjc(", "SolverMuJoCo._convert_to_mjc"), (MU, "def _mujoco_warp_step(", "SolverMuJoCo._mujoco_warp_step"), (MU, "def step(", "SolverMuJoCo.step")],
            ),
        ],
        "kamino": [
            (
                "padmm_variables_desaxce", "PADMM 变量分裂与 De Saxcé 修正",
                ["proximal-admm-2024", "kamino-loops-2025"], paper("proximal-admm-2024", 6, "III-B/C，式(32)–(36)") + "；" + paper("kamino-loops-2025", 23, "VI-F，式(165)–(166)；p.24 式(167a)"),
                "PADMM 中 x 是无约束冲量迭代，y 是投影后的可行冲量，z 是使二者一致的对偶变量，s 是 De Saxcé 速度修正；它们不是刚体位置。2024 的 f/y/z 分裂在 2025 报告中扩展为含双边关节、限位和接触的最大坐标系统。当前 _step 先调用 _update_desaxce_and_velocity_bias，以接触局部切向滑移估计法向修正并构造全体约束的线性右端；只有接触块需要该摩擦修正。",
                "变量在当前求解器内可经对角预条件缩放，不能直接把 x/y 当成最终物理冲量。当前融合 kernel、可选加速和 GPU 批处理是实现细节，不是论文代码逐行复现；非接触双边约束不因此变成摩擦锥。",
                ["config.padmm.eta", "config.padmm.rho_0", "config.dynamics.preconditioning"],
                [(PAD, "def _step(", "PADMMSolver._step"), (PAD, "def _update_desaxce_and_velocity_bias(", "PADMMSolver._update_desaxce_and_velocity_bias"), (KERNELS, "def _compute_desaxce_correction(", "_compute_desaxce_correction")],
            ),
            (
                "padmm_linear_subproblem", "近端线性子问题与 Delassus 求解",
                ["proximal-admm-2024", "kamino-loops-2025"], paper("proximal-admm-2024", 6, "III-C，式(36a)、(37)") + "；" + paper("kamino-loops-2025", 24, "VI-F，式(167b)、(168)"),
                "近端项 eta 与增广罚参数 rho 共同正则化线性子问题。在未缩放记法下，(D+(eta+rho)I)x = -v_f-s+eta*x_prev+rho*y_prev+z_prev。当前 _compute_velocity_bias 的符号与该右端一致；_update_unconstrained_solution 调用 problem._delassus.solve，_update_regularization 管理对应正则项。线性求解器/稀疏选项属于 dynamics 配置，eta/rho 不是材料接触刚度。",
                "该式解释 PADMM 的基本非加速迭代；当前默认启用加速，实际迭代按加速分支阅读。预条件和自适应罚参数也需按当前分支读代码。2024 的 G+R 与 2025 的 D 记号不应直接当成同名数组；当前 Delassus 对象还包含关节、限位及驱动相关约束。未复现论文性能。",
                ["config.padmm.eta", "config.padmm.rho_0", "config.dynamics.linear_solver_type", "config.sparse_dynamics"],
                [(KERNELS, "def _compute_velocity_bias(", "_compute_velocity_bias"), (PAD, "def _update_unconstrained_solution(", "PADMMSolver._update_unconstrained_solution"), (PAD, "def _update_regularization(", "PADMMSolver._update_regularization")],
            ),
            (
                "padmm_projection_dual", "可行集合投影与对偶变量更新",
                ["proximal-admm-2024", "kamino-loops-2025"], paper("proximal-admm-2024", 6, "III-C，式(36b/c)、(38)–(39)") + "；" + paper("kamino-loops-2025", 24, "VI-F，式(167c/d)、(169)"),
                "基本迭代把 x-z_prev/rho 投影到可行集得到 y，再以 z=z_prev+rho*(y-x) 更新对偶变量。当前 _update_projection_argument 准备投影输入，_project_to_feasible_cone 分别处理有界乘子、非负限位和 Coulomb 接触锥；无界双边乘子不需要同样的锥截断。make_update_dual_variables_and_compute_primal_dual_residuals 实现 z 更新与残差。",
                "论文式展示基本迭代；当前加速/松弛路径、批量约束布局和 effort-limited implicit PD 的有界乘子扩展必须从源码辨识。PADMM 的全局线性子问题加投影，不等同于 DVI 每次局部 PGS 扫描。",
                ["config.padmm.rho_0", "config.padmm.max_iterations"],
                [(PAD, "def _update_projection_argument(", "PADMMSolver._update_projection_argument"), (KERNELS, "def _project_to_feasible_cone(", "_project_to_feasible_cone"), (KERNELS, "def make_update_dual_variables_and_compute_primal_dual_residuals(", "make_update_dual_variables_and_compute_primal_dual_residuals")],
            ),
            (
                "physical_residuals_backend_boundary", "停止残差的物理单位与 DVI 实现边界",
                ["proximal-admm-2024", "kamino-loops-2025"], paper("proximal-admm-2024", 6, "III-D，式(40)–(43)") + "；" + paper("kamino-loops-2025", 24, "VI-F，式(170a–c)"),
                "论文用原始共识、对偶变化和互补性残差检查迭代。当前 PADMM 报告 r_p=||P(x-y)||inf（冲量），r_d=||P^-1[eta*Δx+rho*Δy]||inf（速度），r_c 为不等式块冲量与速度内积绝对值最大值（能量）。_update_convergence_check 对照各自容差，status 给每 world 的终态。DVI 当前 solve/_solve_dense_inequality_pgs 则组合双边直接解与单边投影扫描，其 r_p 是物理冲量锥投影距离，r_d 是对偶锥距离/双边速度违反，r_c 是互补内积。",
                "三个残差都是物理量的绝对最大值，不除以约束数或参考范数，不能无量纲混合比较。PADMM 公式映射不证明 DVI 逐行复现上述论文；DVI 的定义依据当前 docs/solvers/kamino.rst 和源码。收敛标记与有限步轨迹精度/物理真实性不同，仍需实验。",
                ["config.padmm.primal_tolerance", "config.padmm.dual_tolerance", "config.padmm.compl_tolerance", "config.dvi.omega"],
                [(PAD, "def _update_convergence_check(", "PADMMSolver._update_convergence_check"), (KERNELS, "def make_update_dual_variables_and_compute_primal_dual_residuals(", "make_update_dual_variables_and_compute_primal_dual_residuals"), (DVI, "def solve(", "DVISolver.solve"), (DVI, "def _solve_dense_inequality_pgs(", "DVISolver._solve_dense_inequality_pgs"), ("docs/solvers/kamino.rst", "These are absolute maxima", "Terminal residual definitions")],
            ),
        ],
    }
    result = []
    for key, title, papers, locator, correspondence, boundary, params, anchors in specs[solver]:
        refs = [ref(path, needle) for path, needle, _ in anchors]
        result.append({
            "id": f"map:{solver}:{key}", "solver": solver, "title_zh": title,
            "paper_id": "paper:" + papers[0], "paper_ids": ["paper:" + p for p in papers],
            "paper_locator": locator, "correspondence": correspondence, "boundary": boundary,
            "parameter_ids": [byname[n]["id"] for n in params], "source_refs": refs,
            "symbols": [{"name": anchor[2], "path": r["path"], "line": r["line"], "url": r["url"]} for anchor, r in zip(anchors, refs)],
            "mapping_kind": "mechanism_correspondence", "evidence_type": "curated_mapping",
        })
    return result


def concept_sections(ref, cite):
    def source(path, needle):
        return cite(ref(path, needle))

    mujoco = """
## 模型转换概念导航

| 概念 | Newton → MuJoCo 的主要语义与边界 |
|---|---|
| joint | FREE/BALL/REVOLUTE/PRISMATIC 分别映射 free/ball/hinge/slide；D6 按活动轴展开至最多 3 slide + 3 hinge；FIXED 合入层级或世界根 mocap。DISTANCE 被丢弃（保留自由体记账），ROD 不转发，不能据此宣称支持。 |
| geometry | sphere/capsule/cylinder/box/ellipsoid 直接转换；plane 必须挂 world 且碰撞为无限平面；heightfield 归一化并修正基准高度。mesh 的凸包由 MuJoCo compiler 处理；cone 是离散网格近似，改变尺寸需重建；Gaussian 不支持。SITE 是引用标记而非碰撞形状。非凸/SDF/hydroelastic 需 Newton 碰撞管线和 Warp 外部接触路径。 |
| equality / mimic | CONNECT、WELD、JOINT equality 经 builder.add_custom_values 的 mujoco:equality_constraint_* 命名空间提供，不能假设有通用 add_equality API；set_joint_mimic 生成含 offset/multiplier 的 JOINT equality，覆盖 revolute/prismatic/D6 标量轴。闭环 FIXED/REVOLUTE/BALL 转为相应等式；闭环的驱动、限位等不会新增广义坐标，部分其他 joint 类型警告跳过。 |
| tendon / general actuator | tendon 通过 mujoco 自定义命名空间与 MJCF/USD 导入；空间 tendon 的 site/geom/pulley 路径受支持性检查，不支持或退化路径警告跳过。general actuator 可表达增益/偏置/动态/传动及范围，不能由简单 joint target 参数概括。 |
| kinematic root | 只支持运动学根，子体可动态；非 fixed 根用普通关节与大 armature 处理，fixed 世界根和全锁 D6 用 mocap。输入 joint_q/qd 写回时保留，施加其上的 body wrench/joint force 忽略，接触仍存在。 |
| dof_ref | Newton 标量 joint_q、limit、position target 相对 authored pose；后端 qpos/range/位置控制加回 ref，qd 不变。native dof_springref / actuator_ctrlrange 保持绝对语义。改变 ref 后通知 JOINT_REFERENCE_POSE_PROPERTIES。 |
| limit gains / passive dynamics | force-space joint_limit_ke/joint_limit_kd 经 dof_invweight0*(1-dmax) 缩放后转换 solreflimit；raw authored 值与隐式 MJCF 默认分开。正值 solref 可被 refsafe 时间步保护钳制。joint_damping、frictionloss、armature 与 PD target gains 含义不同。tendon limit gains 有独立 mode 和 TENDON_PROPERTIES 通知，不等于被动 tendon_damping。 |
| collision filtering | 保留单一导入域的 contype/conaffinity 原生掩码时，掩码仍是权威；collision_mask_domain 是导入来源标签，本身不是过滤器。混合域/原生 Newton 形状/新增排除对时编译允许对。32 位表达能力有限，大图可能走近似回退；显式 pair 可绕过 mask，仍须核对其他过滤。不要假设任意 Newton 排除图都无损映射。 |

"""
    mujoco += "固定入口：" + "；".join([
        source(MU, "def _convert_to_mjc("), source(MU, "def _init_tendons("), source(MU, "def _init_actuators("),
        source(MU, "def _init_pairs("), source(MU, "def _update_solref_from_invweight0("),
    ]) + "。\n\n完整转换规则按固定版本官方文档继续索引：" + source("docs/solvers/mujoco.rst", "Joint types") + "。\n"

    kamino = """
## 驱动、FK、reset 和运行期更新边界

动力学按 DoF 路由 explicit effort、无界 implicit PD、effort-limited implicit PD。速度模式必须有非零 kd，位置类模式至少有适用的非零 ke/kd；关节动力学与 implicit PD 当前只支持 revolute、prismatic、gimbal。Coulomb 摩擦覆盖非 free joint。FK 则按整个 joint 划分被动/驱动：同一 joint 可混合不同非被动 target mode，但不能混合被动和驱动 DoF；fk_actuation_flag 提供 joint 级显式覆盖。因此“逐 DoF 驱动支持”不代表 FK 支持逐 DoF 分区。

reset(state, world_mask, flags, config, success_mask) 原地更新所选 world；ResetConfig 分别选择 body/base pose 与 velocity 的来源，可使用 FK。默认恢复初始值，并清理内部缓存；从结果 body state 重建 joint_q/qd、清零关节约束力。被 flags 排除的状态会缓存并恢复，复杂部分重置优先明确 config；success_mask 区分未选择/失败（包括 FK 未收敛）与成功。外部 body-origin 与内部 CoM frame 的转换由包装层处理，不能只写 joint_q 就假定闭环状态已一致。

| 修改类型 | 当前允许方式与限制 |
|---|---|
| 数值属性 | 保持已分配结构时，质量/惯量、关节/形状变换、现有动态/驱动/限位数值可通过对应 ModelFlags 通知更新；包装层先验证结构不变，再更新转换缓存与内部求解器。 |
| 结构变化 | armature/damping/无界 PD 增益跨零导致动态约束分配变化、限位由有限变无限或反之、启停摩擦、增删有界 implicit PD、改变驱动分区、改变 immovability 等必须重建 SolverKamino。轴正交性与 gimbal 手性仍需有效，notify 不是任意拓扑修改接口。 |
| 内部碰撞材质表 | SHAPE_PROPERTIES 会更新内部材质；若原来共享一个 material 的 shapes 改成不同 friction/restitution，既有分组无法拆开，抛错并要求重建。 |
| 外部 Newton contacts | 直接读 shape 材质，不使用上述内部材质表；不能把内部表更新限制泛化为外部 contacts 的相同机制。 |
| 不支持的约束 | Kamino 不支持 equality/mimic/tendon；相关通知在多 solver 环境中被忽略，不表示已实现这些模型能力。 |

"""
    kamino += "固定来源：" + "；".join([
        source("docs/solvers/kamino.rst", "Actuation and forward kinematics"), source(KA, "def reset("),
        source(KA, "def notify_model_changed("), source(KA, "def _validate_structural_invariants("),
        source(CONV, "def convert_model_materials("),
    ]) + "。\n"
    return {"mujoco": mujoco, "kamino": kamino}


COVERAGE = {
    "mujoco": """
## 审核后覆盖与实验缺口

本节补齐主要模型转换导航和三组具体论文机制映射；保留的旧包装层 mapping 标为 implementation_fact，不能按条数当作论文机制覆盖率。参数目录是字段/默认/分支静态解释，不等于所有参数已充分实验。现有归档只支持各 case 记录的场景与 interventions；backend × contact-source 组合、state-sync interval 与逐步 control 的隔离对照、ref/limit 转换、过滤回退、tendon/equality/kinematic、cone/solver/收敛容差跨场景仍需专项验证。此次修复未新增或重跑物理实验。
""",
    "kamino": """
## 审核后覆盖与实验缺口

本节解释四组 PADMM 机制映射、DVI 当前实现边界、驱动/FK/reset/通知/材质概念。KAM-03 的后续实测按生成的机制实验页逐场景登记，物理通过和未通过均保留；字段/默认的静态覆盖不能当作实验证据。PADMM eta/rho/三类容差全面扫描、稠密/稀疏与预条件消融、复杂闭环多接触、驱动/FK 混合边界、数值通知与结构重建、材料分组分裂、masked/flags/callback 部分 reset 仍需后续验证。DVI 对照必须记录整组默认变化，不能冒充单参数干预；已有局部证据不能外推 Moreau、多 world、GPU、长期稳定性或论文基准。diagnostics 中 proposed/not_run 仍是诊断计划的状态，不等于没有其他已归档实验。
""",
}
