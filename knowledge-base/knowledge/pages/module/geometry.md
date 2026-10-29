# 几何与碰撞工具

几何表示、碰撞检测数据与预处理。

## 职责、输入与输出

newton.Mesh 等根模块几何类型用于建模；geometry 模块提供 BroadPhase、NarrowPhase、SDF 与形状碰撞工具。视觉网格不自动等同于碰撞表示；构建阶段检查尺度、拓扑、法线、形状类型、SDF 和接触支持，再交给 CollisionPipeline。

## 失败模式与限制

模型级凸分解使用 ModelBuilder.approximate_meshes(method="coacd"/"vhacd")；utils.remesh_mesh 是网格重建工具，不提供这两个分解方法。碰撞过滤决定候选配对，增加 solver iterations 无法修复漏检。

## 模块公开导出索引

- [BroadPhaseAllPairs](#/record/symbol%3Anewton.geometry.BroadPhaseAllPairs)
- [BroadPhaseExplicit](#/record/symbol%3Anewton.geometry.BroadPhaseExplicit)
- [BroadPhaseSAP](#/record/symbol%3Anewton.geometry.BroadPhaseSAP)
- [HydroelasticSDF](#/record/symbol%3Anewton.geometry.HydroelasticSDF)
- [NarrowPhase](#/record/symbol%3Anewton.geometry.NarrowPhase)
- [ParticleSurface](#/record/symbol%3Anewton.geometry.ParticleSurface)
- [TriMeshCollisionInfo](#/record/symbol%3Anewton.geometry.TriMeshCollisionInfo)
- [collide_box_box](#/record/symbol%3Anewton.geometry.collide_box_box)
- [collide_capsule_box](#/record/symbol%3Anewton.geometry.collide_capsule_box)
- [collide_capsule_capsule](#/record/symbol%3Anewton.geometry.collide_capsule_capsule)
- [collide_plane_box](#/record/symbol%3Anewton.geometry.collide_plane_box)
- [collide_plane_capsule](#/record/symbol%3Anewton.geometry.collide_plane_capsule)
- [collide_plane_cylinder](#/record/symbol%3Anewton.geometry.collide_plane_cylinder)
- [collide_plane_ellipsoid](#/record/symbol%3Anewton.geometry.collide_plane_ellipsoid)
- [collide_plane_sphere](#/record/symbol%3Anewton.geometry.collide_plane_sphere)
- [collide_sphere_box](#/record/symbol%3Anewton.geometry.collide_sphere_box)
- [collide_sphere_capsule](#/record/symbol%3Anewton.geometry.collide_sphere_capsule)
- [collide_sphere_cylinder](#/record/symbol%3Anewton.geometry.collide_sphere_cylinder)
- [collide_sphere_sphere](#/record/symbol%3Anewton.geometry.collide_sphere_sphere)
- [compute_inertia_shape](#/record/symbol%3Anewton.geometry.compute_inertia_shape)
- [compute_offset_mesh](#/record/symbol%3Anewton.geometry.compute_offset_mesh)
- [create_empty_sdf_data](#/record/symbol%3Anewton.geometry.create_empty_sdf_data)
- [extract_particle_surface](#/record/symbol%3Anewton.geometry.extract_particle_surface)
- [sdf_box](#/record/symbol%3Anewton.geometry.sdf_box)
- [sdf_capsule](#/record/symbol%3Anewton.geometry.sdf_capsule)
- [sdf_cone](#/record/symbol%3Anewton.geometry.sdf_cone)
- [sdf_cylinder](#/record/symbol%3Anewton.geometry.sdf_cylinder)
- [sdf_mesh](#/record/symbol%3Anewton.geometry.sdf_mesh)
- [sdf_plane](#/record/symbol%3Anewton.geometry.sdf_plane)
- [sdf_sphere](#/record/symbol%3Anewton.geometry.sdf_sphere)
- [transform_inertia](#/record/symbol%3Anewton.geometry.transform_inertia)

## 选择路线

建模先区分surface/tet与rigid碰撞表示，再决定凸近似、BVH或SDF。概念与固定出处分别见[几何/SDF/tet准备](#/record/stage%3Apreprocess)、[刚体碰撞表示与算法](#/record/concept%3Acollisions)、[三条软碰撞数据路径](#/record/concept%3Adeformables)。`ModelBuilder.approximate_meshes`负责模型级凸分解，`newton.utils.remesh_mesh`负责其声明方法范围内的网格重建；二者不是同一公开API。

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

## 精确 API 入口

- [newton.Mesh](#/record/symbol%3Anewton.Mesh)
- [newton.geometry.NarrowPhase](#/record/symbol%3Anewton.geometry.NarrowPhase)

## 相关知识

- [concept:collisions](#/record/concept%3Acollisions)
- [stage:preprocess](#/record/stage%3Apreprocess)

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/concepts/collisions.html)。

## 固定版本原始出处

- [newton/geometry.py:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/geometry.py#L1)
- [docs/concepts/collisions.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/collisions.rst#L1)
- [docs/api/newton_geometry.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/api/newton_geometry.rst#L1)
- [newton/_src/sim/builder.py:8712](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/builder.py#L8712-L8737)
- [newton/_src/geometry/utils.py:947](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/geometry/utils.py#L947-L974)
- [newton/_src/geometry/types.py:133](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/geometry/types.py#L133)
- [newton/_src/geometry/narrow_phase.py:2258](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/geometry/narrow_phase.py#L2258)
