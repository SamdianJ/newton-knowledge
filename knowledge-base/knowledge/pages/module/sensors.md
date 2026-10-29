# 传感器与量测

SensorContact / IMU / Camera 与量测依赖。

## 职责、输入与输出

传感器从 State、Sites、Contacts 和 solver Observables 产生量测。SensorContact 声明 CONTACT_F 需求；可与其他传感器所需 kinds 合并，一次分配并跨步复用。

## 失败模式与限制

先确认后端 supported_observables，再配置接触容量和同一 Contacts。接触几何通常按输入 state 消费；native MuJoCo CPU 不提供 CONTACT_F，MuJoCo Warp 路径才支持该观测。

## 模块公开导出索引

- [SensorCamera](#/record/symbol%3Anewton.sensors.SensorCamera)
- [SensorContact](#/record/symbol%3Anewton.sensors.SensorContact)
- [SensorFrameTransform](#/record/symbol%3Anewton.sensors.SensorFrameTransform)
- [SensorIMU](#/record/symbol%3Anewton.sensors.SensorIMU)
- [SensorTiledCamera](#/record/symbol%3Anewton.sensors.SensorTiledCamera)

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

## 精确 API 入口

- [newton.sensors.SensorContact](#/record/symbol%3Anewton.sensors.SensorContact)
- [newton.sensors.SensorContact.update](#/record/symbol%3Anewton.sensors.SensorContact.update)
- [newton.sensors.SensorIMU](#/record/symbol%3Anewton.sensors.SensorIMU)

## 相关知识

- [concept:solver-observables](#/record/concept%3Asolver-observables)
- [recipe:mujoco-native-contact](#/record/recipe%3Amujoco-native-contact)
- [recipe:ik-mujoco-contact](#/record/recipe%3Aik-mujoco-contact)

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/concepts/sensors.html)。

## 固定版本原始出处

- [newton/sensors.py:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/sensors.py#L1)
- [docs/concepts/sensors.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/sensors.rst#L1)
- [docs/api/newton_sensors.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/api/newton_sensors.rst#L1)
- [newton/_src/sensors/sensor_contact.py:257](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sensors/sensor_contact.py#L257)
- [newton/_src/sensors/sensor_contact.py:618](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sensors/sensor_contact.py#L618)
- [newton/_src/sensors/sensor_imu.py:74](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sensors/sensor_imu.py#L74)
