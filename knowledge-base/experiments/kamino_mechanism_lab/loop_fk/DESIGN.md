# Kamino 闭环与 FK 实验设计（运行前草稿）

固定 Newton 1.7.0 `7e75abe28b8d69522bc0b34837aaed2c303dff5a`，只使用 CPU。尚未构造或运行 Newton；先由主代理审阅并冻结 [协议](protocol-draft.json)。

采用固定基座的平面四杆平行四边形。四个 box 各 1 kg，底/顶杆为 0.1×0.01×0.01 m，左右杆为 0.01×0.01×0.1 m；铰点间距 0.112 m。四铰轴沿 Y，第一铰为 EFFORT 主动关节，其余被动。底座有 world fixed joint，闭环铰不进入 spanning-tree articulation。质量惯量显式设置并锁定，碰撞关闭，避免接触、密度累加和关节限位干扰。

第一组比较 FK 初值策略 `reset_state=True/False`，通过公共 `ResetConfig.FromActuatorQ` 依次请求 ±0.2、±0.4 rad 等六个目标。被动关节、body poses 由 solver 推导。独立 NumPy 平行四边形公式检验所有 body 位姿、四铰点闭合和被动坐标；不只看 success 标志。位置误差和闭合阈值 10 µm，旋转/关节角阈值 0.1 mrad；两种初值策略执行同样目标并接受同一门槛。

第二组实际进行 120 步、0.5 s 的重力与 0.02 N·m 恒定主动力矩仿真。A 移除闭环边、保留相同刚体和树边，B 保留完整闭环。对 A 也计算同一对虚拟铰点的距离。B 最大闭合误差 ≤0.5 mm，同时主动角范围 ≥0.01 rad；A 的最大虚拟开口 ≥1 mm 且至少为 B 的 5 倍才支持闭环约束作用的结论。这是结构对照，不是单参数调优。不能达到区分门槛时记录“未形成判别”，不追改验收标准。

每个 case/variant 用独立进程重复两次，共 8 次正式运行。保存完整 body/joint arrays、几何/铰点、actual config、软件/设备、源码/协议/程序指纹、日志和结果；重复容差为 pose 1e-5、velocity 1e-4、rtol 1e-5，计时不参与复现判定。

本设计依据固定源码：

- `newton/tests/utils/basics.py:1271–1695` 的 fourbar 尺寸、拓扑和单主动关节构造；本实验以公共 builder 复现相同几何并明确固定根关节的 articulation 归属。
- `newton/tests/kamino/test_kamino_kinematics_resets.py:282–369` 的 actuator-driven FK 与关节残差检查。
- `newton/_src/solvers/kamino/solver_kamino.py:579–679,899–1040` 的公共 reset、主动坐标输入、success_mask 和状态同步契约。
- `newton/_src/solvers/kamino/config.py:978–1117` 的 FK tolerance、初值、incremental solve 与 regularization 语义。

适用边界：单世界、固定基座、一个主动铰、初态附近的平面非奇异分支，无 contact/limit/GPU。实验不证明任意闭环可解、全局分支选取、长时间稳定或 solver 性能排名。
