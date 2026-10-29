# MuJoCo · 原理与机制

Newton 1.7.0，commit `7e75abe28b8d69522bc0b34837aaed2c303dff5a`。

## 广义坐标与约束响应

Newton 的 SolverMuJoCo 把 Model 转为 MuJoCo 模型，计算广义坐标系统中的动力学，再将状态同步回来。机器人树结构主要在关节坐标中表达，额外闭环通过受支持的 equality 约束表达。

$$M(q)\dot v+c(q,v)=\tau+J(q)^T f$$

MuJoCo 的接触响应是带软约束的优化模型。`solver` 决定数值优化方法，`iterations/tolerance` 决定求解预算，`solref/solimp` 决定约束响应模型，`dt/integrator` 决定时间离散。增加迭代无法修复碰撞漏检、错误模型转换或错误材料参数。

## 接触、材料与后端

`use_mujoco_contacts` 只在 MuJoCo Warp 分支选择接触生成来源，不把约束响应换成 VBD。`use_mujoco_cpu=True` 选择 MuJoCo-C native CPU；它与运行在 CPU 设备上的 MuJoCo Warp 不同。

| 后端 | use_mujoco_contacts | v1.7.0 实际接触路径 |
|---|---|---|
| native CPU（use_mujoco_cpu=True） | True 或 False | 始终由原生 MuJoCo 检测并响应；传入的 Newton contacts 不被消费 |
| MuJoCo Warp（use_mujoco_cpu=False） | True | MuJoCo Warp 内建检测与响应 |
| MuJoCo Warp（use_mujoco_cpu=False） | False | 调用方先检测并传入 Newton contacts，包装层转换后交后端响应 |

这是固定 `SolverMuJoCo.step` 的分支行为：CPU 直接调用 mj_step，只有 Warp 分支调用 `_convert_contacts_to_mjwarp`。`shape_material_ke/kd` 经转换得到 MuJoCo 参数，其作用不应沿用 VBD 的直接 penalty 解释；逐接触 force-space 修正还需核对接触来源和转换模式。

## 对重建 agent 的意义

优先核对机器人关节、质量/惯量、几何导出、接触生成、参考坐标与控制同步；随后探索接触软化和时间步，最后调整优化预算。以几何穿透、滑移、关节误差和运行开销分别评价。

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



## 固定来源

- [newton/_src/solvers/mujoco/solver_mujoco.py:470](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L470)
- [docs/solvers/mujoco.rst:5](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/mujoco.rst#L5)
- [newton/_src/solvers/mujoco/solver_mujoco.py:4557](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4557)
