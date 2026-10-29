# 坐标目标、DOF 布局与合法 Control 清理

## 机制与输入输出

坐标布局、索引和清理是三个独立动作。先在创建模型前设置 newton.use_coord_layout_targets；coord layout 下 joint_target_q 的长度是 joint_coord_count，joint_target_qd/joint_f 是 joint_dof_count。FREE/BALL/DISTANCE 含四元数，不能把 qd 的 DOF offset 当作 q 的坐标 offset。

## 配置与诊断步骤

1. 从 Model 的 joint_target_q_start 与 joint_q/qd_start 核查每个关节的真实切片，再映射 controller 输出；只写被控制的关节。
2. Reset 时使用 `control.clear(model)`：它从 model.joint_target_q 恢复合法坐标目标；不给 model 的兼容路径会零填，四元数槽可能成为 (0,0,0,0)。
3. State.clear_forces 处理外力，执行器输出清零处理累加，Control.clear(model) 处理控制初态，不能把这三个调用混为同一个每步必做动作。
4. 比较当前与目标四元数的有效性、关节切片长度及速度单位，再排查增益或 solver 迭代。

## 适用范围与证据

Newton 1.7.0 固定文档、公开 API 与源码说明；runtime_status=not_run。这里的任务验证只验证知识检索与配置推理证据，不是物理任务执行或参数 A/B。设备、后端和捕获限制按所选路径核对。

## 精确 API

- [newton.Control.clear](#/record/symbol%3Anewton.Control.clear)
- [newton.Control.joint_target_q](#/record/symbol%3Anewton.Control.joint_target_q)
- [newton.Control.joint_target_qd](#/record/symbol%3Anewton.Control.joint_target_qd)

## 相关知识

- [topic:robot-control](#/record/topic%3Arobot-control)
- [concept:conventions](#/record/concept%3Aconventions)
- [module:selection](#/record/module%3Aselection)

## 固定出处

- [newton/_src/sim/control.py:76](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/control.py#L76)
- [newton/_src/sim/control.py:44](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/control.py#L44)
- [newton/_src/sim/control.py:50](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/control.py#L50)
- [docs/migration.rst:149](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/migration.rst#L149)
