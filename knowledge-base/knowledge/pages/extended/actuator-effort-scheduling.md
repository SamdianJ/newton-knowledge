# 执行器累加、限幅与控制频率

## 机制与输入输出

Actuator 的输出是 effort 的 scatter-add，调用方必须先清零将被累加的输出。Delay 读取命令历史，Drive 算原始 effort，Clamping 按电机模型限制输出，然后累加并更新 drive/delay 状态。

## 配置与诊断步骤

1. 检查实际执行器写入哪个控制输出数组，只清理该 effort 累加缓冲，保留需要持有的 targets。
2. 记录每个 actuator 的步进周期。Delay 的 N 个 timesteps 指执行器步，而不是渲染帧；控制更新频率与仿真子步的比例必须明确。
3. 如果 solver 同时启用同一关节的内置驱动，明确外部 effort 是替代、附加前馈还是另一项物理力，避免重复计算同一 PD 项。
4. 初版一执行器一 DOF，不含通用 transmission 与完整电机动力学；可微与 graphable 取决于 drive 的实现，不由 Actuator 名称自动保证。
5. Reset 同时考虑 Delay/Drive 的历史，按其接口处理；本配方不把所有执行器 reset 等价于 solver.reset。

## 适用范围与证据

Newton 1.7.0 固定文档、公开 API 与源码说明；runtime_status=not_run。这里的任务验证只验证知识检索与配置推理证据，不是物理任务执行或参数 A/B。设备、后端和捕获限制按所选路径核对。

## 精确 API

- [newton.actuators.Actuator](#/record/symbol%3Anewton.actuators.Actuator)
- [newton.actuators.DrivePD](#/record/symbol%3Anewton.actuators.DrivePD)

## 相关知识

- [module:actuators](#/record/module%3Aactuators)
- [concept:actuators](#/record/concept%3Aactuators)
- [stage:control](#/record/stage%3Acontrol)

## 固定出处

- [newton/_src/actuators/actuator.py:166](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/actuators/actuator.py#L166)
- [newton/_src/actuators/drives/drive_pd.py:68](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/actuators/drives/drive_pd.py#L68)
- [docs/concepts/actuators.rst:14](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/actuators.rst#L14)
