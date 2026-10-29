# SolverKamino

SolverKamino：正式公开类、能力边界与覆盖状态。

最大坐标刚体与闭环约束、硬摩擦接触，BETA 1 / experimental。分层 Config/PADMM/DVI，config.padmm.max_iterations 声明默认 200；不与其他后端预算等价。无布料/软体/粒子求解支持；本库有 2 组保存的 CPU A/B，每个参数值独立进程复现两次；结论仅限保存场景、后端与参数组。

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

## 精确 API 入口

- [newton.solvers.SolverKamino](#/record/symbol%3Anewton.solvers.SolverKamino)

## 相关知识

- [module:solvers](#/record/module%3Asolvers)

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/solvers/index.html)。

## 固定版本原始出处

- [newton/solvers.py:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/solvers.py#L1)
- [docs/solvers/index.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/index.rst#L1)
- [docs/solvers/kamino.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/kamino.rst#L1)
- [newton/_src/solvers/kamino/solver_kamino.py:111](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/kamino/solver_kamino.py#L111)
