# VBD DAT 的前提、预算与有限保证

## 机制与输入输出

rigid_soft_enable_dat 是针对已报告接触的 Divide-and-Truncate 限制，不是任意非凸场景全局无穿透保证。它要求 solver-owned pipeline。

## 配置与诊断步骤

1. 先构造 CollisionPipeline，再把 collision_pipeline= 传给 SolverVBD；step 必须 contacts=None。DAT 的分割平面来自检测时的参考构型。
2. AUTO 下相关 RIGID slot 解析 PRE_POST_INIT，检测在初始化前后；快速运动可核查 ITERATIONS 调度与 collision_frequency。DAT 家族激活时对应 slot 不能为 NONE。同时启用 rigid-soft DAT 与 self-contact DAT 时，两者共享 motion reference：RIGID 与 SOFT_SELF_CONTACT 必须解析为相同调度类型，若使用 ITERATIONS 还须频率相同；应同时设置两个 slot，不能仅提高其中一个的频率。
3. 每侧预算含 0.5 * dat_conservative_bound_relaxation * 最小查询半径，半径由 gap、soft feature radius 与 shape margin 组成；在构造时固定，后改这些字段不会自动刷新预算。该各向同性预算约束模型中每个动态 body/particle 的检测间运动，不只限制接触附近的对象。
4. Kinematic bodies 在 solver 外运动，不被截断。overflow 丢掉的接触不参与限制；非凸几何稠密覆盖也不由此自动保证。
5. 采样/二分可能漏掉样点间穿过再返回的轨迹；额外 interval prefix 路径仍标 experimental，不将其视为成熟无条件保证。
6. 用具体接触记录、运动预算、检测时刻和实际轨迹排查，再决定是否增大预算/检测频率或改善几何；提高迭代不能补回缺失接触。

## 适用范围与证据

Newton 1.7.0 固定文档、公开 API 与源码说明；runtime_status=not_run。这里的任务验证只验证知识检索与配置推理证据，不是物理任务执行或参数 A/B。设备、后端和捕获限制按所选路径核对。

## 精确 API

- [newton.solvers.SolverVBD](#/record/symbol%3Anewton.solvers.SolverVBD)
- [newton.solvers.SolverBase.set_collision_frequency](#/record/symbol%3Anewton.solvers.SolverBase.set_collision_frequency)

## 相关知识

- [solver:vbd](#/record/solver%3Avbd)
- [concept:collisions](#/record/concept%3Acollisions)
- [recipe:solver-owned-collision](#/record/recipe%3Asolver-owned-collision)
- [pipeline:enable_rigid_soft_full_surface_contact](#/record/pipeline%3Aenable_rigid_soft_full_surface_contact)

## 固定出处

- [newton/_src/solvers/vbd/solver_vbd.py:167](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L167)
- [newton/_src/solvers/solver.py:623](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/solver.py#L623)
- [newton/_src/solvers/vbd/solver_vbd.py:612](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L612)
- [newton/_src/solvers/vbd/solver_vbd.py:4808](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L4808)
