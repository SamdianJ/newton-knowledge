# 预处理与开发工具

资产与网格处理、开发辅助索引。

## 职责、输入与输出

utils 收录资产获取、remesh_mesh 网格重建、着色、惯量和其他辅助函数。首版以公开 __all__ 索引与函数源码为主；模型级凸分解的公开入口是 ModelBuilder.approximate_meshes，应在 finalize 前调用。

## 失败模式与限制

可达的 newton._src 路径属于实现，不是稳定公开导入。可选依赖与工具输出需要固定版本；本地知识服务不执行下载或分解。

## 模块公开导出索引

- [color_graph](#/record/symbol%3Anewton.utils.color_graph)
- [plot_graph](#/record/symbol%3Anewton.utils.plot_graph)
- [MeshAdjacency](#/record/symbol%3Anewton.utils.MeshAdjacency)
- [MeshAdjacencyData](#/record/symbol%3Anewton.utils.MeshAdjacencyData)
- [remesh_mesh](#/record/symbol%3Anewton.utils.remesh_mesh)
- [solidify_mesh](#/record/symbol%3Anewton.utils.solidify_mesh)
- [validate_tet_mesh](#/record/symbol%3Anewton.utils.validate_tet_mesh)
- [validate_triangle_mesh](#/record/symbol%3Anewton.utils.validate_triangle_mesh)
- [rasterize_mesh_to_heightfield](#/record/symbol%3Anewton.utils.rasterize_mesh_to_heightfield)
- [bourke_color_map](#/record/symbol%3Anewton.utils.bourke_color_map)
- [ColorSpace](#/record/symbol%3Anewton.utils.ColorSpace)
- [color_linear_to_srgb](#/record/symbol%3Anewton.utils.color_linear_to_srgb)
- [color_srgb_to_linear](#/record/symbol%3Anewton.utils.color_srgb_to_linear)
- [CableStiffness](#/record/symbol%3Anewton.utils.CableStiffness)
- [create_cable_stiffness_from_elastic_moduli](#/record/symbol%3Anewton.utils.create_cable_stiffness_from_elastic_moduli)
- [create_parallel_transport_cable_quaternions](#/record/symbol%3Anewton.utils.create_parallel_transport_cable_quaternions)
- [create_straight_cable_points](#/record/symbol%3Anewton.utils.create_straight_cable_points)
- [create_straight_cable_points_and_quaternions](#/record/symbol%3Anewton.utils.create_straight_cable_points_and_quaternions)
- [compute_world_offsets](#/record/symbol%3Anewton.utils.compute_world_offsets)
- [download_asset](#/record/symbol%3Anewton.utils.download_asset)
- [EventTracer](#/record/symbol%3Anewton.utils.EventTracer)
- [event_scope](#/record/symbol%3Anewton.utils.event_scope)
- [run_benchmark](#/record/symbol%3Anewton.utils.run_benchmark)
- [string_to_warp](#/record/symbol%3Anewton.utils.string_to_warp)
- [load_texture](#/record/symbol%3Anewton.utils.load_texture)
- [normalize_texture](#/record/symbol%3Anewton.utils.normalize_texture)

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/api/newton_utils.html)。

## 固定版本原始出处

- [newton/utils.py:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/utils.py#L1)
- [docs/api/newton_utils.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/api/newton_utils.rst#L1)
