# Worlds 与批量场景

一个 Model 中的 world 分组与选择。

## 机制与数据流

用 begin_world/end_world、add_world 或 replicate 建立独立 world，实体数组记录各自 world index；-1 为 global。*_world_start 有 world_count+2 项，global 实体可能分布在前后两段，不能只取一个连续 slice。

## 诊断与边界

Builder 可以构建异质 world，不代表全部 solver 或 ArticulationView 都支持异质批量。

通过 ModelBuilder.add_world / replicate 构建同质批量，检查 Model.*_world 与 *_world_start。ArticulationView 按 articulation label/index 创建视图，先读取选中对象的真实布局，再用 set_attribute(name,target,values,mask=...) 局部写入。

ArticulationView 的 mask 是 `(view.world_count,)` 或 `(view.world_count, count_per_world)`；solver.reset 的 world_mask 是 `(model.world_count+1,)`，最后一项选择 global world -1。两种掩码不可直接复用；global 实体还可能位于数组前后两段。

先按 mask 恢复公共 State 与 Control 的物理初态，再按后端要求 `solver.reset(state, world_mask=mask, flags=...)` 同步私有历史和缓存。SolverBase 默认 reset 仅校验掩码，是 no-op；不能宣称任何 solver.reset 都自动恢复全部初态。MuJoCo / VBD / Kamino 的具体缓存、global 行为和 backend 条件需读取对应 override；状态双缓冲也需一致处理。模型属性改动另走 notify_model_changed。

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

## 精确 API 入口

- [newton.ModelBuilder.replicate](#/record/symbol%3Anewton.ModelBuilder.replicate)
- [newton.selection.ArticulationView.set_attribute](#/record/symbol%3Anewton.selection.ArticulationView.set_attribute)

## 相关知识

- [module:selection](#/record/module%3Aselection)
- [topic:worlds-batching](#/record/topic%3Aworlds-batching)
- [recipe:worlds-reset](#/record/recipe%3Aworlds-reset)

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/concepts/worlds.html)。

## 固定版本原始出处

- [docs/concepts/worlds.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/worlds.rst#L1)
- [newton/_src/sim/builder.py:3292](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/builder.py#L3292)
- [newton/_src/utils/selection.py:1531](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/utils/selection.py#L1531)
