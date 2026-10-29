# 刚体与可变形体耦合

MuJoCo 刚体 / VBD 布料：Proxy 与 ADMM。

从 `newton.solvers.experimental.coupled` 导入 ModelView、SolverCoupled、SolverCoupledProxy、SolverCoupledADMM。共享一个 Model，用 Entry 的 bodies/particles/shapes/joints 划分所有权，并在 solver(view) 工厂中绑定 MuJoCo 或 VBD 的构造参数。每个 entry 可有自己的 substeps；只有 owned outputs 合并回共享 state_out。

Proxy 将 source 的真实端点映射为 destination 中的代理端点，按 lagged/staggered 调度，结合质量缩放、relaxation 与反馈 harvest。通用 proxy loop 当前最多两个 entries。代理局部碰撞可由工厂创建并缓存 contacts；反馈不是简单复制位置。

ADMM 在接口上恢复局部状态、推进 subsolvers、解约束行、更新 dual，并注入相反方向的力。跨 solver model joints 支持 BALL/FIXED/REVOLUTE；PRISMATIC/DISTANCE/D6 接口行尚未支持。跨 solver attachment 使用 ModelBuilder.add_attachment_particle_body；接触须显式配置 ContactPair，coupler 有私有检测与固定容量缓存，按源文档处理避免重复求解同一约束。

`integrate_with_external_rigid_solver` 只描述 VBD 与外部刚体步进的一个开关；双向耦合还要求 ownership、接触、反馈、私有历史通知和子步调度。此知识配方有官方源码/示例依据，尚未作为本库物理任务执行；外部共享 Contacts、entry 内部检测和 ADMM 私有接触不能无条件共用。

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

## 相关知识

- [concept:coupling](#/record/concept%3Acoupling)
- [recipe:coupled-rigid-deformable](#/record/recipe%3Acoupled-rigid-deformable)
- [solver:vbd](#/record/solver%3Avbd)
- [solver:mujoco](#/record/solver%3Amujoco)

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/concepts/coupling.html)。

## 固定版本原始出处

- [docs/concepts/coupling.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/coupling.rst#L1)
- [newton/examples/multiphysics/example_mujoco_vbd_coupled_solver.py:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/examples/multiphysics/example_mujoco_vbd_coupled_solver.py#L1)
