# Model 与运行时初始化

Model、运行状态与资源的分配顺序。

输入：已配置 builder 与选定 backend。先在 builder 阶段注册 custom attributes 与 solver 扩展字段，再 finalize 得到 Model。SensorIMU 等接受 Model 的传感器在此后创建；legacy State 字段请求须在 model.state() 前完成，solver Observables 在 solver 构造和接触容量解析后分配。输出为 Model、双缓冲 State、Control、Contacts、solver 与可选 Observables；graph capture 前预分配。原生碰撞与外部碰撞顺序不同，按配方选择。

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

## 相关知识

- [module:newton](#/record/module%3Anewton)
- [concept:custom-attributes](#/record/concept%3Acustom-attributes)
- [concept:solver-observables](#/record/concept%3Asolver-observables)
- [recipe:external-collision](#/record/recipe%3Aexternal-collision)
- [recipe:mujoco-native-contact](#/record/recipe%3Amujoco-native-contact)

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/guide/overview.html)。

## 固定版本原始出处

- [docs/guide/overview.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/guide/overview.rst#L1)
- [docs/concepts/solver_observables.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/solver_observables.rst#L1)
