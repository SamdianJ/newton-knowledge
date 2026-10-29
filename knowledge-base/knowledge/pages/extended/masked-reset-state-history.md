# 局部复位的公共状态与后端历史

## 机制与输入输出

公共初态恢复、Control 恢复、solver 历史重置是不同责任。ArticulationView 的 mask 和 SolverBase.reset 的 world_mask 不能直接复用。

## 配置与诊断步骤

1. 核查 view.world_count 与 Model.world_count、articulation/world 映射。view 的 mask 支持 (world_count,) 或 (world_count,count_per_world)。
2. solver world_mask 为 (model.world_count+1,)；前面选择局部 world，最后一项选择 global world=-1。只复位 world 1 时先验证该 world 存在，显式保持其余项及 global 项为 False。
3. 按选中对象恢复 State/Control，并同步需要的双缓冲状态。再用具体 backend 的 solver.reset(state, world_mask=..., flags=...) 清理私有历史；不要把默认 no-op 当作恢复物理初态。
4. StateFlags 的 JOINT_Q/QD、BODY_Q/QD、PARTICLE_Q/QD 与 FORCE 分组表达公共输入变化，不是 ModelFlags。
5. MuJoCo、VBD、Kamino 的 reset override 与缓存不同，核查选定配置；不能因 mask 同形就推断所有后端历史行为等价。global 实体还可能位于数组前后两段。

## 适用范围与证据

Newton 1.7.0 固定文档、公开 API 与源码说明；runtime_status=not_run。这里的任务验证只验证知识检索与配置推理证据，不是物理任务执行或参数 A/B。设备、后端和捕获限制按所选路径核对。

## 精确 API

- [newton.StateFlags](#/record/symbol%3Anewton.StateFlags)
- [newton.solvers.SolverMuJoCo.reset](#/record/symbol%3Anewton.solvers.SolverMuJoCo.reset)
- [newton.selection.ArticulationView.set_attribute](#/record/symbol%3Anewton.selection.ArticulationView.set_attribute)

## 相关知识

- [recipe:worlds-reset](#/record/recipe%3Aworlds-reset)
- [topic:worlds-batching](#/record/topic%3Aworlds-batching)
- [concept:worlds](#/record/concept%3Aworlds)
- [module:selection](#/record/module%3Aselection)

## 固定出处

- [newton/_src/sim/enums.py:73](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/enums.py#L73)
- [newton/_src/solvers/mujoco/solver_mujoco.py:4606](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/mujoco/solver_mujoco.py#L4606)
- [newton/_src/utils/selection.py:1531](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/utils/selection.py#L1531)
- [newton/_src/core/reset.py:19](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/core/reset.py#L19)
- [newton/_src/solvers/solver.py:1003](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/solver.py#L1003)
