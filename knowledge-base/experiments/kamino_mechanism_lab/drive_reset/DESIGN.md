# Kamino 驱动与 reset：事前设计

设计在运行前完成并经主代理冻结为 [protocol.json](protocol.json)。正式运行和独立分析已完成，结果见 [RESULTS.md](RESULTS.md)；本文件保留事前场景、指标和门槛说明。

共同模型为 1 kg 刚体通过 Y 轴转动关节连至世界，COM 相对 body origin 偏移 0.5 m，COM 惯量对角线为 1 kg·m²，锁定惯量。零重力、无接触、无臂长惯量/阻尼/摩擦，单 world。关节有效惯量由平行轴定理独立计算为 1.25 kg·m²。模型包含 COM 偏移，可同时检查 origin/COM 转换，避免只验证退化的零偏移情形。

## 场景与验收

1. **显式努力与有界 implicit PD。** 显式请求 ±10 N·m，限幅为 1 N·m；PD 目标 ±1 rad，kp=100、kd=2，同样限幅 1 N·m。dt=0.005 s，80 步，前 40 步正向、后 40 步反向。参考解由 ±1/1.25 的加速度独立积分；读取实际施加 wrench，且 PD 路径还读取 joint_lambdas_tau。要求正反力矩误差 ≤0.002 N·m、最大绝对力矩 ≤1.001、关节速度参考最大误差 ≤0.002 rad/s、Euler 位置参考最大误差 ≤0.001 rad、锚点漂移 ≤0.5 mm。路由必须实际为 BODY_WRENCHES / EFFORT_CTS。阈值分别为 0.2% 力限、1.25% 峰值速度和 0.1% COM 半径，能拒绝未限幅、符号反转或错误惯量。
2. **默认 reset 重放。** 在 bounded-PD 下先跑 60 步形成非零位姿、速度、乘子及内部 warmstart 历史。默认 reset 后与新求解器的初态重放比较。检查恢复初始 body pose、速度清零、lambda/加速度/时间清零；Control 单独捕获并要求不变，然后显式设置重放命令。保存初始及每步 body/joint 状态。
3. **preserve reset 重放。** 同样预热，一边在旧求解器 preserve reset；另一边创建新求解器，仅复制同一 body pose/velocity 再 preserve reset。二者都必须保留运动状态，清除旧乘子与内部历史；之后重放同一控制序列。该设计不将“只覆盖 State”当完整 reset，也不将不一致输入的 projection 作为 preserve 能力。

每变体独立进程运行两次，共 12 个主运行。重复与配对重放容差为 pose 1e-5、velocity 1e-4、rtol 1e-5。reset 写零/复制检查使用 1e-6 或 1e-7 级阈值；预热必须产生 |q|>0.001 rad 且 |lambda|>0.5 N·m，防止空测。Reset 场景明确配置 `warmstart_mode=internal`；drive 场景保持 containers。PADMM 默认加速保持启用，CPU 禁用 graph conditionals。全部配置保存，不将默认 ResetConfig 等同于所有默认 SolverConfig。

## 实验与知识边界

这些实验覆盖单 revolute 的饱和驱动与两个 reset 生命周期路径，不验证多自由度 joint、PD 非饱和跟踪、接触缓存、多 world 掩码、flags、FK reset、callback、GPU 或长期性能。status 残差和迭代数作为诊断记录，不将 converged 当轨迹正确性的替代条件，也不要求两条不同驱动路径迭代数相同。

runner 只能使用 public API 构建/推进；用于路由、实际 wrench、内部时间的私有读取被明确标记为 instrumentation。NPZ 原始轨迹、每步命令、重置前后快照、resolved config、环境/源码/协议/runner 哈希及日志全部保存。失败保持为失败；任何协议修订必须先记录新版本，不根据已见结果放宽验收。

具体机器可读协议：[protocol-draft.json](protocol-draft.json)。独立 NumPy 分析器从原数组重算指标，不复用 runner 的验收结论。
