# 模型更新通知、私有缓存与捕获边界

## 机制与输入输出

Model 数组更新与后端私有缓存更新分开。ModelFlags 的宽泛分组与较窄分组各有自己的 bit；只检查 JOINT_DOF_PROPERTIES 不会自动覆盖所有窄通知。

## 配置与诊断步骤

1. 修改质量/质心/惯量时核对 BODY_INERTIAL_PROPERTIES；修改 armature 核对 JOINT_DOF_INERTIAL_PROPERTIES；增益、阻尼、摩擦和力限核对 JOINT_DOF_FORCE_PROPERTIES。
2. 通过选定 SolverMuJoCo 的 notify_model_changed(flags) 处理缓存与常数更新；直接改 Python 属性或 Model Warp 数组不是刷新后端的证明。
3. 固定源码说明 armature 和参考姿态相关更新可能重算 MuJoCo 常数，应在 reset/域随机化等时段规划，避免把完整重建放进每个子步。
4. 重新分配、拓扑/容量变化或捕获指针失效需要重建/重新捕获；仅数据更新是否可直接复用捕获图，需按具体后端更新函数与设备条件核查。
5. 改动后检查后端实际值、有限状态和相同输入下的响应。这里给出通知依据，不声称执行过该参数干预。

## 适用范围与证据

Newton 1.7.0 固定文档、公开 API 与源码说明；runtime_status=not_run。这里的任务验证只验证知识检索与配置推理证据，不是物理任务执行或参数 A/B。设备、后端和捕获限制按所选路径核对。

## 精确 API

- [newton.ModelFlags](#/record/symbol%3Anewton.ModelFlags)
- [newton.solvers.SolverMuJoCo.notify_model_changed](#/record/symbol%3Anewton.solvers.SolverMuJoCo.notify_model_changed)

## 相关知识

- [topic:lifecycle-observation](#/record/topic%3Alifecycle-observation)
- [module:newton](#/record/module%3Anewton)
- [solver:mujoco](#/record/solver%3Amujoco)

## 固定出处

- [newton/_src/sim/enums.py:8](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/enums.py#L8)
- [newton/_src/solvers/mujoco/solver_mujoco.py:5132](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L5132)
