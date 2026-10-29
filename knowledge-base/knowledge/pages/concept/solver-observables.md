# 求解器观测资源

可选观测独立于 State 和 Contacts。

## 机制与数据流

solver.observables(kinds,contacts=...) 分配请求的数组；CONTACT_F 需要先解析容量并绑定同一 Contacts。未请求字段为 None，请求但容量零的字段为空数组。分配后容量在该 Model 生命周期内冻结；删除 Observables 不解除冻结，修改容量必须新建 Model 和相应运行资源。

## 诊断与边界

container 属于创建它的 solver/model；step 与消费者必须使用相同 contact storage。原生碰撞需 solver 先建立导出容量；MuJoCo CPU 仅支持 QFRC_ACTUATOR。

先确认 `solver.supported_observables`。接触索引量要求容量已解析、`contacts=contacts` 与后续 step/consumer 使用同一实例；分配之后容量在 Model 生命周期内冻结。修改冻结容量必须重新 finalize 得到新 Model，再创建 solver、pipeline、Contacts 和 Observables；仅删除/重建 Observables 不会解冻。同容量替换 storage 需重新绑定相应 Observables。组合传感器的 `solver_observable_kinds` 后一次分配，graph capture 前完成分配。

外部碰撞：pipeline → solver/contacts → observables → 每步 collide → step → sensor.update。
原生 MuJoCo：solver → 使用 get_max_contact_count 配置 pipeline → contacts → observables → step 导出几何和力；不调用 pipeline.collide。
Solver 自持碰撞：绑定 solver.contacts；step(..., contacts=None) 使用内部存储。

`CONTACT_F` 在 MuJoCo Warp、XPBD、VBD、Kamino 可用；native MuJoCo CPU (`use_mujoco_cpu=True`) 仅支持 `QFRC_ACTUATOR`，因此不能走本接触力配方。MuJoCo Warp 可在 CPU 或 GPU 运行，依赖与硬件条件另行核对。
SensorContact 用 `update(state_in, contacts, observables=observables)` 消费接触；Kamino 的接触点在输入 body frame，原位步进也需保留输入位姿。IMU 等状态型传感器按其 API 消费 `state_out`，不要统一套用输出 state。

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

## 精确 API 入口

- [newton.solvers.SolverBase.observables](#/record/symbol%3Anewton.solvers.SolverBase.observables)
- [newton.sensors.SensorContact.update](#/record/symbol%3Anewton.sensors.SensorContact.update)

## 相关知识

- [module:sensors](#/record/module%3Asensors)
- [recipe:mujoco-native-contact](#/record/recipe%3Amujoco-native-contact)
- [recipe:ik-mujoco-contact](#/record/recipe%3Aik-mujoco-contact)

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/concepts/solver_observables.html)。

## 固定版本原始出处

- [docs/concepts/solver_observables.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/solver_observables.rst#L1)
- [newton/_src/solvers/solver.py:721](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/solver.py#L721)
- [newton/_src/sensors/sensor_contact.py:618](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sensors/sensor_contact.py#L618)
