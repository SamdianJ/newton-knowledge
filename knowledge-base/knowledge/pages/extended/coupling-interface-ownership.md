# 耦合接口约束与重复求解排查

## 机制与输入输出

ModelView 划分所有权，coupler 与子 solver 不能同时重复负责同一接口行。ADMM 的对称接口约束路径不同于代理反馈。

## 配置与诊断步骤

1. 对每个 body/particle/joint/shape 检查所属 Entry；仅当关节端点属于不同 entry 且 joint 本身不归任一子 solver 时，coupler 接管该跨 solver 关节。
2. 当前 ADMM 关节行支持 BALL/FIXED/REVOLUTE，PRISMATIC/DISTANCE/D6 行未支持。不要根据某个子 solver 自己支持关节就推断 coupler 也支持接口行。
3. particle-body attachment 由 ModelBuilder.add_attachment_particle_body 建立。跨 entry 由 coupler 处理；同 entry 留给该 solver，端点无 owner 或该 solver 不支持时应检查 warning。
4. legacy coupling:body_particle_attachment 自定义行仍被 ADMM 消费，但对 VBD 直接求解不可见；迁移时分清数据布局。
5. ContactPair 显式开启 ADMM 私有接触检测，确保子 solver 的接触路径没有再次解同一跨 entry 交互。接触摩擦从模型材料读取，不是 ContactPair 的任意字段。
6. attachment 是物理假设，不作为夹爪接触抓取的默认替代；本知识配方未执行实际耦合任务。

## 适用范围与证据

Newton 1.7.0 固定文档、公开 API 与源码说明；runtime_status=not_run。这里的任务验证只验证知识检索与配置推理证据，不是物理任务执行或参数 A/B。设备、后端和捕获限制按所选路径核对。

## 精确 API

- [newton.solvers.experimental.coupled.SolverCoupledADMM](#/record/symbol%3Anewton.solvers.experimental.coupled.SolverCoupledADMM)
- [newton.ModelBuilder.add_attachment_particle_body](#/record/symbol%3Anewton.ModelBuilder.add_attachment_particle_body)

## 相关知识

- [concept:coupling](#/record/concept%3Acoupling)
- [topic:coupling](#/record/topic%3Acoupling)
- [recipe:coupled-rigid-deformable](#/record/recipe%3Acoupled-rigid-deformable)

## 固定出处

- [newton/_src/solvers/coupled/solver_coupled_admm.py:428](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/coupled/solver_coupled_admm.py#L428)
- [newton/_src/sim/builder.py:10234](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/builder.py#L10234)
- [docs/concepts/coupling.rst:256](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/coupling.rst#L256)
