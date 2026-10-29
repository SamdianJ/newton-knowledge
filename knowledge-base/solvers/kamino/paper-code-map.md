# Kamino · 机制—论文—参数—源码对应

每组对应关系包含边界；包装层默认事实由源码提供。

## Config 构造时按 PADMM/DVI 和 sparsity 解析 Jacobian、预条件与线性求解器默认值。

类型：implementation_fact。

Config 构造时按 PADMM/DVI 和 sparsity 解析 Jacobian、预条件与线性求解器默认值。

参数：`config.dynamics_solver`、`config.sparse_jacobian`、`config.dynamics.preconditioning`、`config.dynamics.linear_solver_type`。论文定位：源码事实；所连论文只提供方法背景，不是此包装层行为的逐项出处。保留兼容 ID 的 implementation_fact。默认、分支和包装层行为由固定源码支持；不计作独立论文算法映射或已复现性能。

源码符号：

[newton/_src/solvers/kamino/solver_kamino.py:485](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L485)

## PADMM 的 rho_0/eta、三种残差容差与最大迭代共同控制数值求解。

类型：implementation_fact。

PADMM 的 rho_0/eta、三种残差容差与最大迭代共同控制数值求解。

参数：`config.padmm.rho_0`、`config.padmm.eta`、`config.padmm.max_iterations`、`config.padmm.primal_tolerance`、`config.padmm.dual_tolerance`、`config.padmm.compl_tolerance`。论文定位：源码事实；所连论文只提供方法背景，不是此包装层行为的逐项出处。保留兼容 ID 的 implementation_fact。默认、分支和包装层行为由固定源码支持；不计作独立论文算法映射或已复现性能。

源码符号：

[newton/_src/solvers/kamino/config.py:469](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L469)

## DVI 外层交替迭代与单边投影 sweeps 是两层预算，不等同于 PADMM iterations。

类型：implementation_fact。

DVI 外层交替迭代与单边投影 sweeps 是两层预算，不等同于 PADMM iterations。

参数：`config.dvi.max_alternating_iterations`、`config.dvi.inequality_sweeps_per_iteration`、`config.dvi.omega`。论文定位：源码事实；所连论文只提供方法背景，不是此包装层行为的逐项出处。保留兼容 ID 的 implementation_fact。默认、分支和包装层行为由固定源码支持；不计作独立论文算法映射或已复现性能。

源码符号：

[newton/_src/solvers/kamino/config.py:797](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L797)

## alpha/beta/gamma 分别控制双边关节、单边限位、单边接触稳定化。

类型：implementation_fact。

alpha/beta/gamma 分别控制双边关节、单边限位、单边接触稳定化。

参数：`config.constraints.alpha`、`config.constraints.beta`、`config.constraints.gamma`、`config.constraints.delta`。论文定位：源码事实；所连论文只提供方法背景，不是此包装层行为的逐项出处。保留兼容 ID 的 implementation_fact。默认、分支和包装层行为由固定源码支持；不计作独立论文算法映射或已复现性能。

源码符号：

[newton/_src/solvers/kamino/config.py:225](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L225)

## status 总是维护

类型：implementation_fact。

status 总是维护；collect_solver_info 控制额外统计而非 status 是否存在。

参数：`config.collect_solver_info`、`config.compute_solution_metrics`。论文定位：源码事实；所连论文只提供方法背景，不是此包装层行为的逐项出处。保留兼容 ID 的 implementation_fact。默认、分支和包装层行为由固定源码支持；不计作独立论文算法映射或已复现性能。

源码符号：

