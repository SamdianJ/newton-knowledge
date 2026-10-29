# 传感器生命周期

量测在物理步后的显式消费。

## 机制与数据流

传感器在构建/初始化阶段声明所需资源；量测阶段调用 update。状态型、接触型、渲染型传感器的输入与刷新时机不同。

## 诊断与边界

SensorContact 消费 CONTACT_F 与绑定的 Contacts，不能只把几何接触数量当作接触力；原生 CPU 与 Warp 的支持不同。

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/concepts/sensors.html)。

## 固定版本原始出处

- [docs/concepts/sensors.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/sensors.rst#L1)
