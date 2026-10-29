# 碰撞检测与 Contacts

从当前位姿生成有效 Contacts。

输入：当前 State 的 body/particle 位姿、Model 几何/过滤与 pipeline 配置。输出：有固定容量与原始计数的接触存储；溢出时 raw count 可超过容量，读取刚体存储行应限制为 min(raw_count, capacity)，并另报溢出，不能把被丢接触算成有效记录。外部模式调用 collide；MuJoCo 原生模式由 solver 导出。碰撞覆盖、接触材料、solver 响应分开诊断。full surface contact 是 CollisionPipeline 开关；其 edge/face soft records 由 VBD 指定路径消费，particle-only 消费器明确拒绝，并非支持状态未知。

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

## 相关知识

- [concept:collisions](#/record/concept%3Acollisions)
- [pipeline:enable_rigid_soft_full_surface_contact](#/record/pipeline%3Aenable_rigid_soft_full_surface_contact)
- [recipe:external-collision](#/record/recipe%3Aexternal-collision)
- [recipe:mujoco-native-contact](#/record/recipe%3Amujoco-native-contact)

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/concepts/collisions.html)。

## 固定版本原始出处

- [docs/concepts/collisions.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/collisions.rst#L1)
