# 核心对象与生命周期

ModelBuilder / Model / State / Control / Contacts 的生命周期。

## 职责、输入与输出

Builder 接收原语、URDF/MJCF/USD 与自定义属性；finalize 分配 Model。随后分配输入/输出 State、Control、Contacts 和可选 Observables，由所选 solver.step 推进。Model 主要保存拓扑、材料和参数，State 保存动态量；变更 Model 数组要核对 notify_model_changed 和缓存语义。

## 失败模式与限制

状态交换后继续使用新输入；清理每步外力。contact_f 不在 State 中，应通过 solver.observables 请求。

## 模块公开导出索引

- [MAXVAL](#/record/symbol%3Anewton.MAXVAL)
- [Axis](#/record/symbol%3Anewton.Axis)
- [AxisType](#/record/symbol%3Anewton.AxisType)
- [use_coord_layout_targets](#/record/symbol%3Anewton.use_coord_layout_targets)
- [SDF](#/record/symbol%3Anewton.SDF)
- [Gaussian](#/record/symbol%3Anewton.Gaussian)
- [GeoType](#/record/symbol%3Anewton.GeoType)
- [Heightfield](#/record/symbol%3Anewton.Heightfield)
- [Mesh](#/record/symbol%3Anewton.Mesh)
- [ParticleFlags](#/record/symbol%3Anewton.ParticleFlags)
- [ShapeFlags](#/record/symbol%3Anewton.ShapeFlags)
- [TetMesh](#/record/symbol%3Anewton.TetMesh)
- [intersect_ray](#/record/symbol%3Anewton.intersect_ray)
- [BodyFlags](#/record/symbol%3Anewton.BodyFlags)
- [CollisionPipeline](#/record/symbol%3Anewton.CollisionPipeline)
- [Contacts](#/record/symbol%3Anewton.Contacts)
- [Control](#/record/symbol%3Anewton.Control)
- [JointTargetMode](#/record/symbol%3Anewton.JointTargetMode)
- [JointType](#/record/symbol%3Anewton.JointType)
- [Model](#/record/symbol%3Anewton.Model)
- [ModelBuilder](#/record/symbol%3Anewton.ModelBuilder)
- [ModelFlags](#/record/symbol%3Anewton.ModelFlags)
- [Rod](#/record/symbol%3Anewton.Rod)
- [State](#/record/symbol%3Anewton.State)
- [StateFlags](#/record/symbol%3Anewton.StateFlags)
- [eval_fk](#/record/symbol%3Anewton.eval_fk)
- [eval_ik](#/record/symbol%3Anewton.eval_ik)
- [eval_inverse_dynamics_force](#/record/symbol%3Anewton.eval_inverse_dynamics_force)
- [eval_inverse_dynamics_passive](#/record/symbol%3Anewton.eval_inverse_dynamics_passive)
- [eval_jacobian](#/record/symbol%3Anewton.eval_jacobian)
- [eval_mass_matrix](#/record/symbol%3Anewton.eval_mass_matrix)
- [eval_mimic](#/record/symbol%3Anewton.eval_mimic)
- [eval_rigid_contact_kinematics](#/record/symbol%3Anewton.eval_rigid_contact_kinematics)
- [actuators](#/record/symbol%3Anewton.actuators)
- [controllers](#/record/symbol%3Anewton.controllers)
- [geometry](#/record/symbol%3Anewton.geometry)
- [ik](#/record/symbol%3Anewton.ik)
- [math](#/record/symbol%3Anewton.math)
- [selection](#/record/symbol%3Anewton.selection)
- [sensors](#/record/symbol%3Anewton.sensors)
- [solvers](#/record/symbol%3Anewton.solvers)
- [usd](#/record/symbol%3Anewton.usd)
- [utils](#/record/symbol%3Anewton.utils)
- [viewer](#/record/symbol%3Anewton.viewer)

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

## 精确 API 入口

- [newton.ModelBuilder](#/record/symbol%3Anewton.ModelBuilder)
- [newton.Model](#/record/symbol%3Anewton.Model)
- [newton.State](#/record/symbol%3Anewton.State)
- [newton.Control](#/record/symbol%3Anewton.Control)
- [newton.Contacts](#/record/symbol%3Anewton.Contacts)
- [newton.CollisionPipeline](#/record/symbol%3Anewton.CollisionPipeline)

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/guide/overview.html)。

## 固定版本原始出处

- [newton/__init__.py:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/__init__.py#L1)
- [docs/guide/overview.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/guide/overview.rst#L1)
- [docs/api/newton.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/api/newton.rst#L1)
- [newton/_src/sim/builder.py:536](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/builder.py#L536)
- [newton/_src/sim/model.py:134](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L134)
- [newton/_src/sim/state.py:50](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/state.py#L50)
- [newton/_src/sim/control.py:16](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/control.py#L16)
- [newton/_src/sim/contacts.py:118](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/contacts.py#L118)
- [newton/_src/sim/collide.py:1250](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/collide.py#L1250)
