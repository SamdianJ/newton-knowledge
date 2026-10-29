# MuJoCo · 重点模型输入

这些输入与 solver 构造参数分开记录；不是全量字段数据流分析。

## `body_mass`

刚体质量；先从参考尺度与密度确定，避免用质量补偿错误接触。 单位：kg。由实际 ModelBuilder / 导入模型决定，未声明跨场景通用默认值。

[newton/_src/sim/model.py:972](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L972)

## `body_inertia`

刚体惯量张量；影响转动与约束条件数。 单位：kg·m²。由实际 ModelBuilder / 导入模型决定，未声明跨场景通用默认值。

[newton/_src/sim/model.py:968](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L968)

## `joint_armature`

关节附加惯量；需区分转动与平移自由度。 单位：依自由度而定。由实际 ModelBuilder / 导入模型决定，未声明跨场景通用默认值。

[newton/_src/sim/model.py:1050](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L1050)

## `joint_target_ke`

关节 PD 比例增益；不同 solver 的执行/隐式路径需分别核对。 单位：依自由度而定。由实际 ModelBuilder / 导入模型决定，未声明跨场景通用默认值。

[newton/_src/sim/model.py:1054](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L1054)

## `joint_target_kd`

关节 PD 导数增益。 单位：依自由度而定。由实际 ModelBuilder / 导入模型决定，未声明跨场景通用默认值。

[newton/_src/sim/model.py:1056](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L1056)

## `joint_effort_limit`

执行器力/力矩上限；与驱动方式共同作用。 单位：N 或 N·m。由实际 ModelBuilder / 导入模型决定，未声明跨场景通用默认值。

[newton/_src/sim/model.py:1060](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L1060)

## `joint_limit_lower`

关节下限及参考坐标约定。 单位：m 或 rad。由实际 ModelBuilder / 导入模型决定，未声明跨场景通用默认值。

[newton/_src/sim/model.py:1070](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L1070)

## `joint_limit_upper`

关节上限及参考坐标约定。 单位：m 或 rad。由实际 ModelBuilder / 导入模型决定，未声明跨场景通用默认值。

[newton/_src/sim/model.py:1072](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L1072)

## `shape_material_mu`

形状表面摩擦；需同时检查材料混合和接触维度。 单位：无量纲。由实际 ModelBuilder / 导入模型决定，未声明跨场景通用默认值。

[newton/_src/sim/model.py:706](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L706)

## `joint_damping`

关节被动黏性阻尼，导出为 MuJoCo dof_damping；区别于 PD 目标速度误差项 joint_target_kd。 单位：N·s/m 或 N·m·s/rad。由实际 ModelBuilder / 导入模型决定，未声明跨场景通用默认值。

[newton/_src/sim/model.py:1058](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L1058)

## `shape_material_mu_torsional`

扭转摩擦系数，控制接触法线方向的摩擦力矩尺度；需 condim≥4 才启用。单位为长度，不与无量纲滑动摩擦系数混用。 单位：m。由实际 ModelBuilder / 导入模型决定，未声明跨场景通用默认值。

[newton/_src/sim/model.py:710](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L710)

## `shape_material_mu_rolling`

滚动摩擦系数，控制切向旋转的摩擦力矩尺度；需 condim=6 才启用。此次扭转实验不构成滚动摩擦验证。 单位：m。由实际 ModelBuilder / 导入模型决定，未声明跨场景通用默认值。

[newton/_src/sim/model.py:712](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L712)

## `shape_margin`

形状接触裕量；需核对 native 后端实际 geom_margin 与 CCD 标志，不能仅根据请求值推断激活距离。 单位：m。由实际 ModelBuilder / 导入模型决定，未声明跨场景通用默认值。

[newton/_src/sim/model.py:726](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L726)

## `shape_gap`

形状接触候选间隙；应区分候选生成与活动约束，语义以固定 MuJoCo 版本及实际 geom_gap 为准。 单位：m。由实际 ModelBuilder / 导入模型决定，未声明跨场景通用默认值。

[newton/_src/sim/model.py:718](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L718)

## `shape_material_ke`

接触刚度输入会转换为 MuJoCo solref；MuJoCo Warp 的 Newton-contacts force-space 路径有额外条件。native CPU 不消费外部 Newton contacts。 单位：按转换模式解释。由实际 ModelBuilder / 导入模型决定，未声明跨场景通用默认值。

[newton/_src/sim/model.py:698](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L698)

## `shape_material_kd`

接触阻尼输入，不能把 VBD penalty 单位/效果直接搬到 MuJoCo。 单位：按转换模式解释。由实际 ModelBuilder / 导入模型决定，未声明跨场景通用默认值。

[newton/_src/sim/model.py:700](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L700)

## `mujoco.solref`

接触参考响应参数；正值格式与直接负值格式含义不同。 单位：见字段定义。读取已注册 mujoco 自定义属性及实际模型值。

[newton/_src/solvers/mujoco/solver_mujoco.py:1449](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L1449)

