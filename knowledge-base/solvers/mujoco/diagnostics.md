# MuJoCo · 诊断与实验计划

**全部为 proposed / not_run，不是既有成功调参经验。**

## 穿透或接触响应偏软

1. 确认编译后的几何、接触记录和碰撞来源。
2. 冻结质量/尺度与 dt，比较 solref/solimp 或相应 ke/kd 转换模式。
3. 再扫 iterations/tolerance，分别量测穿透和收敛。

边界：更高迭代不能修复几何漏检。

## 抓持缓慢滑落

1. 确认 condim、mu、cone 与 impratio。
2. 冻结驱动目标，记录切向位移和法向力。
3. 逐组比较摩擦模型和接触软化。

边界：impratio 不是摩擦系数。

## 控制目标改变但状态没有跟随

1. 检查控制端口、关节切片与驱动映射；control 和外力每步提交，不受 update_data_interval 降采样。
2. 核对 joint ref、关节坐标与 actuator target。
3. 另行检查 state 的 update_data_interval 同步；先用逐步 state 同步和固定控制输入建立基线。

边界：先排查同步和参考坐标，再调整增益。

## 多接触场景容量或编译问题

1. 检查 nconmax/njmax/njmax_nnz 告警与初始接触数。
2. 确认 world 拆分与 CPU/GPU 路径。
3. 容量与优化预算分别扫描。

边界：容量设置不能当作材料参数。



## 固定来源

- [newton/_src/solvers/mujoco/solver_mujoco.py:470](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L470)
- [docs/solvers/mujoco.rst:5](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/mujoco.rst#L5)
- [newton/_src/solvers/mujoco/solver_mujoco.py:4557](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4557)
