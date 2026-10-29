# SolverSemiImplicit

SolverSemiImplicit：正式公开类、能力边界与覆盖状态。

最大坐标半隐式积分，支持刚体、关节、粒子与软体，cloth 无自碰撞。官方可微性为 basic，文档 Tape 示例使用此 backend。首版只有源码索引，未整理参数与实测。

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

## 精确 API 入口

- [newton.solvers.SolverSemiImplicit](#/record/symbol%3Anewton.solvers.SolverSemiImplicit)

## 相关知识

- [module:solvers](#/record/module%3Asolvers)
- [topic:differentiable-simulation](#/record/topic%3Adifferentiable-simulation)

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/solvers/index.html)。

## 固定版本原始出处

- [newton/solvers.py:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/solvers.py#L1)
- [docs/solvers/index.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/index.rst#L1)
- [newton/_src/solvers/semi_implicit/solver_semi_implicit.py:34](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/semi_implicit/solver_semi_implicit.py#L34)
