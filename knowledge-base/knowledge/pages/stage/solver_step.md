# Solver step 与状态推进

control → collision detection → solver.step()。

输入：Model、state_in、Control、匹配的 Contacts 和子步 dt。输出：state_out 与请求的 Observables。使用具体 solver 的坐标、碰撞和驱动支持；每帧 substeps 决定 dt，iterations 仅是一次 step 的内部预算。更新传感器后交换 State；复位或 Model 修改时同步后端私有缓存。

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

## 相关知识

- [stage:control](#/record/stage%3Acontrol)
- [stage:collision](#/record/stage%3Acollision)
- [module:solvers](#/record/module%3Asolvers)
- [topic:coupling](#/record/topic%3Acoupling)
- [topic:differentiable-simulation](#/record/topic%3Adifferentiable-simulation)
- [process:substeps](#/record/process%3Asubsteps)

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/solvers/index.html)。

## 固定版本原始出处

- [docs/solvers/index.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/solvers/index.rst#L1)
