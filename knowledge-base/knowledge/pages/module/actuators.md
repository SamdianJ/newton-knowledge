# 执行器与驱动

执行器 Delay → Drive → Clamping → scatter-add。

## 职责、输入与输出

执行器读取状态与目标，计算 DOF effort，并累加到控制输出。ModelBuilder.add_actuator 注册后在 finalize 时实例化；也可独立组合 DrivePD/DrivePID、Delay 和电机限幅。

## 失败模式与限制

调用方每步先清零 effort 输出；执行器的可微、graph capture 能力依赖具体 drive。首版一执行器一 DOF，无通用传动模型或完整电机动力学。

## 模块公开导出索引

- [Actuator](#/record/symbol%3Anewton.actuators.Actuator)
- [ActuatorParsed](#/record/symbol%3Anewton.actuators.ActuatorParsed)
- [ClampingBase](#/record/symbol%3Anewton.actuators.ClampingBase)
- [ClampingDCMotor](#/record/symbol%3Anewton.actuators.ClampingDCMotor)
- [ClampingMaxEffort](#/record/symbol%3Anewton.actuators.ClampingMaxEffort)
- [ClampingPositionBased](#/record/symbol%3Anewton.actuators.ClampingPositionBased)
- [ComponentKind](#/record/symbol%3Anewton.actuators.ComponentKind)
- [Delay](#/record/symbol%3Anewton.actuators.Delay)
- [DriveBase](#/record/symbol%3Anewton.actuators.DriveBase)
- [DriveNeuralGRU](#/record/symbol%3Anewton.actuators.DriveNeuralGRU)
- [DriveNeuralLSTM](#/record/symbol%3Anewton.actuators.DriveNeuralLSTM)
- [DriveNeuralMLP](#/record/symbol%3Anewton.actuators.DriveNeuralMLP)
- [DrivePD](#/record/symbol%3Anewton.actuators.DrivePD)
- [DrivePID](#/record/symbol%3Anewton.actuators.DrivePID)
- [JointSpaceResponse](#/record/symbol%3Anewton.actuators.JointSpaceResponse)
- [SchemaNames](#/record/symbol%3Anewton.actuators.SchemaNames)
- [parse_actuator_prim](#/record/symbol%3Anewton.actuators.parse_actuator_prim)
- [register_actuator_component](#/record/symbol%3Anewton.actuators.register_actuator_component)

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

## 精确 API 入口

- [newton.actuators.Actuator](#/record/symbol%3Anewton.actuators.Actuator)
- [newton.actuators.DrivePD](#/record/symbol%3Anewton.actuators.DrivePD)

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/concepts/actuators.html)。

## 固定版本原始出处

- [newton/actuators.py:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/actuators.py#L1)
- [docs/concepts/actuators.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/actuators.rst#L1)
- [docs/api/newton_actuators.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/api/newton_actuators.rst#L1)
- [newton/_src/actuators/actuator.py:166](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/actuators/actuator.py#L166)
- [newton/_src/actuators/drives/drive_pd.py:68](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/actuators/drives/drive_pd.py#L68)
