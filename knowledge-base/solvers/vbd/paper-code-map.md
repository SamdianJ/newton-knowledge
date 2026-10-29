# 论文—机制—源码—参数—实验映射

图边表示有范围的对应关系；`source_extension` 不表示论文原样实现。实验只支持其记录的窄条件。

## 惯性目标与隐式积分（map:variational）

论文定位：paper:vbd2024；PDF p.3 Eqs.(2)–(4); p.4 Eq.(6)。

源码：[`SolverVBD._initialize_particles`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L3187-L3224)；[`solve_elasticity`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/particle_vbd_kernels.py#L2720-L2857)；[`SolverVBD._finalize_particles`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L4625-L4636)。

参数：`iterations`。

对应性质：implementation_of_core_idea; full nonlinear convergence not proven by probe。

既有窄探针：[exp:implicit_spring](#/record/exp%3Aimplicit_spring)；只支持该探针记录的输入与结论。

## 局部 3×3 系统与着色（map:block）

论文定位：paper:vbd2024；PDF p.4 Eqs.(7)–(9); Sec.3.9。

源码：[`SolverVBD._solve_particle_iteration`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L3747-L3982)；[`solve_elasticity`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/particle_vbd_kernels.py#L2720-L2857)；[`make_solve_elasticity_tile`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/particle_vbd_kernels.py#L2499-L2716)。

参数：`iterations`, `particle_enable_tile_solve`。

对应性质：scalar and tile kernels are distinct implementations。

既有窄探针：[exp:implicit_spring](#/record/exp%3Aimplicit_spring)；只支持该探针记录的输入与结论。

## 膜、弯曲与体积弹性（map:elastic）

论文定位：paper:vbd2024；Sec.3 material-energy framework。

源码：[`evaluate_neo_hookean_membrane_force_hessian`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/particle_vbd_kernels.py#L533-L662)；[`evaluate_dihedral_angle_based_bending_force_hessian`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/particle_vbd_kernels.py#L695-L846)；[`evaluate_volumetric_neo_hookean_force_and_hessian`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/particle_vbd_kernels.py#L179-L322)。

参数：主要由 Model 材料字段配置。

对应性质：constitutive-model correspondence, not identical discretization of every paper experiment。

局部实测证据（不代表整张映射已验证）：

- [lab:membrane](#/record/lab%3Amembrane)：固定单三角形和载荷下，同时改变 tri_ke 与 tri_ka 的薄膜位移响应。 边界：联合干预不能分别识别两项贡献；没有验证 tet、厚度换算或网格收敛。
- [lab:bending](#/record/lab%3Abending)：两个三角形折页中，保持面内材料不变并改变 edge_ke 的弯曲响应。 边界：只支持该固定拓扑的方向性结果，不是连续弯曲模量或真实材料标定。

仍未覆盖：tet 体积材料、近不可压条件及其收敛。；客观阻尼在刚体旋转叠加下的响应、薄膜厚度换算与网格收敛。

## legacy AVBD primal / dual / penalty（map:legacy）

论文定位：paper:avbd2025；PDF p.3 Eqs.(8)–(12); p.6 Algorithm 1。

源码：[`solve_rigid_body`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L6219-L6493)；[`ldlt6_solve`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L326-L408)；[`update_duals_joint`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L6497-L7093)；[`_ramp_penalty_k`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L1151-L1158)。

参数：`rigid_avbd_beta`, `rigid_avbd_alpha`, `rigid_avbd_gamma`。

对应性质：legacy foundation; source default beta=0/gamma=.999 differ from paper experiment settings。

既有窄探针：[exp:default_modes](#/record/exp%3Adefault_modes)；只支持该探针记录的输入与结论。

## compliant ALM 工程扩展（map:compliant）

论文定位：当前源码扩展；source equations; no identical paper equation asserted。

源码：[`_compliant_alm_coefficients`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L117-L134)；[`_alm_relaxed_ascent`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L138-L149)；[`_material_force_terms`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L153-L163)；[`_compliant_contact_dual_step`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L1078-L1103)。

参数：`rigid_compliant_alm`, `rigid_joint_linear_ke`。

对应性质：source_extension; mode probe does not validate all ALM dynamics。

既有窄探针：[exp:default_modes](#/record/exp%3Adefault_modes)；只支持该探针记录的输入与结论。

## 平滑摩擦与接触投影（map:friction）

论文定位：paper:vbd2024；Sec.3.6。

源码：[`compute_friction`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/particle_vbd_kernels.py#L1348-L1378)；[`_compliant_contact_dual_step`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L1078-L1103)。

参数：`friction_epsilon`。

对应性质：particle regularization vs compliant rigid Coulomb projection must be distinguished。

局部实测证据（不代表整张映射已验证）：

- [lab:friction](#/record/lab%3Afriction)：相同初速度的单粒子平面滑动，改变接触 mu 后的位移。 边界：没有验证刚体 Coulomb 锥投影、抓持或密集堆叠。
- [lab:friction_epsilon](#/record/lab%3Afriction_epsilon)：相同 mu、小恒力驱动单粒子时，friction_epsilon 改变低速蠕滑。 边界：仅支持粒子平滑摩擦；不验证刚体接触历史和跨设备结果。

仍未覆盖：compliant 刚体 Coulomb 投影、抓持/堆叠以及匹配历史摩擦。；不同步长、载荷与几何下的摩擦参数泛化。

## 平面划分与位移截断（map:dat）

论文定位：paper:dat2026；PDF p.4 Eqs.(11)–(16); Sec.3。

源码：[`create_vertex_triangle_division_plane_closest_pt`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/particle_vbd_kernels.py#L1971-L2006)；[`create_edge_edge_division_plane_closest_pt`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/particle_vbd_kernels.py#L2010-L2050)；[`apply_planar_truncation_parallel_by_collision`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/particle_vbd_kernels.py#L2054-L2188)；[`rigid_trajectory_truncation_t`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L7944-L8058)。

参数：`dat_conservative_bound_relaxation`, `rigid_soft_enable_dat`, `rigid_soft_dat_use_interval_arithmetic`。

对应性质：conditional geometry mechanism; dense collision runtime validation pending。

局部实测证据（不代表整张映射已验证）：

- [lab:dat](#/record/lab%3Adat)：零半径高速质点冲向薄板、弱 penalty 条件下，开启刚柔 DAT 后的位移截断。 边界：不是任意无穿透证明；没有验证自接触平面分配、tet 翻转或旋转刚体轨迹。
- [lab:dat_relaxation](#/record/lab%3Adat_relaxation)：同一简单刚柔 DAT 场景中，保守系数改变接近接触面的过程。 边界：没有验证密集候选、容量溢出、刚体 interval arithmetic 或所有调度组合。

仍未覆盖：VT/EE 分隔平面机制的逐项验证与密集/初始相交场景。；旋转刚体、interval arithmetic、复杂非凸候选覆盖和 tet 反转。

## 候选检测范围与兼容层（map:detect）

论文定位：paper:dat2026；neighborhood coverage assumption; no constructor naming in paper。

源码：[`SolverVBD.__init__`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L353-L1000)；[`SolverVBD._collision_detection_penetration_free`](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L4831-L4851)。

参数：`particle_self_contact_margin`, `particle_self_contact_gap`, `particle_vertex_contact_buffer_size`, `particle_edge_contact_buffer_size`。

对应性质：engineering API semantics; paper has no Newton parameter defaults。

既有窄探针：[exp:margin_compatibility](#/record/exp%3Amargin_compatibility)；只支持该探针记录的输入与结论。

## 证据层级与剩余实验

`exp:*` 是早期构造语义/CPU 窄探针，`lab:*` 是保存 A/B 轨迹的参数实验。两者保留各自的场景与边界；关联局部实验不将整个映射标为 experiment_validated。

当前参数实验为17组CPU A/B，直接干预9/47个可选构造项，没有全参数扫描或独立重复统计。tet、rod、历史状态、耦合与GPU等下一批实验见[版本差异与缺口](version-notes.md)。
