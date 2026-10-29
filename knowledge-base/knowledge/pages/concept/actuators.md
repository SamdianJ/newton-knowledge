# 执行器组合与控制

执行器模型与 solver 驱动的接口。

## 机制与数据流

Drive 计算 effort，Delay 模拟命令延迟，Clamping 表达电机输出限制，最后 scatter-add 到控制数组。control target、驱动刚度/阻尼和力限共同决定跟踪响应。

## 诊断与边界

控制器求目标、执行器算 effort、solver 施加动力学三层要分清。保留直接后端 drive 时，避免和外部 effort 双重驱动。

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/concepts/actuators.html)。

## 固定版本原始出处

- [docs/concepts/actuators.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/actuators.rst#L1)
