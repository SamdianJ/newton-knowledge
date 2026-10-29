# 接触容量、观测冻结与溢出诊断

## 机制与输入输出

live contact count 要区分原始计数 raw_count 与已存储行数：刚体写入先递增计数，溢出时 raw_count 可超过 capacity，不能直接作为数组遍历上限。capacity 是已分配数组大小；CONTACT_F 分配按 rigid_contact_max + soft_contact_max，刚体槽在前，软接触槽在后。零接触不表示零容量。

## 配置与诊断步骤

1. 在分配接触观测前确定所选碰撞路径的容量，创建 Contacts，再给 solver.observables(kinds={CONTACT_F}, contacts=contacts)。即使容量为零也要绑定 Contacts。
2. 分配后容量冻结在 Model 上；删除 Observables 不能解除冻结。修改已冻结容量必须从 builder 重新 finalize/new Model，再构造 solver、pipeline、Contacts 与 Observables。同容量更换 storage 也必须重新绑定相应观测；捕获了旧数组指针时还要重新捕获。
3. 刚体数组只读取 min(raw_count, capacity) 行，并单独报告 raw_count > capacity 的 overflow。分别检查 broad-phase/triangle-pair/reduction 中间缓冲、solver 内部每对象接触列表和求解约束容量；最终计数未超限不代表中间阶段没有丢候选。nconmax/njmax 与 iterations/tolerance 不是同一类预算。
4. VBD rigid_body_particle_contact_buffer_size 涵盖粒子和 full-surface edge/face 记录。overflow 表示可能丢接触；DAT 也无法截断未被报告的接触。
5. 增加迭代只改变已有约束的求解预算，不能补回被过滤、漏检或溢出丢掉的行。

## 适用范围与证据

Newton 1.7.0 固定文档、公开 API 与源码说明；runtime_status=not_run。这里的任务验证只验证知识检索与配置推理证据，不是物理任务执行或参数 A/B。设备、后端和捕获限制按所选路径核对。

## 精确 API

- [newton.solvers.SolverBase.observables](#/record/symbol%3Anewton.solvers.SolverBase.observables)
- [newton.CollisionPipeline](#/record/symbol%3Anewton.CollisionPipeline)

## 相关知识

- [concept:solver-observables](#/record/concept%3Asolver-observables)
- [concept:collisions](#/record/concept%3Acollisions)
- [recipe:mujoco-native-contact](#/record/recipe%3Amujoco-native-contact)
- [solver:vbd](#/record/solver%3Avbd)

## 固定出处

- [newton/_src/solvers/solver.py:721](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/solver.py#L721)
- [newton/_src/sim/collide.py:1250](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/collide.py#L1250)
- [docs/concepts/solver_observables.rst:75](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/solver_observables.rst#L75)
- [newton/_src/solvers/vbd/solver_vbd.py:587](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L587)
- [newton/_src/sim/collide.py:142](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/collide.py#L142)
- [newton/_src/sim/collide.py:223](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/collide.py#L223)
- [newton/_src/sim/model.py:1965](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L1965)
- [newton/_src/geometry/narrow_phase.py:2225](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/geometry/narrow_phase.py#L2225)
