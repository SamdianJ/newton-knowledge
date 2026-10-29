# Control 与外力

先形成可解释的输入，再推进物理。

导入机器人后保留 articulation、joint、site 的 label/index 映射。IKSolver 求运动学目标；ControllerDifferentialIK 用模型内 FK/Jacobian 每步求控制信号，`step(inputs=..., outputs=..., dt=...)`，每个受控 articulation 匹配一个工具 site，只控制一坐标一 DOF 的关节。它能处理异构受控机器人集合，但 ArticulationView 当前的批量布局假设同质，两者能力不能混用。

`newton.use_coord_layout_targets` 在创建任何模型前一次设置。启用 coord layout 时 `Control.joint_target_q` 对齐 `joint_coord_count`，`joint_target_qd` 和 `joint_f` 对齐 `joint_dof_count`；使用 `joint_target_q_start` 等映射，不按 qd offset 盲写四元数目标。`Control.clear(model)` 恢复合法初始坐标目标。

Controller 输出通过真实端口与选中关节映射写 Control，配置该 solver 支持的驱动，再走求解循环。对 MuJoCo 核查模型转换后的 drive、力限与 backend 选项；IK 本身不确保碰撞可行、力矩可行或接触稳定。

每个子步清理 State 外力，按实际调度写 targets/effort；Actuator scatter-add 输出需要调用方清零。记录 controller/drive/solver 三层的参数来源。

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

## 相关知识

- [module:controllers](#/record/module%3Acontrollers)
- [module:ik](#/record/module%3Aik)
- [module:actuators](#/record/module%3Aactuators)
- [topic:robot-control](#/record/topic%3Arobot-control)

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/concepts/actuators.html)。

## 固定版本原始出处

- [docs/concepts/actuators.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/actuators.rst#L1)
- [docs/migration.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/migration.rst#L1)
