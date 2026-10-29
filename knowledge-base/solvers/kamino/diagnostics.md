# Kamino · 诊断与实验计划

**全部为 proposed / not_run，不是既有成功调参经验。**

## 闭环漂移或关节约束不一致

1. 先校验几何、关节拓扑和初始姿态。
2. 检查 FK 是否启用及其收敛。
3. 冻结 dt，扫描约束稳定化与 solver 预算，记录闭环误差及三类残差。

边界：不能仅用更强稳定化掩盖错误关节模型。

## PADMM 未收敛或反复达到上限

1. 读取 status 的 converged/iterations/r_p/r_d/r_c。
2. 冻结尺度和模型，比较 max_iterations 与各容差。
3. 再探索 eta/rho_0、warmstart 和合法的罚参数策略。

边界：残差阈值不是所有任务通用的物理精度保证。

## DVI 多接触误差增大

1. 核对 preconditioning=False 和后端默认组合。
2. 分别扫描外层迭代与 inequality sweeps。
3. 在相同接触/步长/模型下与 PADMM 比较。

边界：后端同名残差定义不同，不可直接以单个数字排名。

## 接触漏检或穿透

1. 确认使用内部 collision detector 还是外部 contacts。
2. 检查容量、gap 与几何。
3. 最后扫描 gamma/delta 与 dt。

边界：delta 和稳定化不能生成缺失接触。

## 改后端或积分器后配置报错

1. 从新的 Config(dynamics_solver=...) 重建。
2. 核对 sparse_dynamics / sparse_jacobian / preconditioning。
3. Moreau 同时启用内部碰撞；按异常定位组合约束。

边界：不要在完成默认解析后只改一个字段。



## 固定来源

- [newton/_src/solvers/kamino/solver_kamino.py:111](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L111)
- [docs/solvers/kamino.rst:5](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/kamino.rst#L5)
- [newton/_src/solvers/kamino/solver_kamino.py:1062](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L1062)
