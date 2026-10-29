# MuJoCo · 机制—论文—参数—源码对应

每组对应关系包含边界；包装层默认事实由源码提供。

## 构造值优先于模型 mujoco 自定义属性，再到注册/后端默认

类型：implementation_fact。

构造值优先于模型 mujoco 自定义属性，再到注册/后端默认；None 不等于固定数值默认。

参数：`iterations`、`integrator`、`solver`。论文定位：源码事实；所连论文只提供方法背景，不是此包装层行为的逐项出处。保留兼容 ID 的 implementation_fact。默认、分支和包装层行为由固定源码支持；不计作独立论文算法映射或已复现性能。

源码符号：

[newton/_src/solvers/mujoco/solver_mujoco.py:1655](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L1655)

## separate_worlds=None 时，实际分支为 not use_mujoco_cpu and model.world_count > 1。

类型：implementation_fact。

separate_worlds=None 时，实际分支为 not use_mujoco_cpu and model.world_count > 1。

参数：`separate_worlds`、`use_mujoco_cpu`。论文定位：源码事实；所连论文只提供方法背景，不是此包装层行为的逐项出处。保留兼容 ID 的 implementation_fact。默认、分支和包装层行为由固定源码支持；不计作独立论文算法映射或已复现性能。

源码符号：

[newton/_src/solvers/mujoco/solver_mujoco.py:4418](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4418)

## Newton 注册的默认积分器是 implicitfast，不应套用原生 MuJoCo 默认 Euler。

类型：implementation_fact。

Newton 注册的默认积分器是 implicitfast，不应套用原生 MuJoCo 默认 Euler。

参数：`integrator`。论文定位：源码事实；所连论文只提供方法背景，不是此包装层行为的逐项出处。保留兼容 ID 的 implementation_fact。默认、分支和包装层行为由固定源码支持；不计作独立论文算法映射或已复现性能。

源码符号：

[newton/_src/solvers/mujoco/solver_mujoco.py:1844](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L1844)

## 外部 Newton contacts 只由 MuJoCo Warp 的 use_mujoco_contacts=False 分支转换并消费

类型：implementation_fact。

外部 Newton contacts 只由 MuJoCo Warp 的 use_mujoco_contacts=False 分支转换并消费；native CPU 不消费传入 contacts，仍使用原生检测。约束响应均由 MuJoCo 负责。

参数：`use_mujoco_contacts`、`use_mujoco_cpu`。论文定位：源码事实；所连论文只提供方法背景，不是此包装层行为的逐项出处。保留兼容 ID 的 implementation_fact。默认、分支和包装层行为由固定源码支持；不计作独立论文算法映射或已复现性能。

源码符号：

[newton/_src/solvers/mujoco/solver_mujoco.py:4583](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4583)

## nconmax/njmax 控制容量而非数值收敛预算，初始化不足可能告警扩容。

类型：implementation_fact。

nconmax/njmax 控制容量而非数值收敛预算，初始化不足可能告警扩容。

参数：`nconmax`、`njmax`、`iterations`。论文定位：源码事实；所连论文只提供方法背景，不是此包装层行为的逐项出处。保留兼容 ID 的 implementation_fact。默认、分支和包装层行为由固定源码支持；不计作独立论文算法映射或已复现性能。

源码符号：

[newton/_src/solvers/mujoco/solver_mujoco.py:4117](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4117)

## sleeping 的有效组合受后端、优化方法、积分器与接触来源限制。

类型：implementation_fact。

sleeping 的有效组合受后端、优化方法、积分器与接触来源限制。

参数：`enable_sleeping`、`use_mujoco_cpu`、`solver`、`integrator`。论文定位：源码事实；所连论文只提供方法背景，不是此包装层行为的逐项出处。保留兼容 ID 的 implementation_fact。默认、分支和包装层行为由固定源码支持；不计作独立论文算法映射或已复现性能。

源码符号：

[newton/_src/solvers/mujoco/solver_mujoco.py:6277](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L6277)

## 模型编译层次与广义坐标前向动力学的职责划分

类型：mechanism_correspondence。

2012 论文把建模描述、运行时模型和编译后动力学结构分层；2014 式(3)把质量矩阵、外力、约束冲量连接到速度更新。Newton 的 SolverMuJoCo._convert_to_mjc 将 Model 映射到现代 MjSpec 并调用 spec.compile()；step 将控制/状态交给 mj_step 或 _mujoco_warp_step。质量矩阵、偏置力、约束动力学和积分由 MuJoCo / MuJoCo Warp 后端执行。

