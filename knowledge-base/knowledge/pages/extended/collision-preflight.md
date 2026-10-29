# 非凸网格近似与碰撞预检

## 机制与输入输出

先查看碰撞形状，再比较视觉网格。ModelBuilder.approximate_meshes 默认 method="convex_hull"；凸包会填平凹洞，不适合作为保留容器内腔的保证。

## 配置与诊断步骤

1. 需要非凸分解时显式选择 coacd/vhacd，并固定依赖、shape_indices 与 remeshing 参数。官方代码在缺依赖或失败且 raise_on_failure=False 时可回退 convex_hull 等后续方法。
2. 若回退不可接受，使用 raise_on_failure=True 并检查返回的实际形状集合与 warning。keep_visual_shapes 控制保留视觉形状，不能证明碰撞近似保真。
3. 核查每个 shape 的 collision/visibility 标记、world 分配与 add_shape_collision_filter_pair；碰撞过滤配对会移除候选，不能靠提高 iterations 恢复。
4. 用截面、接触记录和探针位置检查内腔与壁厚，再核查质量/惯量。预处理产物和参数要保存；本库没有替用户执行本次网格分解。
5. 接着按目标 solver 的 mesh 支持和导入转换规则确认最终使用的几何。

## 适用范围与证据

Newton 1.7.0 固定文档、公开 API 与源码说明；runtime_status=not_run。这里的任务验证只验证知识检索与配置推理证据，不是物理任务执行或参数 A/B。设备、后端和捕获限制按所选路径核对。

## 精确 API

- [newton.ModelBuilder.approximate_meshes](#/record/symbol%3Anewton.ModelBuilder.approximate_meshes)
- [newton.ModelBuilder.add_shape_collision_filter_pair](#/record/symbol%3Anewton.ModelBuilder.add_shape_collision_filter_pair)

## 相关知识

- [stage:preprocess](#/record/stage%3Apreprocess)
- [module:geometry](#/record/module%3Ageometry)
- [module:utils](#/record/module%3Autils)
- [concept:collisions](#/record/concept%3Acollisions)

## 固定出处

- [newton/_src/sim/builder.py:8712](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/builder.py#L8712)
- [newton/_src/sim/builder.py:2184](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/builder.py#L2184)
- [docs/concepts/collisions.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/collisions.rst#L1)
