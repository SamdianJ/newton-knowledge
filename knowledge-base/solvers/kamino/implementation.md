# Kamino · 源码导读

Newton 1.7.0，commit `7e75abe28b8d69522bc0b34837aaed2c303dff5a`。

## 构造与默认解析

公开入口为 `SolverKamino(model, config=None)`。未提供 config 时从 Model 的 Kamino 自定义属性构造。Config 的 `__post_init__` 建立启用的子配置并校验组合。

- 默认 PADMM：sparse_jacobian=False、sparse_dynamics=False；dynamics 子配置采用其默认 LLTB 和 preconditioning=True。
- DVI、非稀疏动力学：sparse_jacobian 默认 True；Config 自动建立 preconditioning=False、linear_solver_type=LLTBRCM 的 dynamics 子配置。
- DVI、稀疏动力学：同样禁用 preconditioning，动力学线性求解改为 CR，并提供 maxiter=9 的依赖默认 kwargs。

直接实例化 `ConstrainedDynamicsConfig()` 的默认值与嵌入特定后端 Config 后的值不同。不能在 Config 创建完成后只改 dynamics_solver 就假设所有默认值同步变化。

## step 管线

Newton 数据转换 → 初始状态/FK（按配置）→ 接触与限位 → Jacobian / dynamics / dual problem → PADMM 或 DVI → 时间积分 → Newton 输出。默认 `use_collision_detector=False`；调用方需要按接口提供 contacts。Moreau 需要内部碰撞检测路径。

## 诊断接口

`solver.status` 持续维护每 world 的终止记录，不要求 collect_solver_info=True；额外统计和 solution metrics 会增加开销。读取设备数据到 host 会同步。


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

固定来源：[docs/solvers/kamino.rst:129](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/kamino.rst#L129)；[newton/_src/solvers/kamino/solver_kamino.py:899](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L899)；[newton/_src/solvers/kamino/solver_kamino.py:1198](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L1198)；[newton/_src/solvers/kamino/solver_kamino.py:1558](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L1558)；[newton/_src/solvers/kamino/_src/core/conversions.py:1420](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/core/conversions.py#L1420)。

## 已保存的机制实验

已有 8 组 Kamino / CPU 机制对照，其中 6 组满足各自事前物理门槛；未通过的对照也保留原始数据和失败条件，不能作为已验证的调参建议。场景、指标与门槛先冻结，每个设置由两个独立进程重复。实测覆盖四杆闭环/FK、PADMM–DVI 配置组、力限及 default/preserve reset；它们是指定场景的行为证据，不等于所有相关参数都完成了单因素扫描。详见 [机制实验与验收](experiments.md) 和 [原始数据与复现](../../experiments/kamino_mechanism_lab/README.md)。

求解器的 `converged`、速度层残差、位置几何误差及重复性分开报告。残差定义随后端变化，触及迭代上限也不能被隐藏为成功收敛；同样，速度层收敛不能证明有限时间步下关节位置约束准确。

**驱动场景的诊断限制：** 有界隐式 PD 的收敛标记比例为 0%，最大迭代数达到 200；末步互补残差 `r_c` 为 4.4e-07 J。在冻结的严格容差下，本组通过的是实际力矩和运动参考门槛，求解器收敛检查并未通过；没有放宽容差来改写该结果。

## 有界 PD 后续诊断与跟踪实测

新增 7 组配对案例、22 次唯一正式运行，7 组达到事前物理门槛。诊断配对复用同一严格基线，运行数不重复计数。实验分别检查观测一致性、配置停止条件、原始严格停止条件和实际运动误差。详见 [PD 收敛、非饱和跟踪与力限切换](pd-experiments.md)。原饱和驱动 0% 收敛记录保持不变；后续实验不能将旧结果追认成收敛。


## 固定来源

- [newton/_src/solvers/kamino/solver_kamino.py:111](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L111)
- [docs/solvers/kamino.rst:5](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/kamino.rst#L5)
- [newton/_src/solvers/kamino/solver_kamino.py:1062](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L1062)
