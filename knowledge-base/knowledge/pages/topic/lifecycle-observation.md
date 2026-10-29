# 生命周期 复位与量测

State、Contacts、Observables 的初始化与复用。

先确认 `solver.supported_observables`。接触索引量要求容量已解析、`contacts=contacts` 与后续 step/consumer 使用同一实例；分配之后容量在 Model 生命周期内冻结。修改冻结容量必须重新 finalize 得到新 Model，再创建 solver、pipeline、Contacts 和 Observables；仅删除/重建 Observables 不会解冻。同容量替换 storage 需重新绑定相应 Observables。组合传感器的 `solver_observable_kinds` 后一次分配，graph capture 前完成分配。

外部碰撞：pipeline → solver/contacts → observables → 每步 collide → step → sensor.update。
原生 MuJoCo：solver → 使用 get_max_contact_count 配置 pipeline → contacts → observables → step 导出几何和力；不调用 pipeline.collide。
Solver 自持碰撞：绑定 solver.contacts；step(..., contacts=None) 使用内部存储。

`CONTACT_F` 在 MuJoCo Warp、XPBD、VBD、Kamino 可用；native MuJoCo CPU (`use_mujoco_cpu=True`) 仅支持 `QFRC_ACTUATOR`，因此不能走本接触力配方。MuJoCo Warp 可在 CPU 或 GPU 运行，依赖与硬件条件另行核对。
SensorContact 用 `update(state_in, contacts, observables=observables)` 消费接触；Kamino 的接触点在输入 body frame，原位步进也需保留输入位姿。IMU 等状态型传感器按其 API 消费 `state_out`，不要统一套用输出 state。

通过 ModelBuilder.add_world / replicate 构建同质批量，检查 Model.*_world 与 *_world_start。ArticulationView 按 articulation label/index 创建视图，先读取选中对象的真实布局，再用 set_attribute(name,target,values,mask=...) 局部写入。

ArticulationView 的 mask 是 `(view.world_count,)` 或 `(view.world_count, count_per_world)`；solver.reset 的 world_mask 是 `(model.world_count+1,)`，最后一项选择 global world -1。两种掩码不可直接复用；global 实体还可能位于数组前后两段。

先按 mask 恢复公共 State 与 Control 的物理初态，再按后端要求 `solver.reset(state, world_mask=mask, flags=...)` 同步私有历史和缓存。SolverBase 默认 reset 仅校验掩码，是 no-op；不能宣称任何 solver.reset 都自动恢复全部初态。MuJoCo / VBD / Kamino 的具体缓存、global 行为和 backend 条件需读取对应 override；状态双缓冲也需一致处理。模型属性改动另走 notify_model_changed。

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

## 精确 API 入口

- [newton.sensors.SensorContact.update](#/record/symbol%3Anewton.sensors.SensorContact.update)
- [newton.State.clear_forces](#/record/symbol%3Anewton.State.clear_forces)

## 相关知识

- [concept:solver-observables](#/record/concept%3Asolver-observables)
- [recipe:external-collision](#/record/recipe%3Aexternal-collision)
- [recipe:solver-owned-collision](#/record/recipe%3Asolver-owned-collision)
- [recipe:mujoco-native-contact](#/record/recipe%3Amujoco-native-contact)

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/concepts/solver_observables.html)。

## 固定版本原始出处

- [docs/concepts/solver_observables.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/solver_observables.rst#L1)
- [docs/concepts/sensors.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/sensors.rst#L1)
- [newton/_src/sensors/sensor_contact.py:618](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sensors/sensor_contact.py#L618)
- [newton/_src/sim/state.py:167](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/state.py#L167)
