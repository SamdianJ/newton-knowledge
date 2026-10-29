# 模型输入：constructor 之外的物理知识

本表是重点字段解释，不声称覆盖 Model 全部输入。完整直接引用字段清单见 [model_field_uses.json](../../indexes/model_field_uses.json)，其范围是 VBD 模块里的 model.field 语法，不解析别名或跨函数数据流。

| 字段 | 单位/约定 | 作用与证据 |
|---|---|---|
| `particle_mass` | kg | 质量；零质量粒子为运动学粒子。与 dt 共同决定惯性块，不可用错误质量补偿尺度错误。 [Model 定义](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L640) · [消费者](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/particle_vbd_kernels.py#L2720-L2857) |
| `particle_radius` | m | 刚柔碰撞粒子几何半径；不同于软体自接触 margin，也参与刚柔 DAT 查询半径下界。 [Model 定义](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L644) · [消费者](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L2837-L2896) |
| `tri_materials` | 官方 Model 标注 [Pa, Pa, Pa·s, Pa·s, Pa]；薄膜有效量纲/厚度换算待核验 | 前三项为膜弹性与阻尼；内核乘静止面积，不能仅按 Pa 标签把真实三维杨氏模量直接填入；需明确厚度与离散能量约定。后两项存在不等于 VBD 全部使用。 [Model 定义](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L909) · [消费者](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/particle_vbd_kernels.py#L533-L662) |
| `edge_bending_properties` | 官方 Model 标注 [N·m/rad, N·s]；有效刚度与静止边长约定待核验 | 二面角弯曲参数；内核还乘静止边长，不能直接替代连续材料弯曲模量。官方单位标签和离散系数换算需单独校验。 [Model 定义](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L926) · [消费者](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/particle_vbd_kernels.py#L695-L846) |
| `tet_materials` | [mu Pa, lambda Pa, damping Pa·s] | 体积弹性参数与客观阻尼，内核内部乘静止体积。 [Model 定义](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L943) · [消费者](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/particle_vbd_kernels.py#L179-L322) |
| `particle_q` | m | 模型初始/静止构形；参与自接触静止过滤，不能与可变 State.particle_q 混淆。 [Model 定义](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L636) · [消费者](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L1002-L1105) |
| `soft_contact_ke` | N/m（具体势函数须核查） | 软接触刚度；二次与 barrier 路径需按实际力函数解释。 [Model 定义](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L1197) · [消费者](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/particle_vbd_kernels.py#L850-L879) |
| `soft_contact_kd` | N·s/m | 软接触阻尼；不是全局刚体阻尼。 [Model 定义](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L1199) · [消费者](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/particle_vbd_kernels.py#L883-L897) |
| `soft_contact_mu` | 无量纲 | 软接触材料摩擦系数；不同于 friction_epsilon。 [Model 定义](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L1203) · [消费者](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/particle_vbd_kernels.py#L1348-L1378) |
| `shape_material_ke` | N/m | 每形状接触刚度；最终有效接触材料由接触初始化/混合规则决定。 [Model 定义](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L698) · [消费者](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L4750-L4853) |
| `shape_material_kd` | N·s/m | 每形状接触阻尼；记录两侧材料与混合后的接触记录。 [Model 定义](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L700) · [消费者](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L4750-L4853) |
| `shape_material_mu` | 无量纲 | 每形状摩擦系数；不能把单一形状值当作每个接触的最终 mu。 [Model 定义](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L706) · [消费者](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L4750-L4853) |
| `body_mass` | kg | 刚体质量，连同转动惯量、质心决定局部 6×6 系统。 [Model 定义](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L972) · [消费者](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L6219-L6493) |
| `body_inertia` | kg·m² | 刚体惯量，需与几何、质心、质量一致；不是任意的稳定性旋钮。 [Model 定义](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L968) · [消费者](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L6219-L6493) |
| `joint_target_ke` | 平移 N/m / 转动 N·m/rad | REVOLUTE/PRISMATIC/D6 drive 与 ROD 材料；与非 ROD structural ke 分层。ROD 材料更新用 JOINT_DOF_PROPERTIES 或 JOINT_DOF_FORCE_PROPERTIES，不负责静止构形缓存。 [Model 定义](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L1054) · [消费者](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L2894-L3757) |
| `joint_target_kd` | 平移 N·s/m / 转动 N·m·s/rad | 绝对物理阻尼；ROD 材料更新用 JOINT_DOF_PROPERTIES 或 JOINT_DOF_FORCE_PROPERTIES。ROD rest frame/rest pose 缓存另需 JOINT_PROPERTIES/BODY_PROPERTIES。 [Model 定义](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L1056) · [消费者](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L2894-L3757) |
| `joint_limit_ke` | 依线性/角度 DOF | 支持的关节限位行材料，不等同结构连接刚度。 [Model 定义](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L1074) · [消费者](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/rigid_vbd_kernels.py#L2894-L3757) |
| `joint_enabled` | 布尔 | 使能标志读 live；JOINT_PROPERTIES 通知还会刷新派生接触 conditioning。 [Model 定义](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L1068) · [消费者](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L167-L4866) |
| `spring_stiffness` | N/m | 粒子弹簧刚度，本样板一维 CPU 探针使用的能量项。 [Model 定义](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L879) · [消费者](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/particle_vbd_kernels.py#L1706-L1744) |
| `spring_damping` | N·s/m | 粒子弹簧阻尼，探针取 0 以便与解析隐式步比较。 [Model 定义](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L881) · [消费者](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/particle_vbd_kernels.py#L1706-L1744) |

## 连续材料到离散输入

三维各向同性材料常用 E、nu 转换为 Lamé 系数：mu=E/[2(1+nu)]、lambda=E*nu/[(1+nu)(1-2nu)]。这只适用于相应三维本构约定，不能把这对数值直接复制为薄膜或 rod 的离散系数。厚度、截面积、静止网格、归一化和平面应力/应变约定必须明确。

特别保留两个单位核查点：Model 对 tri_materials 标 Pa/Pa·s，但膜 kernel 按静止面积缩放；edge stiffness 文档标 N·m/rad，弯曲 kernel 还乘静止边长。这里保存官方标签，不自行宣告等价的物理标定单位。用确定几何的拉伸/弯曲静态实验核对有效系数，再把适配公式入库。

## 数据层级

- `Model`：几何、质量、材料与静止数据。
- `State`：位置、速度等时变数据。
- `Control`：关节/执行器命令；VBD 支持的字段须从能力清单筛选。
- `CollisionPipeline / Contacts`：候选、接触几何、容量、matching；不全部由 SolverVBD 参数决定。
- 调用层：dt、子步数、控制更新率、碰撞频率、目标评价。

旧工程中与这些层级混合保存的调参记录，需要先拆分，再判定哪些能迁移到 1.7.0。
