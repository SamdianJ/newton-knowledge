# Kamino · 版本与边界

Newton 1.7.0，commit `7e75abe28b8d69522bc0b34837aaed2c303dff5a`。

## 正式版本中的实验性组件

Newton 1.7.0 的 Kamino 文档仍标为 BETA 1 / experimental，不能用当前日期推断它已经变为稳定版本。其 API、行为和支持范围按固定快照解释。

## 配置组合限制

`sparse_dynamics=True` 要求 sparse_jacobian=True；DVI 要求 dynamics.preconditioning=False；PADMM 的自适应罚参数更新要求 sparse_dynamics=True；Moreau 要求内部碰撞检测。这些是组合约束，不是独立调参旋钮。

## 状态与执行边界

Kamino 面向 constrained rigid systems。FK 对每关节 passive/actuated 的划分与动力学逐 DoF 驱动并非同一能力边界。body_qdd 是离散步平均加速度，冲击时可表现为冲量/dt，不是连续中点加速度。

## 实验状态

静态入库阶段的参数说明来自源码与论文，诊断记录仍为 proposed。P4 已完成两组 PADMM / CPU 参数 A/B，并关闭 graph conditionals，见 [实验协议与复现](../../experiments/solver_parameter_lab/README.md)。不据此声称其他 CPU/GPU 组合已验证。


## 审核后覆盖与实验缺口

本节解释四组 PADMM 机制映射、DVI 当前实现边界、驱动/FK/reset/通知/材质概念。KAM-03 的后续实测按生成的机制实验页逐场景登记，物理通过和未通过均保留；字段/默认的静态覆盖不能当作实验证据。PADMM eta/rho/三类容差全面扫描、稠密/稀疏与预条件消融、复杂闭环多接触、驱动/FK 混合边界、数值通知与结构重建、材料分组分裂、masked/flags/callback 部分 reset 仍需后续验证。DVI 对照必须记录整组默认变化，不能冒充单参数干预；已有局部证据不能外推 Moreau、多 world、GPU、长期稳定性或论文基准。diagnostics 中 proposed/not_run 仍是诊断计划的状态，不等于没有其他已归档实验。

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