[docs/solvers/kamino.rst:125](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/kamino.rst#L125)

## DVI 预条件、PADMM 自适应罚参数与稀疏设置受显式校验约束。

类型：implementation_fact。

DVI 预条件、PADMM 自适应罚参数与稀疏设置受显式校验约束。

参数：`config.dynamics.preconditioning`、`config.padmm.penalty_update_method`、`config.sparse_dynamics`。论文定位：源码事实；所连论文只提供方法背景，不是此包装层行为的逐项出处。保留兼容 ID 的 implementation_fact。默认、分支和包装层行为由固定源码支持；不计作独立论文算法映射或已复现性能。

源码符号：

[newton/_src/solvers/kamino/solver_kamino.py:467](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L467)

## PADMM 变量分裂与 De Saxcé 修正

类型：mechanism_correspondence。

PADMM 中 x 是无约束冲量迭代，y 是投影后的可行冲量，z 是使二者一致的对偶变量，s 是 De Saxcé 速度修正；它们不是刚体位置。2024 的 f/y/z 分裂在 2025 报告中扩展为含双边关节、限位和接触的最大坐标系统。当前 _step 先调用 _update_desaxce_and_velocity_bias，以接触局部切向滑移估计法向修正并构造全体约束的线性右端；只有接触块需要该摩擦修正。

参数：`config.padmm.eta`、`config.padmm.rho_0`、`config.dynamics.preconditioning`。论文定位：[proximal-admm-2024 · PDF p.6 · III-B/C，式(32)–(36)](../../sources/papers/proximal-admm-2024/paper.pdf#page=6)；[kamino-loops-2025 · PDF p.23 · VI-F，式(165)–(166)；p.24 式(167a)](../../sources/papers/kamino-loops-2025/paper.pdf#page=23)。变量在当前求解器内可经对角预条件缩放，不能直接把 x/y 当成最终物理冲量。当前融合 kernel、可选加速和 GPU 批处理是实现细节，不是论文代码逐行复现；非接触双边约束不因此变成摩擦锥。

源码符号：[PADMMSolver._step](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/solver.py#L562)、[PADMMSolver._update_desaxce_and_velocity_bias](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/solver.py#L955)、[_compute_desaxce_correction](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/kernels.py#L395)

[newton/_src/solvers/kamino/_src/solvers/padmm/solver.py:562](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/solver.py#L562)
[newton/_src/solvers/kamino/_src/solvers/padmm/solver.py:955](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/solver.py#L955)
[newton/_src/solvers/kamino/_src/solvers/padmm/kernels.py:395](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/kernels.py#L395)

## 近端线性子问题与 Delassus 求解

类型：mechanism_correspondence。

近端项 eta 与增广罚参数 rho 共同正则化线性子问题。在未缩放记法下，(D+(eta+rho)I)x = -v_f-s+eta*x_prev+rho*y_prev+z_prev。当前 _compute_velocity_bias 的符号与该右端一致；_update_unconstrained_solution 调用 problem._delassus.solve，_update_regularization 管理对应正则项。线性求解器/稀疏选项属于 dynamics 配置，eta/rho 不是材料接触刚度。

参数：`config.padmm.eta`、`config.padmm.rho_0`、`config.dynamics.linear_solver_type`、`config.sparse_dynamics`。论文定位：[proximal-admm-2024 · PDF p.6 · III-C，式(36a)、(37)](../../sources/papers/proximal-admm-2024/paper.pdf#page=6)；[kamino-loops-2025 · PDF p.24 · VI-F，式(167b)、(168)](../../sources/papers/kamino-loops-2025/paper.pdf#page=24)。该式解释 PADMM 的基本非加速迭代；当前默认启用加速，实际迭代按加速分支阅读。预条件和自适应罚参数也需按当前分支读代码。2024 的 G+R 与 2025 的 D 记号不应直接当成同名数组；当前 Delassus 对象还包含关节、限位及驱动相关约束。未复现论文性能。

源码符号：[_compute_velocity_bias](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/kernels.py#L447)、[PADMMSolver._update_unconstrained_solution](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/solver.py#L995)、[PADMMSolver._update_regularization](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/solver.py#L527)

[newton/_src/solvers/kamino/_src/solvers/padmm/kernels.py:447](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/kernels.py#L447)
[newton/_src/solvers/kamino/_src/solvers/padmm/solver.py:995](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/solver.py#L995)
[newton/_src/solvers/kamino/_src/solvers/padmm/solver.py:527](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/solver.py#L527)

## 可行集合投影与对偶变量更新

类型：mechanism_correspondence。

基本迭代把 x-z_prev/rho 投影到可行集得到 y，再以 z=z_prev+rho*(y-x) 更新对偶变量。当前 _update_projection_argument 准备投影输入，_project_to_feasible_cone 分别处理有界乘子、非负限位和 Coulomb 接触锥；无界双边乘子不需要同样的锥截断。make_update_dual_variables_and_compute_primal_dual_residuals 实现 z 更新与残差。

参数：`config.padmm.rho_0`、`config.padmm.max_iterations`。论文定位：[proximal-admm-2024 · PDF p.6 · III-C，式(36b/c)、(38)–(39)](../../sources/papers/proximal-admm-2024/paper.pdf#page=6)；[kamino-loops-2025 · PDF p.24 · VI-F，式(167c/d)、(169)](../../sources/papers/kamino-loops-2025/paper.pdf#page=24)。论文式展示基本迭代；当前加速/松弛路径、批量约束布局和 effort-limited implicit PD 的有界乘子扩展必须从源码辨识。PADMM 的全局线性子问题加投影，不等同于 DVI 每次局部 PGS 扫描。

源码符号：[PADMMSolver._update_projection_argument](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/solver.py#L1009)、[_project_to_feasible_cone](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/kernels.py#L617)、[make_update_dual_variables_and_compute_primal_dual_residuals](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/kernels.py#L698)

[newton/_src/solvers/kamino/_src/solvers/padmm/solver.py:1009](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/solver.py#L1009)
[newton/_src/solvers/kamino/_src/solvers/padmm/kernels.py:617](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/kernels.py#L617)
[newton/_src/solvers/kamino/_src/solvers/padmm/kernels.py:698](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/kernels.py#L698)

局部实测：[lab:kamino_drive_effort_paths](#/record/lab%3Akamino_drive_effort_paths)。单 revolute 的正反饱和力矩与有界 implicit PD 输出，记录实际路由及报告 effort。边界：未隔离证明投影 kernel 或论文算法；未验证无饱和跟踪、其他关节及所有停止容差。

## 停止残差的物理单位与 DVI 实现边界

类型：mechanism_correspondence。

论文用原始共识、对偶变化和互补性残差检查迭代。当前 PADMM 报告 r_p=||P(x-y)||inf（冲量），r_d=||P^-1[eta*Δx+rho*Δy]||inf（速度），r_c 为不等式块冲量与速度内积绝对值最大值（能量）。_update_convergence_check 对照各自容差，status 给每 world 的终态。DVI 当前 solve/_solve_dense_inequality_pgs 则组合双边直接解与单边投影扫描，其 r_p 是物理冲量锥投影距离，r_d 是对偶锥距离/双边速度违反，r_c 是互补内积。

参数：`config.padmm.primal_tolerance`、`config.padmm.dual_tolerance`、`config.padmm.compl_tolerance`、`config.dvi.omega`。论文定位：[proximal-admm-2024 · PDF p.6 · III-D，式(40)–(43)](../../sources/papers/proximal-admm-2024/paper.pdf#page=6)；[kamino-loops-2025 · PDF p.24 · VI-F，式(170a–c)](../../sources/papers/kamino-loops-2025/paper.pdf#page=24)。三个残差都是物理量的绝对最大值，不除以约束数或参考范数，不能无量纲混合比较。PADMM 公式映射不证明 DVI 逐行复现上述论文；DVI 的定义依据当前 docs/solvers/kamino.rst 和源码。收敛标记与有限步轨迹精度/物理真实性不同，仍需实验。

源码符号：[PADMMSolver._update_convergence_check](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/solver.py#L1203)、[make_update_dual_variables_and_compute_primal_dual_residuals](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/kernels.py#L698)、[DVISolver.solve](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/dvi/solver.py#L450)、[DVISolver._solve_dense_inequality_pgs](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/dvi/solver.py#L698)、[Terminal residual definitions](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/kamino.rst#L111)

[newton/_src/solvers/kamino/_src/solvers/padmm/solver.py:1203](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/solver.py#L1203)
[newton/_src/solvers/kamino/_src/solvers/padmm/kernels.py:698](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/padmm/kernels.py#L698)
[newton/_src/solvers/kamino/_src/solvers/dvi/solver.py:450](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/dvi/solver.py#L450)
[newton/_src/solvers/kamino/_src/solvers/dvi/solver.py:698](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/solvers/dvi/solver.py#L698)
[docs/solvers/kamino.rst:111](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/kamino.rst#L111)

局部实测：[lab:kamino_backend_guided_contact](#/record/lab%3Akamino_backend_guided_contact)。同一倾斜导轨单接触场景的 PADMM/DVI 配置组、实际状态和各自残差时间序列。边界：同名残差和收敛率不能直接比较准确性；未覆盖稀疏动态、复杂接触、性能或论文基准。



## 固定来源

- [newton/_src/solvers/kamino/solver_kamino.py:111](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L111)
- [docs/solvers/kamino.rst:5](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/kamino.rst#L5)
- [newton/_src/solvers/kamino/solver_kamino.py:1062](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L1062)
