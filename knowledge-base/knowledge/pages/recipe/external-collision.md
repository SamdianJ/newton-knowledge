# 外部碰撞与步进

外部碰撞与接触力的调用顺序。

先确认 `solver.supported_observables`。接触索引量要求容量已解析、`contacts=contacts` 与后续 step/consumer 使用同一实例；分配之后容量在 Model 生命周期内冻结。修改冻结容量必须重新 finalize 得到新 Model，再创建 solver、pipeline、Contacts 和 Observables；仅删除/重建 Observables 不会解冻。同容量替换 storage 需重新绑定相应 Observables。组合传感器的 `solver_observable_kinds` 后一次分配，graph capture 前完成分配。

外部碰撞：pipeline → solver/contacts → observables → 每步 collide → step → sensor.update。
原生 MuJoCo：solver → 使用 get_max_contact_count 配置 pipeline → contacts → observables → step 导出几何和力；不调用 pipeline.collide。
Solver 自持碰撞：绑定 solver.contacts；step(..., contacts=None) 使用内部存储。

`CONTACT_F` 在 MuJoCo Warp、XPBD、VBD、Kamino 可用；native MuJoCo CPU (`use_mujoco_cpu=True`) 仅支持 `QFRC_ACTUATOR`，因此不能走本接触力配方。MuJoCo Warp 可在 CPU 或 GPU 运行，依赖与硬件条件另行核对。
SensorContact 用 `update(state_in, contacts, observables=observables)` 消费接触；Kamino 的接触点在输入 body frame，原位步进也需保留输入位姿。IMU 等状态型传感器按其 API 消费 `state_out`，不要统一套用输出 state。

```python
pipeline = newton.CollisionPipeline(model)
solver = newton.solvers.SolverXPBD(model)
contacts = pipeline.contacts()
observables = solver.observables(kinds={solver.ObservableKind.CONTACT_F}, contacts=contacts)
# 每个子步，state_in / state_out 已由 model.state() 分配
state_in.clear_forces()
pipeline.collide(state_in, contacts)
solver.step(state_in, state_out, control, contacts, dt, observables=observables)
# 有 SensorContact 时先用输入位姿消费接触，再交换 state
contact_sensor.update(state_in, contacts, observables=observables)
state_in, state_out = state_out, state_in
```
前提：contact_sensor 已针对同一 Model 构建；该片段是顺序配方，不是独立可运行资产脚本。示例 backend 是 XPBD，不暗示所有 solver 消费该接触格式。

## 调度的五个时段

| 时段 | 本配方的责任 |
|---|---|
| Setup | 根据上述 backend 条件完成 Model、State、Control、Contacts 和 Observables；先解析容量，绑定同一 storage；graph capture 前完成分配与所需 warmup。 |
| 每仿真子步 | 清理外力、施加持有或新控制输入；外部模式每子步 collide，自持/原生模式由 step 按其碰撞调度更新；step 产生新状态和本子步观测。 |
| 每控制帧 | 仅在控制周期更新 IK/controller/轨迹目标；周期内按应用约定持有目标，不把控制帧率误当仿真 dt。 |
| 每输出帧 | 按采样周期消费最新有效观测；接触传感器使用对应的输入位姿，其他传感器按 API 读取所需 State；记录准确仿真时间并渲染/导出。 |
| Reset / Model 更新 | 按掩码恢复公共状态/控制并调用受支持的 solver.reset；Model 更新用 notify_model_changed 的后端支持 flags。改变已被 Observables 冻结的容量必须新建 Model 及相应 solver/Contacts/Observables；其他拓扑、分配或指针变化按后端重建资源并重新捕获，不假定已有 graph 自动反映任意 Python 参数变动。 |

配方中的控制与输出调度由调用方明确；本库没有把所有时段强制合并到每个 step。

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

## 精确 API 入口

- [newton.solvers.SolverBase.observables](#/record/symbol%3Anewton.solvers.SolverBase.observables)
- [newton.sensors.SensorContact.update](#/record/symbol%3Anewton.sensors.SensorContact.update)

## 相关知识

- [concept:solver-observables](#/record/concept%3Asolver-observables)
- [module:sensors](#/record/module%3Asensors)

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/concepts/solver_observables.html)。

## 固定版本原始出处

- [docs/concepts/solver_observables.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/solver_observables.rst#L1)
- [newton/_src/solvers/solver.py:721](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/solver.py#L721)
- [newton/_src/sensors/sensor_contact.py:618](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sensors/sensor_contact.py#L618)