参数：`use_mujoco_cpu`、`integrator`。论文定位：[mujoco-2012 · PDF p.6 · III-A，模型三级表示](../../sources/papers/mujoco-2012/paper.pdf#page=6)；[mujoco-2014 · PDF p.2 · II-A/B，式(1)–(3)](../../sources/papers/mujoco-2014/paper.pdf#page=2)。2012 的 C++ 建模 API 不是当前 MjSpec 的逐行说明；Newton 包装层没有自行实现论文中的 CRB/RNE/质量矩阵分解。2014 模型的数学角色用于解释数据流，具体积分器和支持能力以锁定包装层及实际后端版本为准。

源码符号：[SolverMuJoCo._convert_to_mjc](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L6023)、[MjSpec.compile call site](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L7992)、[SolverMuJoCo.step](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4557)

[newton/_src/solvers/mujoco/solver_mujoco.py:6023](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L6023)
[newton/_src/solvers/mujoco/solver_mujoco.py:7992](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L7992)
[newton/_src/solvers/mujoco/solver_mujoco.py:4557](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4557)

## 软约束正则化与包装层材料/限位参数转换

类型：mechanism_correspondence。

软化的 Gauss 原理通过正则化允许有限约束偏差；接触目标中 R 与参考速度影响响应。Newton 的 _update_solref_from_invweight0 把关节限位 force-space ke/kd 按 dof_invweight0 与 solimp 的 dmax 换算为后端 solref；_convert_contacts_to_mjwarp 负责外部接触转换。正则化约束系统的组装和求解由后端完成。

参数：`use_mujoco_contacts`、`use_mujoco_cpu`、`impratio`。论文定位：[mujoco-2014 · PDF p.2 · II-C，式(4)；p.3 式(5)–(7)](../../sources/papers/mujoco-2014/paper.pdf#page=2)；[mujoco-2014 · PDF p.4 · II-E，式(10)–(11)](../../sources/papers/mujoco-2014/paper.pdf#page=4)。论文 R、参考速度与现代 solref/solimp 只有机制层对应，不能把论文 R 直接当成 Newton ke。关节限位换算与逐接触 force-space 修正不同；后者只适用于 Warp + Newton contacts，native CPU 不消费外部 contacts。保留 raw authored solreflimit、隐式导入默认和 refsafety 的现代分支，均不是论文逐项指定。

源码符号：[SolverMuJoCo._update_solref_from_invweight0](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L9557)、[SolverMuJoCo._convert_contacts_to_mjwarp](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L5012)

[newton/_src/solvers/mujoco/solver_mujoco.py:9557](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L9557)
[newton/_src/solvers/mujoco/solver_mujoco.py:5012](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L5012)

## 接触空间、摩擦锥与正则化凸优化

类型：mechanism_correspondence。

式(8)用接触空间矩阵 A=J Mhat^-1 J^T 连接冲量与接触速度，式(9)规定摩擦可行域，式(11)在该域中最小化正则化二次目标。Newton 的 _convert_to_mjc 传递 cone、solver、iterations、tolerance 等选项；_mujoco_warp_step / step 调用实际后端求解。condim 决定切向、扭转和滚动分量，cone 决定后端采用的锥近似。

参数：`cone`、`solver`、`iterations`、`tolerance`。论文定位：[mujoco-2014 · PDF p.3 · II-D，式(8)–(9)](../../sources/papers/mujoco-2014/paper.pdf#page=3)；[mujoco-2014 · PDF p.4 · II-E，式(10)–(11)](../../sources/papers/mujoco-2014/paper.pdf#page=4)。Newton 没有在此包装类内实现式(11)的优化器。2014 论文的 GPGS 不等同于现代后端提供的 CG/Newton 等选项；不能由论文推定两后端能力、收敛速度或结果相同。论文 III 节的解析逆动力学也不是 SolverMuJoCo.step 的对外能力承诺。

源码符号：[SolverMuJoCo._convert_to_mjc](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L6023)、[SolverMuJoCo._mujoco_warp_step](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4552)、[SolverMuJoCo.step](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4557)

[newton/_src/solvers/mujoco/solver_mujoco.py:6023](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L6023)
[newton/_src/solvers/mujoco/solver_mujoco.py:4552](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4552)
[newton/_src/solvers/mujoco/solver_mujoco.py:4557](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4557)



## 固定来源

- [newton/_src/solvers/mujoco/solver_mujoco.py:470](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L470)
- [docs/solvers/mujoco.rst:5](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/mujoco.rst#L5)
- [newton/_src/solvers/mujoco/solver_mujoco.py:4557](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4557)
