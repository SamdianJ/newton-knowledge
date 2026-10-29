# 观测 记录 导出与渲染

观测、回放与可复现结果导出。

输入：物理状态、Contacts、Observables 与仿真时间。输出：Sensor 量测、Viewer 显示、USD/图像/轨迹和指标。保存单位、采样频率、run ID、配置差异、依赖、设备与 raw hash；渲染帧率不能替代仿真步长。接触传感器按输入位姿消费，普通状态显示通常取推进后的 state。

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

## 相关知识

- [module:sensors](#/record/module%3Asensors)
- [module:viewer](#/record/module%3Aviewer)
- [topic:lifecycle-observation](#/record/topic%3Alifecycle-observation)

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/guide/visualization.html)。

## 固定版本原始出处

- [docs/guide/visualization.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/guide/visualization.rst#L1)
- [docs/concepts/sensors.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/sensors.rst#L1)