## `mujoco.geom_solimp`

约束阻抗曲线；与 solref 共同定义接触软化。 单位：见字段定义。读取已注册 mujoco 自定义属性及实际模型值。

[newton/_src/solvers/mujoco/solver_mujoco.py:1425](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L1425)

## `mujoco.condim`

接触维度，决定是否含切向/扭转/滚动摩擦。 单位：见字段定义。读取已注册 mujoco 自定义属性及实际模型值。

[newton/_src/solvers/mujoco/solver_mujoco.py:1390](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L1390)

## `mujoco.solref_mode`

ke/kd 转换模式；逐接触 force-space 修正属于 MuJoCo Warp 的 Newton-contacts 路径。native CPU 不消费外部 contacts，原生检测也不采用该逐接触修正。 单位：见字段定义。读取已注册 mujoco 自定义属性及实际模型值。

[newton/_src/solvers/mujoco/solver_mujoco.py:1463](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L1463)


## 模型转换概念导航

| 概念 | Newton → MuJoCo 的主要语义与边界 |
|---|---|
| joint | FREE/BALL/REVOLUTE/PRISMATIC 分别映射 free/ball/hinge/slide；D6 按活动轴展开至最多 3 slide + 3 hinge；FIXED 合入层级或世界根 mocap。DISTANCE 被丢弃（保留自由体记账），ROD 不转发，不能据此宣称支持。 |
| geometry | sphere/capsule/cylinder/box/ellipsoid 直接转换；plane 必须挂 world 且碰撞为无限平面；heightfield 归一化并修正基准高度。mesh 的凸包由 MuJoCo compiler 处理；cone 是离散网格近似，改变尺寸需重建；Gaussian 不支持。SITE 是引用标记而非碰撞形状。非凸/SDF/hydroelastic 需 Newton 碰撞管线和 Warp 外部接触路径。 |
| equality / mimic | CONNECT、WELD、JOINT equality 经 builder.add_custom_values 的 mujoco:equality_constraint_* 命名空间提供，不能假设有通用 add_equality API；set_joint_mimic 生成含 offset/multiplier 的 JOINT equality，覆盖 revolute/prismatic/D6 标量轴。闭环 FIXED/REVOLUTE/BALL 转为相应等式；闭环的驱动、限位等不会新增广义坐标，部分其他 joint 类型警告跳过。 |
| tendon / general actuator | tendon 通过 mujoco 自定义命名空间与 MJCF/USD 导入；空间 tendon 的 site/geom/pulley 路径受支持性检查，不支持或退化路径警告跳过。general actuator 可表达增益/偏置/动态/传动及范围，不能由简单 joint target 参数概括。 |
| kinematic root | 只支持运动学根，子体可动态；非 fixed 根用普通关节与大 armature 处理，fixed 世界根和全锁 D6 用 mocap。输入 joint_q/qd 写回时保留，施加其上的 body wrench/joint force 忽略，接触仍存在。 |
| dof_ref | Newton 标量 joint_q、limit、position target 相对 authored pose；后端 qpos/range/位置控制加回 ref，qd 不变。native dof_springref / actuator_ctrlrange 保持绝对语义。改变 ref 后通知 JOINT_REFERENCE_POSE_PROPERTIES。 |
| limit gains / passive dynamics | force-space joint_limit_ke/joint_limit_kd 经 dof_invweight0*(1-dmax) 缩放后转换 solreflimit；raw authored 值与隐式 MJCF 默认分开。正值 solref 可被 refsafe 时间步保护钳制。joint_damping、frictionloss、armature 与 PD target gains 含义不同。tendon limit gains 有独立 mode 和 TENDON_PROPERTIES 通知，不等于被动 tendon_damping。 |
| collision filtering | 保留单一导入域的 contype/conaffinity 原生掩码时，掩码仍是权威；collision_mask_domain 是导入来源标签，本身不是过滤器。混合域/原生 Newton 形状/新增排除对时编译允许对。32 位表达能力有限，大图可能走近似回退；显式 pair 可绕过 mask，仍须核对其他过滤。不要假设任意 Newton 排除图都无损映射。 |

固定入口：[newton/_src/solvers/mujoco/solver_mujoco.py:6023](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L6023)；[newton/_src/solvers/mujoco/solver_mujoco.py:3394](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L3394)；[newton/_src/solvers/mujoco/solver_mujoco.py:3713](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L3713)；[newton/_src/solvers/mujoco/solver_mujoco.py:3180](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L3180)；[newton/_src/solvers/mujoco/solver_mujoco.py:9557](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L9557)。

完整转换规则按固定版本官方文档继续索引：[docs/solvers/mujoco.rst:36](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/mujoco.rst#L36)。


## 固定来源

- [newton/_src/solvers/mujoco/solver_mujoco.py:470](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L470)
- [docs/solvers/mujoco.rst:5](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/mujoco.rst#L5)
- [newton/_src/solvers/mujoco/solver_mujoco.py:4557](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4557)
