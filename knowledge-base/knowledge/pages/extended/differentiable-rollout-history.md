# 可微 rollout 的后端与状态历史

## 机制与输入输出

先选固定版本支持的微分路径。官方能力表仅将 SolverSemiImplicit / SolverFeatherstone 标为 basic 可微，XPBD/VBD 不支持；requires_grad=True 只是分配相关缓冲的前提。

## 配置与诊断步骤

1. 通过 builder.finalize(requires_grad=True) 分配模型，按示例创建需要梯度的 State 与标量 loss。
2. 在 wp.Tape() 范围内记录 forward rollout 和 loss 计算，再调用 tape.backward(loss)。检查所求导的数组是否参与、是否分配 grad，以及是否被非可微流程断开。
3. 多步时保留反向所需的中间状态/数组；不能照搬普通仿真的双缓冲交换后覆盖所有历史。按 diffsim 示例的状态列表与优化循环处理。
4. 梯度非 None 不等于数值正确，还需有限差分等验证；当前条目是源码与示例依据，不宣称本库完成梯度数值检验。
5. 控制器、导入器或外部组件的梯度支持也要分别核查，不能从 Warp 可微直接推导整个应用可微。

## 适用范围与证据

Newton 1.7.0 固定文档、公开 API 与源码说明；runtime_status=not_run。这里的任务验证只验证知识检索与配置推理证据，不是物理任务执行或参数 A/B。设备、后端和捕获限制按所选路径核对。

## 精确 API

- [newton.ModelBuilder.finalize](#/record/symbol%3Anewton.ModelBuilder.finalize)
- [newton.solvers.SolverSemiImplicit](#/record/symbol%3Anewton.solvers.SolverSemiImplicit)

## 相关知识

- [topic:differentiable-simulation](#/record/topic%3Adifferentiable-simulation)
- [solver:semi-implicit](#/record/solver%3Asemi-implicit)
- [solver:featherstone](#/record/solver%3Afeatherstone)
- [solver:xpbd](#/record/solver%3Axpbd)

## 固定出处

- [newton/_src/sim/builder.py:13192](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/builder.py#L13192)
- [newton/_src/solvers/semi_implicit/solver_semi_implicit.py:34](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/semi_implicit/solver_semi_implicit.py#L34)
- [docs/solvers/index.rst:463](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/index.rst#L463)
- [newton/examples/diffsim/example_diffsim_ball.py:97](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/examples/diffsim/example_diffsim_ball.py#L97)
