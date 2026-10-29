# IMU 与接触观测的时刻和参考系

## 机制与输入输出

SensorIMU 请求 BODY_QDD，SensorContact 请求 CONTACT_F，可合并请求 kinds，但两种传感器的输入时刻与物理定义不同。

## 配置与诊断步骤

1. 固定版本中 Kamino BODY_QDD 是 (body_qd_out-body_qd_in)/dt 的步平均，包括碰撞冲量除以 dt；MuJoCo Warp 使用对应后约束动力学阶段，不能把冲击下两者当同一瞬时采样。
2. SensorIMU.update(state, observables=...) 使用所需的当前位姿和加速度，核对 site 局部参考系、重力与刚体质心/量测点关系；不要只比较数组数字。
3. Kamino 导出的接触点在输入 body frame，wrench 关于输入 COM；SensorContact.update(state_in, contacts, observables=...) 消费相应接触。原位 step 也要保留输入位姿给需要变换的消费者。
4. native MuJoCo CPU 仅提供 QFRC_ACTUATOR，不支持这些 BODY_QDD/CONTACT_F 请求；MuJoCo Warp 的 cpu/cuda 设备与 native CPU 选项是不同维度。
5. 保存 dt、冲击发生的子步与输出采样时刻，才可分析读数差异。此处没有执行跨后端 IMU 实测。

## 适用范围与证据

Newton 1.7.0 固定文档、公开 API 与源码说明；runtime_status=not_run。这里的任务验证只验证知识检索与配置推理证据，不是物理任务执行或参数 A/B。设备、后端和捕获限制按所选路径核对。

## 精确 API

- [newton.sensors.SensorIMU.update](#/record/symbol%3Anewton.sensors.SensorIMU.update)
- [newton.sensors.SensorContact.update](#/record/symbol%3Anewton.sensors.SensorContact.update)

## 相关知识

- [module:sensors](#/record/module%3Asensors)
- [concept:solver-observables](#/record/concept%3Asolver-observables)
- [topic:lifecycle-observation](#/record/topic%3Alifecycle-observation)
- [solver:kamino](#/record/solver%3Akamino)
- [solver:mujoco](#/record/solver%3Amujoco)

## 固定出处

- [newton/_src/sensors/sensor_imu.py:208](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sensors/sensor_imu.py#L208)
- [newton/_src/sensors/sensor_contact.py:618](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sensors/sensor_contact.py#L618)
- [docs/concepts/solver_observables.rst:146](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/solver_observables.rst#L146)
