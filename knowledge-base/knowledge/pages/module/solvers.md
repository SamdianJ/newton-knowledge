# 求解器接口与后端

SolverBase 接口、8 个后端与能力边界。

## 职责、输入与输出

统一接口为 step(state_in,state_out,control,contacts,dt,observables=...)。坐标表示、材料响应、关节类型、碰撞来源、可微性和观测支持按 backend 与配置分别判断。

## 失败模式与限制

继承 ObservableKind 名称不代表支持；以 solver.supported_observables 为准。solver.reset 默认实现不恢复所有物理初态；查看后端覆盖。coupled 是 experimental 子系统，不计作第九个普通后端。

## 模块公开导出索引

- [SolverBase](#/record/symbol%3Anewton.solvers.SolverBase)
- [SolverFeatherstone](#/record/symbol%3Anewton.solvers.SolverFeatherstone)
- [SolverImplicitMPM](#/record/symbol%3Anewton.solvers.SolverImplicitMPM)
- [SolverKamino](#/record/symbol%3Anewton.solvers.SolverKamino)
- [SolverMuJoCo](#/record/symbol%3Anewton.solvers.SolverMuJoCo)
- [SolverSemiImplicit](#/record/symbol%3Anewton.solvers.SolverSemiImplicit)
- [SolverStyle3D](#/record/symbol%3Anewton.solvers.SolverStyle3D)
- [SolverVBD](#/record/symbol%3Anewton.solvers.SolverVBD)
- [SolverXPBD](#/record/symbol%3Anewton.solvers.SolverXPBD)
- [style3d](#/record/symbol%3Anewton.solvers.style3d)
- [experimental](#/record/symbol%3Anewton.solvers.experimental)

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

## 精确 API 入口

- [newton.solvers.SolverBase](#/record/symbol%3Anewton.solvers.SolverBase)
- [newton.solvers.SolverBase.step](#/record/symbol%3Anewton.solvers.SolverBase.step)
- [newton.solvers.SolverBase.reset](#/record/symbol%3Anewton.solvers.SolverBase.reset)

## 相关知识

- [topic:differentiable-simulation](#/record/topic%3Adifferentiable-simulation)
- [concept:coupling](#/record/concept%3Acoupling)
- [solver:vbd](#/record/solver%3Avbd)
- [solver:xpbd](#/record/solver%3Axpbd)

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/solvers/index.html)。

## 固定版本原始出处

- [newton/solvers.py:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/solvers.py#L1)
- [docs/solvers/index.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/index.rst#L1)
- [docs/api/newton_solvers.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/api/newton_solvers.rst#L1)
- [newton/_src/solvers/solver.py:218](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/solver.py#L218)
- [newton/_src/solvers/solver.py:1031](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/solver.py#L1031)
- [newton/_src/solvers/solver.py:1003](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/solver.py#L1003)
