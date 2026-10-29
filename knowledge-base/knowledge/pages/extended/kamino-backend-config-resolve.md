# Kamino 后端配置组与残差语义

## 机制与输入输出

dynamics_solver 选择会触发一组依赖默认值。应该在 SolverKamino.Config(dynamics_solver="dvi") 构造时选择后端，并核查解析后的 dynamics、线性求解和稀疏布局，而非只事后改字符串。

## 配置与诊断步骤

1. PADMM 是默认 proximal ADMM 路径，使用其对应的 dense Jacobian/dynamics 与线性系统配置；DVI 有自己的块/稀疏与求解器组合。实际值由 Config 的初始化/校验逻辑解析。
2. PADMM 使用预条件冲量 x/y，但报告 r_p=||P(x-y)||_inf，r_d=||P^-1(eta(x-x_prev)+rho(y-y_prev))||_inf；P 因子将其转到物理约束单位。DVI r_p 为物理冲量的锥投影距离，r_d 为对偶锥速度距离/双边速度违约。两者 r_p 为 N·s 或 N·m·s，r_d 为 m/s 或 rad/s，r_c 为冲量-速度内积的绝对最大值 [J]；同单位不表示同一定义。
3. 官方文档说明两者残差均为绝对最大值，未除以参考范数归一；不能按同名字段直接跨 backend 排优劣或套用同一容差。
4. 切换后端是配置组干预，应保存所有实际 diff、终止状态和物理误差，不写成只改变一个独立参数的 A/B。
5. 首版深入知识中 config.padmm.max_iterations=200 是 PADMM 的声明上限，不是 DVI 的等效预算。本配方没有执行后端性能比较。

## 适用范围与证据

Newton 1.7.0 固定文档、公开 API 与源码说明；runtime_status=not_run。这里的任务验证只验证知识检索与配置推理证据，不是物理任务执行或参数 A/B。设备、后端和捕获限制按所选路径核对。

## 精确 API

- [newton.solvers.SolverKamino](#/record/symbol%3Anewton.solvers.SolverKamino)
- [newton.solvers.SolverKamino.Config](#/record/symbol%3Anewton.solvers.SolverKamino.Config)

## 相关知识

- [solver:kamino](#/record/solver%3Akamino)
- [page:solvers/kamino/parameters.md](#/record/page%3Asolvers%2Fkamino%2Fparameters.md)
- [page:solvers/kamino/theory.md](#/record/page%3Asolvers%2Fkamino%2Ftheory.md)

## 固定出处

- [newton/_src/solvers/kamino/solver_kamino.py:111](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L111)
- [newton/_src/solvers/kamino/solver_kamino.py:186](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L186)
- [docs/solvers/kamino.rst:91](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/kamino.rst#L91)
- [newton/_src/solvers/kamino/config.py:361](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/config.py#L361)
- [newton/_src/solvers/kamino/solver_kamino.py:485](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L485)
