# Kamino · 重点模型输入

这些输入与 solver 构造参数分开记录；不是全量字段数据流分析。

## `body_mass`

刚体质量；先从参考尺度与密度确定，避免用质量补偿错误接触。 单位：kg。由实际 ModelBuilder / 导入模型决定，未声明跨场景通用默认值。

[newton/_src/sim/model.py:972](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L972)

## `body_inertia`

刚体惯量张量；影响转动与约束条件数。 单位：kg·m²。由实际 ModelBuilder / 导入模型决定，未声明跨场景通用默认值。

[newton/_src/sim/model.py:968](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L968)

## `joint_armature`

关节附加惯量；需区分转动与平移自由度。 Kamino 关节动力学/implicit PD 当前限于 revolute、prismatic、gimbal；按 DoF 路由驱动，但 FK 仍按整 joint 分被动/驱动。保持约束分配时可通知数值变化；跨零改变动态分配、增删有界 PD 或改变驱动分区必须重建。 单位：依自由度而定。由实际 ModelBuilder / 导入模型决定，未声明跨场景通用默认值。

[newton/_src/sim/model.py:1050](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L1050)

## `joint_target_ke`

关节 PD 比例增益；不同 solver 的执行/隐式路径需分别核对。 Kamino 关节动力学/implicit PD 当前限于 revolute、prismatic、gimbal；按 DoF 路由驱动，但 FK 仍按整 joint 分被动/驱动。保持约束分配时可通知数值变化；跨零改变动态分配、增删有界 PD 或改变驱动分区必须重建。 单位：依自由度而定。由实际 ModelBuilder / 导入模型决定，未声明跨场景通用默认值。

[newton/_src/sim/model.py:1054](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L1054)

## `joint_target_kd`

关节 PD 导数增益。 Kamino 关节动力学/implicit PD 当前限于 revolute、prismatic、gimbal；按 DoF 路由驱动，但 FK 仍按整 joint 分被动/驱动。保持约束分配时可通知数值变化；跨零改变动态分配、增删有界 PD 或改变驱动分区必须重建。 单位：依自由度而定。由实际 ModelBuilder / 导入模型决定，未声明跨场景通用默认值。

[newton/_src/sim/model.py:1056](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L1056)

## `joint_effort_limit`

执行器力/力矩上限；与驱动方式共同作用。 Kamino 关节动力学/implicit PD 当前限于 revolute、prismatic、gimbal；按 DoF 路由驱动，但 FK 仍按整 joint 分被动/驱动。保持约束分配时可通知数值变化；跨零改变动态分配、增删有界 PD 或改变驱动分区必须重建。 单位：N 或 N·m。由实际 ModelBuilder / 导入模型决定，未声明跨场景通用默认值。

[newton/_src/sim/model.py:1060](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L1060)

## `joint_limit_lower`

关节下限及参考坐标约定。 已有有限限位可通知数值更新；改变有限/无限状态导致约束结构变化，必须重建。 单位：m 或 rad。由实际 ModelBuilder / 导入模型决定，未声明跨场景通用默认值。

[newton/_src/sim/model.py:1070](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L1070)

## `joint_limit_upper`

关节上限及参考坐标约定。 已有有限限位可通知数值更新；改变有限/无限状态导致约束结构变化，必须重建。 单位：m 或 rad。由实际 ModelBuilder / 导入模型决定，未声明跨场景通用默认值。

[newton/_src/sim/model.py:1072](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L1072)

## `shape_material_mu`

形状表面摩擦；需同时检查材料混合和接触维度。 内部碰撞器经 SHAPE_PROPERTIES 更新固定材质表；共享 material 的 shapes 若分歧为不同材质值，必须重建以拆分分组。外部 Newton contacts 直接读 shape 材质，不使用内部材质表。 单位：无量纲。由实际 ModelBuilder / 导入模型决定，未声明跨场景通用默认值。

[newton/_src/sim/model.py:706](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L706)

## `shape_material_restitution`

碰撞恢复系数；与 material manager 的混合模式共同决定成对材料响应。 内部碰撞器经 SHAPE_PROPERTIES 更新固定材质表；共享 material 的 shapes 若分歧为不同材质值，必须重建以拆分分组。外部 Newton contacts 直接读 shape 材质，不使用内部材质表。 单位：无量纲。由实际 ModelBuilder / 导入模型决定，未声明跨场景通用默认值。

[newton/_src/sim/model.py:708](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L708)


## 驱动、FK、reset 和运行期更新边界

动力学按 DoF 路由 explicit effort、无界 implicit PD、effort-limited implicit PD。速度模式必须有非零 kd，位置类模式至少有适用的非零 ke/kd；关节动力学与 implicit PD 当前只支持 revolute、prismatic、gimbal。Coulomb 摩擦覆盖非 free joint。FK 则按整个 joint 划分被动/驱动：同一 joint 可混合不同非被动 target mode，但不能混合被动和驱动 DoF；fk_actuation_flag 提供 joint 级显式覆盖。因此“逐 DoF 驱动支持”不代表 FK 支持逐 DoF 分区。

reset(state, world_mask, flags, config, success_mask) 原地更新所选 world；ResetConfig 分别选择 body/base pose 与 velocity 的来源，可使用 FK。默认恢复初始值，并清理内部缓存；从结果 body state 重建 joint_q/qd、清零关节约束力。被 flags 排除的状态会缓存并恢复，复杂部分重置优先明确 config；success_mask 区分未选择/失败（包括 FK 未收敛）与成功。外部 body-origin 与内部 CoM frame 的转换由包装层处理，不能只写 joint_q 就假定闭环状态已一致。

| 修改类型 | 当前允许方式与限制 |
|---|---|
| 数值属性 | 保持已分配结构时，质量/惯量、关节/形状变换、现有动态/驱动/限位数值可通过对应 ModelFlags 通知更新；包装层先验证结构不变，再更新转换缓存与内部求解器。 |
| 结构变化 | armature/damping/无界 PD 增益跨零导致动态约束分配变化、限位由有限变无限或反之、启停摩擦、增删有界 implicit PD、改变驱动分区、改变 immovability 等必须重建 SolverKamino。轴正交性与 gimbal 手性仍需有效，notify 不是任意拓扑修改接口。 |
| 内部碰撞材质表 | SHAPE_PROPERTIES 会更新内部材质；若原来共享一个 material 的 shapes 改成不同 friction/restitution，既有分组无法拆开，抛错并要求重建。 |
| 外部 Newton contacts | 直接读 shape 材质，不使用上述内部材质表；不能把内部表更新限制泛化为外部 contacts 的相同机制。 |
| 不支持的约束 | Kamino 不支持 equality/mimic/tendon；相关通知在多 solver 环境中被忽略，不表示已实现这些模型能力。 |

固定来源：[docs/solvers/kamino.rst:129](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/kamino.rst#L129)；[newton/_src/solvers/kamino/solver_kamino.py:899](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L899)；[newton/_src/solvers/kamino/solver_kamino.py:1198](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L1198)；[newton/_src/solvers/kamino/solver_kamino.py:1558](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L1558)；[newton/_src/solvers/kamino/_src/core/conversions.py:1420](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/_src/core/conversions.py#L1420)。


## 固定来源

- [newton/_src/solvers/kamino/solver_kamino.py:111](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L111)
- [docs/solvers/kamino.rst:5](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/kamino.rst#L5)
- [newton/_src/solvers/kamino/solver_kamino.py:1062](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L1062)
