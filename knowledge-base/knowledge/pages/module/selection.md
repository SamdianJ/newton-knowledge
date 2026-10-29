# 批量对象选择

ArticulationView 批量读取与掩码写入。

## 职责、输入与输出

ArticulationView 根据标签或索引选择 articulation，建立 view 与 Model 的索引映射，在 Model、State、Control、Observables 上读写受支持 frequency 的属性。set_attribute 支持 world 或 world×articulation 掩码。

## 失败模式与限制

选择 API 当前假设模型同质。选择掩码形状与 solver.reset 的 world_count+1 掩码不同；raw contact 行没有稳定唯一的 articulation 归属，不能直接通过 view 过滤。

## 模块公开导出索引

- [ArticulationView](#/record/symbol%3Anewton.selection.ArticulationView)

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

## 精确 API 入口

- [newton.selection.ArticulationView](#/record/symbol%3Anewton.selection.ArticulationView)
- [newton.selection.ArticulationView.set_attribute](#/record/symbol%3Anewton.selection.ArticulationView.set_attribute)

## 相关知识

- [concept:worlds](#/record/concept%3Aworlds)
- [topic:worlds-batching](#/record/topic%3Aworlds-batching)
- [recipe:worlds-reset](#/record/recipe%3Aworlds-reset)

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/api/newton_selection.html)。

## 固定版本原始出处

- [newton/selection.py:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/selection.py#L1)
- [newton/_src/utils/selection.py:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/utils/selection.py#L1)
- [docs/api/newton_selection.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/api/newton_selection.rst#L1)
- [newton/_src/utils/selection.py:686](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/utils/selection.py#L686)
- [newton/_src/utils/selection.py:1531](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/utils/selection.py#L1531)
