# MuJoCo · 论文与实现

Newton 1.7.0，commit `7e75abe28b8d69522bc0b34837aaed2c303dff5a`。

## 两篇方法背景

- **Todorov, Erez, Tassa (2012)**：解释面向控制的广义坐标引擎结构，包含模型编译、动力学与约束响应。对本任务的用途是定位模型层与求解层；其历史实现不是当前 Warp 后端的支持列表。
- **Todorov (2014)**：解释软化约束、凸接触响应与可解析逆动力学。对本任务的用途是理解接触软化与优化收敛的区别；本轮未复现论文性能结果。

## 阅读与复现边界

输入是多刚体模型、状态、驱动与接触；输出是约束反力与推进后的状态。论文实验用于论证其方法，Newton 1.7.0 的包装、材料转换和 CPU/GPU 路径需另查源码。图示建议：阅读论文的约束求解/管线图，并绘制 Model → MuJoCo spec → backend → State 的本地解释图。

## 具体机制与论文对应

### 模型编译层次与广义坐标前向动力学的职责划分

[mujoco-2012 · PDF p.6 · III-A，模型三级表示](../../sources/papers/mujoco-2012/paper.pdf#page=6)；[mujoco-2014 · PDF p.2 · II-A/B，式(1)–(3)](../../sources/papers/mujoco-2014/paper.pdf#page=2)

2012 论文把建模描述、运行时模型和编译后动力学结构分层；2014 式(3)把质量矩阵、外力、约束冲量连接到速度更新。Newton 的 SolverMuJoCo._convert_to_mjc 将 Model 映射到现代 MjSpec 并调用 spec.compile()；step 将控制/状态交给 mj_step 或 _mujoco_warp_step。质量矩阵、偏置力、约束动力学和积分由 MuJoCo / MuJoCo Warp 后端执行。

源码符号：[SolverMuJoCo._convert_to_mjc](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L6023)、[MjSpec.compile call site](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L7992)、[SolverMuJoCo.step](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4557)。

适用边界：2012 的 C++ 建模 API 不是当前 MjSpec 的逐行说明；Newton 包装层没有自行实现论文中的 CRB/RNE/质量矩阵分解。2014 模型的数学角色用于解释数据流，具体积分器和支持能力以锁定包装层及实际后端版本为准。

### 软约束正则化与包装层材料/限位参数转换

[mujoco-2014 · PDF p.2 · II-C，式(4)；p.3 式(5)–(7)](../../sources/papers/mujoco-2014/paper.pdf#page=2)；[mujoco-2014 · PDF p.4 · II-E，式(10)–(11)](../../sources/papers/mujoco-2014/paper.pdf#page=4)

软化的 Gauss 原理通过正则化允许有限约束偏差；接触目标中 R 与参考速度影响响应。Newton 的 _update_solref_from_invweight0 把关节限位 force-space ke/kd 按 dof_invweight0 与 solimp 的 dmax 换算为后端 solref；_convert_contacts_to_mjwarp 负责外部接触转换。正则化约束系统的组装和求解由后端完成。

源码符号：[SolverMuJoCo._update_solref_from_invweight0](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L9557)、[SolverMuJoCo._convert_contacts_to_mjwarp](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L5012)。

适用边界：论文 R、参考速度与现代 solref/solimp 只有机制层对应，不能把论文 R 直接当成 Newton ke。关节限位换算与逐接触 force-space 修正不同；后者只适用于 Warp + Newton contacts，native CPU 不消费外部 contacts。保留 raw authored solreflimit、隐式导入默认和 refsafety 的现代分支，均不是论文逐项指定。

### 接触空间、摩擦锥与正则化凸优化

[mujoco-2014 · PDF p.3 · II-D，式(8)–(9)](../../sources/papers/mujoco-2014/paper.pdf#page=3)；[mujoco-2014 · PDF p.4 · II-E，式(10)–(11)](../../sources/papers/mujoco-2014/paper.pdf#page=4)

式(8)用接触空间矩阵 A=J Mhat^-1 J^T 连接冲量与接触速度，式(9)规定摩擦可行域，式(11)在该域中最小化正则化二次目标。Newton 的 _convert_to_mjc 传递 cone、solver、iterations、tolerance 等选项；_mujoco_warp_step / step 调用实际后端求解。condim 决定切向、扭转和滚动分量，cone 决定后端采用的锥近似。

源码符号：[SolverMuJoCo._convert_to_mjc](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L6023)、[SolverMuJoCo._mujoco_warp_step](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4552)、[SolverMuJoCo.step](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4557)。

适用边界：Newton 没有在此包装类内实现式(11)的优化器。2014 论文的 GPGS 不等同于现代后端提供的 CG/Newton 等选项；不能由论文推定两后端能力、收敛速度或结果相同。论文 III 节的解析逆动力学也不是 SolverMuJoCo.step 的对外能力承诺。


## 审核后覆盖与实验缺口

本节补齐主要模型转换导航和三组具体论文机制映射；保留的旧包装层 mapping 标为 implementation_fact，不能按条数当作论文机制覆盖率。参数目录是字段/默认/分支静态解释，不等于所有参数已充分实验。现有归档只支持各 case 记录的场景与 interventions；backend × contact-source 组合、state-sync interval 与逐步 control 的隔离对照、ref/limit 转换、过滤回退、tendon/equality/kinematic、cone/solver/收敛容差跨场景仍需专项验证。此次修复未新增或重跑物理实验。

## 本地原文

- [MuJoCo: A physics engine for model-based control](../../sources/papers/mujoco-2012/paper.pdf)，8 页；[作者/出版方入口](https://roboti.us/lab/papers/TodorovIROS12.pdf)。
- [Convex and analytically-invertible dynamics with contacts and constraints: Theory and implementation in MuJoCo](../../sources/papers/mujoco-2014/paper.pdf)，8 页；[作者/出版方入口](https://roboti.us/lab/papers/TodorovICRA14.pdf)。

## 固定来源

- [newton/_src/solvers/mujoco/solver_mujoco.py:470](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L470)
- [docs/solvers/mujoco.rst:5](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/mujoco.rst#L5)
- [newton/_src/solvers/mujoco/solver_mujoco.py:4557](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4557)
