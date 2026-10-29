# Kamino · 论文与实现

Newton 1.7.0，commit `7e75abe28b8d69522bc0b34837aaed2c303dff5a`。

## 两篇直接引用的方法文献

- **Tsounis, Grandia, Bächer (2025)**：针对闭环机械系统、硬接触和限位，整理最大坐标对偶动力学与多类数值求解方法，并提供基准。重点阅读 V 节构建对偶问题、VI-F ADMM、VII–VIII 基准与实验；论文中的性能结论不能自动套到当前机器。
- **Carpentier, Le Lidec, Montaut (2024)**：结合近端方法与 ADMM 处理刚性/顺应接触，研究残差与罚参数调整。重点阅读 III-B 至 III-F；Kamino 源码在此基础上加入自身预条件、加速、warmstart 和后端约束。

## 从论文到本地重建

输入为刚体状态、质量/惯量、关节与接触约束；输出为约束冲量及推进状态。应同时量测闭环误差、穿透、摩擦行为和残差，再做速度/精度比较。本轮没有复现论文基准。建议读论文的求解算法和性能分布图，另绘制双边/单边约束进入对偶问题的解释图。

## 具体机制与论文对应

### PADMM 变量分裂与 De Saxcé 修正

[proximal-admm-2024 · PDF p.6 · III-B/C，式(32)–(36)](../../sources/papers/proximal-admm-2024/paper.pdf#page=6)；[kamino-loops-2025 · PDF p.23 · VI-F，式(165)–(166)；p.24 式(167a)](../../sources/papers/kamino-loops-2025/paper.pdf#page=23)

PADMM 中 x 是无约束冲量迭代，y 是投影后的可行冲量，z 是使二者一致的对偶变量，s 是 De Saxcé 速度修正；它们不是刚体位置。2024 的 f/y/z 分裂在 2025 报告中扩展为含双边关节、限位和接触的最大坐标系统。当前 _step 先调用 _update_desaxce_and_velocity_bias，以接触局部切向滑移估计法向修正并构造全体约束的线性右端；只有接触块需要该摩擦修正。

源码符号：[PADMMSolver._step](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/solver.py#L562)、[PADMMSolver._update_desaxce_and_velocity_bias](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/solver.py#L955)、[_compute_desaxce_correction](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/kernels.py#L395)。

适用边界：变量在当前求解器内可经对角预条件缩放，不能直接把 x/y 当成最终物理冲量。当前融合 kernel、可选加速和 GPU 批处理是实现细节，不是论文代码逐行复现；非接触双边约束不因此变成摩擦锥。

### 近端线性子问题与 Delassus 求解

[proximal-admm-2024 · PDF p.6 · III-C，式(36a)、(37)](../../sources/papers/proximal-admm-2024/paper.pdf#page=6)；[kamino-loops-2025 · PDF p.24 · VI-F，式(167b)、(168)](../../sources/papers/kamino-loops-2025/paper.pdf#page=24)

近端项 eta 与增广罚参数 rho 共同正则化线性子问题。在未缩放记法下，(D+(eta+rho)I)x = -v_f-s+eta*x_prev+rho*y_prev+z_prev。当前 _compute_velocity_bias 的符号与该右端一致；_update_unconstrained_solution 调用 problem._delassus.solve，_update_regularization 管理对应正则项。线性求解器/稀疏选项属于 dynamics 配置，eta/rho 不是材料接触刚度。

源码符号：[_compute_velocity_bias](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/kernels.py#L447)、[PADMMSolver._update_unconstrained_solution](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/solver.py#L995)、[PADMMSolver._update_regularization](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/solver.py#L527)。

适用边界：该式解释 PADMM 的基本非加速迭代；当前默认启用加速，实际迭代按加速分支阅读。预条件和自适应罚参数也需按当前分支读代码。2024 的 G+R 与 2025 的 D 记号不应直接当成同名数组；当前 Delassus 对象还包含关节、限位及驱动相关约束。未复现论文性能。

### 可行集合投影与对偶变量更新

[proximal-admm-2024 · PDF p.6 · III-C，式(36b/c)、(38)–(39)](../../sources/papers/proximal-admm-2024/paper.pdf#page=6)；[kamino-loops-2025 · PDF p.24 · VI-F，式(167c/d)、(169)](../../sources/papers/kamino-loops-2025/paper.pdf#page=24)

基本迭代把 x-z_prev/rho 投影到可行集得到 y，再以 z=z_prev+rho*(y-x) 更新对偶变量。当前 _update_projection_argument 准备投影输入，_project_to_feasible_cone 分别处理有界乘子、非负限位和 Coulomb 接触锥；无界双边乘子不需要同样的锥截断。make_update_dual_variables_and_compute_primal_dual_residuals 实现 z 更新与残差。

源码符号：[PADMMSolver._update_projection_argument](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/solver.py#L1009)、[_project_to_feasible_cone](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/kernels.py#L617)、[make_update_dual_variables_and_compute_primal_dual_residuals](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/kernels.py#L698)。

适用边界：论文式展示基本迭代；当前加速/松弛路径、批量约束布局和 effort-limited implicit PD 的有界乘子扩展必须从源码辨识。PADMM 的全局线性子问题加投影，不等同于 DVI 每次局部 PGS 扫描。

### 停止残差的物理单位与 DVI 实现边界

[proximal-admm-2024 · PDF p.6 · III-D，式(40)–(43)](../../sources/papers/proximal-admm-2024/paper.pdf#page=6)；[kamino-loops-2025 · PDF p.24 · VI-F，式(170a–c)](../../sources/papers/kamino-loops-2025/paper.pdf#page=24)

论文用原始共识、对偶变化和互补性残差检查迭代。当前 PADMM 报告 r_p=||P(x-y)||inf（冲量），r_d=||P^-1[eta*Δx+rho*Δy]||inf（速度），r_c 为不等式块冲量与速度内积绝对值最大值（能量）。_update_convergence_check 对照各自容差，status 给每 world 的终态。DVI 当前 solve/_solve_dense_inequality_pgs 则组合双边直接解与单边投影扫描，其 r_p 是物理冲量锥投影距离，r_d 是对偶锥距离/双边速度违反，r_c 是互补内积。

源码符号：[PADMMSolver._update_convergence_check](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/solver.py#L1203)、[make_update_dual_variables_and_compute_primal_dual_residuals](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/kernels.py#L698)、[DVISolver.solve](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/dvi/solver.py#L450)、[DVISolver._solve_dense_inequality_pgs](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/dvi/solver.py#L698)、[Terminal residual definitions](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/kamino.rst#L111)。

适用边界：三个残差都是物理量的绝对最大值，不除以约束数或参考范数，不能无量纲混合比较。PADMM 公式映射不证明 DVI 逐行复现上述论文；DVI 的定义依据当前 docs/solvers/kamino.rst 和源码。收敛标记与有限步轨迹精度/物理真实性不同，仍需实验。


## 审核后覆盖与实验缺口

本节解释四组 PADMM 机制映射、DVI 当前实现边界、驱动/FK/reset/通知/材质概念。KAM-03 的后续实测按生成的机制实验页逐场景登记，物理通过和未通过均保留；字段/默认的静态覆盖不能当作实验证据。PADMM eta/rho/三类容差全面扫描、稠密/稀疏与预条件消融、复杂闭环多接触、驱动/FK 混合边界、数值通知与结构重建、材料分组分裂、masked/flags/callback 部分 reset 仍需后续验证。DVI 对照必须记录整组默认变化，不能冒充单参数干预；已有局部证据不能外推 Moreau、多 world、GPU、长期稳定性或论文基准。diagnostics 中 proposed/not_run 仍是诊断计划的状态，不等于没有其他已归档实验。

## 本地原文

- [On Solving the Dynamics of Constrained Rigid Multi-Body Systems with Kinematic Loops](../../sources/papers/kamino-loops-2025/paper.pdf)，66 页；[作者/出版方入口](https://arxiv.org/pdf/2504.19771v1)。
- [From Compliant to Rigid Contact Simulation: a Unified and Efficient Approach](../../sources/papers/proximal-admm-2024/paper.pdf)，14 页；[作者/出版方入口](https://arxiv.org/pdf/2405.17020v1)。

## 固定来源

- [newton/_src/solvers/kamino/solver_kamino.py:111](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L111)
- [docs/solvers/kamino.rst:5](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/kamino.rst#L5)
- [newton/_src/solvers/kamino/solver_kamino.py:1062](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L1062)
