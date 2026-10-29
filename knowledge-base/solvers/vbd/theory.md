# VBD 原理：从能量到每一步计算

适用版本：Newton 1.7.0。Newton 是引擎名称；VBD 局部更新使用 Newton 型线性化，并不是每步装配并求解整个场景的全局 Newton 系统。

## 1. 隐式 Euler 的变分形式

以无额外速度相关项的粒子系统说明。位置 x、速度 v、质量矩阵 M、时间步 h、外加加速度 a：

$$y=x^n+h v^n+h^2a,\qquad G(x)=\frac{1}{2h^2}(x-y)^T M(x-y)+E(x).$$

惯性项希望粒子靠近自由预测位置 y，材料与接触项 E 希望满足弹性/接触关系。求解这个平衡后，由位置差得到速度。对应 [Vertex Block Descent](https://graphics.cs.utah.edu/research/projects/vbd/vbd-siggraph2024.pdf) PDF p.3 Eqs.(2)–(4)、p.4 Eq.(6)，及 [`SolverVBD._initialize_particles`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L3187-L3224)、[`SolverVBD._finalize_particles`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L4625-L4636)。

这不是“忽略时间积分、直接把物体投影回去”。质量和步长进入局部系统，改变 h 会同时改变时间离散误差、惯性权重与数值耗散。材料阻尼、隐式积分耗散和有限迭代误差应分开识别。

## 2. 将大系统拆成顶点块

固定其他顶点，仅更新 i 的三个坐标：

$$f_i=-\nabla_iG,\quad H_i=\frac{m_i}{h^2}I+\sum_j\nabla_i^2E_j,\quad H_i\Delta x_i=f_i.$$

每次只处理与 i 相邻的力元。按拓扑着色安排同色块并行，不同颜色依次消费更新状态；动态接触另有积累/近似处理，不能把所有接触一概称为无耦合并行。对应论文 p.4 Eqs.(7)–(9)、Sec.3.9，以及 [`SolverVBD._solve_particle_iteration`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L3747-L3982)、[`solve_elasticity`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/particle_vbd_kernels.py#L2720-L2857)。

标量核用 3×3 逆，行列式绝对值不大于 `1e-8` 时跳过该更新。CUDA 还存在 tiled 特化路径。一次局部 Newton 更新不保证已求出局部最优，论文讨论的可选 line search 也不等于 Newton 当前所有路径都执行 line search。不能把“论文在极端测试中稳定”改写成任意初值/任意 dt 的正确性保证。

## 3. 刚体块、legacy AVBD 与 compliant ALM

刚体使用平移和转动的 6 自由度局部块；力、力矩、惯性、约束雅可比进入局部系统，[`solve_rigid_body`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L6219-L6493) 调用 [`ldlt6_solve`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L326-L408)。

legacy AVBD 引入拉格朗日乘子，双边硬约束的示意能量为 `0.5*k*C²+lambda*C`，随后更新 lambda 与 penalty。实际实现还含误差稳定化 `C-alpha*C0`、单边投影、罚参数上限与 warm start。论文依据是 [Augmented Vertex Block Descent](https://graphics.cs.utah.edu/research/projects/avbd/Augmented_VBD-SIGGRAPH25.pdf) PDF pp.3–6；对应 [`_update_joint_structural_dual`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L1425-L1464)。软行和硬行的 dual 规则不同。

Newton 1.7.0 推荐的 compliant ALM 是需要单独理解的实现扩展：

$$s=\frac{K}{K+\rho},\quad k_{eff}=\frac{K\rho}{K+\rho},\quad F_{row}=k_{eff}C+s\lambda.$$
$$\lambda^+=s\,[\lambda+\rho(C-\alpha C_0)].$$

K 是有限材料刚度，rho 是数值求解参数。K 不能简单被“无限增大 iterations/rho”替代；在平衡条件下 lambda 表达材料反力。内部 rho 按行类型与惯性支撑计算，例如双边行策略包含 `max(H,9K)`，并非用户 beta 的同义词。数值实现使用避免乘法溢出的等价形式。来源：[`_compliant_alm_coefficients`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L117-L134)、[`_alm_relaxed_ascent`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L138-L149)、[`_material_force_terms`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L153-L163)、[`_bilateral_auto_rho`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L178-L182)。

接触法向乘子投影为非负；切向 trial 乘子投影到由 `mu*lambda_n` 决定的 Coulomb 圆盘。切向不套用法向材料 s 缩放。见 [`_compliant_contact_dual_step`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L1078-L1103)。以上公式并非直接摘自 AVBD 2025 的同编号公式。

**1.7.0 必须显式选择模式：**省略 `rigid_compliant_alm` 仍为 legacy；`True` 才进入 compliant。alpha 默认分别为 0.95 与 0，gamma 默认 0.999。beta=0 是当前默认，不是论文所有示例的配置。

## 4. 材料与摩擦的实现差异

膜能量、二面角弯曲、tet 体积能量各自贡献局部 force/Hessian。VBD 是求解组织方式，不是唯一的材料模型。改变网格、静止面积/体积、厚度约定或材料律，都会改变同一数值参数对应的物理含义。

VBD 2024 Sec.3.3 的简化 Rayleigh 阻尼不能直接当作 1.7.0 膜/tet 阻尼实现：当前膜核以 `C=FᵀF` 的变化率构造客观阻尼，使纯刚体旋转不引入此应变阻尼；tet 核也采用该类结构。弯曲阻尼则依据二面角变化率。见 [`evaluate_neo_hookean_membrane_force_hessian`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/particle_vbd_kernels.py#L533-L662)、[`evaluate_volumetric_neo_hookean_force_and_hessian`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/particle_vbd_kernels.py#L179-L322)、[`evaluate_dihedral_angle_based_bending_force_hessian`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/particle_vbd_kernels.py#L695-L846)。

粒子摩擦使用滑移距离的平滑函数，`eps_u=friction_epsilon*h`。mu 决定摩擦强度，epsilon 决定小滑移的平滑区域；二者不可互换。见 [`compute_friction`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/particle_vbd_kernels.py#L1348-L1378)。

## 5. DAT 是几何位移限制层

优化器先提出位移，DAT 用接触候选定义安全区域，再截断位移，使几何更新留在区域内。Planar-DAT 根据双侧趋近位移分配分隔平面，避免对远离/切向运动做同等的各向同性限制；它不替代材料反力或摩擦模型。见 [Divide and Truncate: A Penetration and Inversion Free Framework for Coupled Multi-physics Systems](https://arxiv.org/pdf/2604.15513v1) PDF p.4 Eqs.(11)–(16)，以及 [`apply_planar_truncation_parallel_by_collision`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/particle_vbd_kernels.py#L2054-L2188)。

软自接触使用 vertex–triangle 与 edge–edge 候选，刚柔还需考虑刚体转动轨迹，相关实现为 [`rigid_trajectory_truncation_t`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L7944-L8058)。本版本刚柔 DAT 需 owned pipeline、禁止 external rigid，并要求有效查询半径；见 [`SolverVBD._init_rigid_penetration_free`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L2837-L2896)。

论文的几何性质有前提：初始合法构形、充分候选覆盖、有效距离/轨迹界和正确截断。有限 buffer、错误过滤、初始穿插都不能由一个布尔开关消除。本样板没有证明任意 tet 翻转都受保护，也没有运行密集接触验证。

```mermaid
flowchart LR
 A[状态、控制、模型] --> B[预测与检测]
 B --> C[局部力和 Hessian]
 C --> D[按颜色求解刚体或粒子块]
 D --> E[适用时 DAT 截断]
 E --> F[约束与历史更新]
 F --> C
 F --> G[速度与接触力输出]
```

图为机制关系示意，精确的刚体/粒子调用顺序以 [源码导读](implementation.md) 和 `step` 为准。
