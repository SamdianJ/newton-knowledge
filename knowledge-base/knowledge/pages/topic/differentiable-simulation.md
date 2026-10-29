# 可微仿真

requires_grad、Warp Tape 与后端能力表。

固定版本官方能力表中，仅 SolverSemiImplicit 和 SolverFeatherstone 标为 basic 可微；SolverVBD、SolverXPBD、MuJoCo、Kamino、ImplicitMPM、Style3D 均未标为可微支持。`requires_grad=True` 分配梯度缓冲不能改变这个能力边界，尤其不能从 Warp 语言可微推断任一 solver 可微。

官方最小流程：builder.finalize(requires_grad=True)，分配带梯度 State 和 loss，在 `with wp.Tape():` 内执行 forward rollout 和标量 loss，然后 `tape.backward(loss)`。多步优化需要保存 Tape 所需的状态历史，不能随意双缓冲覆盖中间量；具体示例看 newton/examples/diffsim。

本条是源码与官方示例解释，没有在本知识库中完成梯度数值检验。外部 simulator 的可微能力、控制器可微能力和 Newton backend 的梯度支持分别判断。

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

## 精确 API 入口

- [newton.ModelBuilder.finalize](#/record/symbol%3Anewton.ModelBuilder.finalize)
- [newton.solvers.SolverSemiImplicit](#/record/symbol%3Anewton.solvers.SolverSemiImplicit)

## 相关知识

- [module:solvers](#/record/module%3Asolvers)
- [solver:vbd](#/record/solver%3Avbd)
- [solver:xpbd](#/record/solver%3Axpbd)
- [solver:semi-implicit](#/record/solver%3Asemi-implicit)
- [solver:featherstone](#/record/solver%3Afeatherstone)

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/solvers/index.html)。

## 固定版本原始出处

- [docs/solvers/index.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/index.rst#L1)
- [docs/solvers/index.rst:463](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/index.rst#L463)
- [newton/examples/diffsim/example_diffsim_ball.py:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/examples/diffsim/example_diffsim_ball.py#L1)
- [newton/_src/sim/builder.py:13192](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/builder.py#L13192)
- [newton/_src/solvers/semi_implicit/solver_semi_implicit.py:34](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/semi_implicit/solver_semi_implicit.py#L34)
