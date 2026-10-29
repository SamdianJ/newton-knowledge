# 构建与预处理

配置构建期预处理，并检查 finalize 的派生结果。

输入：导入后的 builder。finalize 前配置几何、拓扑和 collision filter，显式完成 mesh approximation 与 solver 所需着色；对 VBD 等路径按示例调用 builder.color()。finalize 内还可能生成 deferred SDF、分配设备资源并验证/修正质量惯量，因此不能把 finalize 当作纯数据搬运。完成后检查 Model 实际数组与 warning，保存近似/SDF 参数和产物；增加迭代不能弥补漏掉的几何或错误过滤。

## 几何表示与前置条件

| 要模拟的对象 | 输入与准备 | 不应混淆的边界 |
|---|---|---|
| cloth/surface | 粒子、三角形、弯曲边；`add_cloth_mesh/grid` | 表面三角网格不自动成为tet体网格；VBD需要正确着色 |
| soft volume | 真正的顶点+tetra cells；`TetMesh.create_from_file`后交给体网格构建路径 | 该读取函数不对任意triangle mesh执行四面体化；体网格生成需先由适当工具完成 |
| rigid collision mesh | 原始mesh/BVH，或`ModelBuilder.approximate_meshes`生成的凸近似 | convex_hull填平凹腔；CoACD/V-HACD需依赖及失败策略，详见碰撞预检配方 |
| SDF collision representation | `Mesh.build_sdf`或ShapeConfig SDF配置；可由finalize执行deferred生成 | SDF是几何距离表示，不是tet离散材料，也不是启用所有solver支持的开关 |

tet导入要求见[TetMesh.create_from_file](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/geometry/types.py#L2132-L2139)与[tetra cells读取](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/geometry/types.py#L2198-L2208)。`add_soft_mesh(validate_mesh=True)`会检查反向或过小体积等单元，默认False，不能假设未显式开启时已验网格质量；参见[体网格验证入口](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/builder.py#L11540-L11587)。

## SDF烘焙与资源分配

`Mesh.build_sdf(target_voxel_size=...)`的voxel size优先于`max_resolution`，后者要求8的倍数。符号策略`auto`按watertight选择parity/winding，开放薄面可显式考虑normal，但这不使开放面自动满足hydroelastic体积前提。非单位缩放的hydroelastic形状要求scale-baked SDF；纹理SDF分配/生成路径要求CUDA，CPU-only环境不能把配置成功当烘焙成功。保存网格内容、scale、voxel、narrow band、padding和cache配置。

对于hydroelastic，SDF construction padding必须覆盖shape的margin+gap；外部预计算SDF也需声明原始construction_padding供验证。带SDF/hydro配置的mesh不能盲目再近似为不支持该配置的非mesh形状。依据：[SDF参数与符号/缩放策略](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/geometry/types.py#L848-L918)；[deferred SDF与CUDA检查](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/builder.py#L13764-L13816)；[近似与SDF配置限制](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/builder.py#L8804-L8824)；[SDF contact-band padding要求](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/collisions.rst#L1337-L1354)。

显式近似和着色在finalize前完成；finalize还生成部分派生资源并修正质量惯量，之后检查实际Model和warning。相关入口：[质量惯量](#/record/concept%3Amass-inertia)、[碰撞预检](#/record/recipe%3Acollision-preflight)、[可变形体数据路径](#/record/concept%3Adeformables)。本页没有新增网格转换或SDF物理实测。

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

## 相关知识

- [module:geometry](#/record/module%3Ageometry)
- [module:utils](#/record/module%3Autils)
- [concept:mass-inertia](#/record/concept%3Amass-inertia)
- [concept:deformables](#/record/concept%3Adeformables)
- [concept:collisions](#/record/concept%3Acollisions)

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/concepts/collisions.html)。

## 固定版本原始出处

- [docs/concepts/collisions.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/collisions.rst#L1)
- [docs/concepts/mass_inertia.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/mass_inertia.rst#L1)
- [newton/_src/geometry/types.py:2132](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/geometry/types.py#L2132-L2139)
- [newton/_src/geometry/types.py:2198](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/geometry/types.py#L2198-L2208)
- [newton/_src/sim/builder.py:11540](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/builder.py#L11540-L11587)
- [newton/_src/geometry/types.py:848](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/geometry/types.py#L848-L918)
- [newton/_src/sim/builder.py:13764](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/builder.py#L13764-L13816)
- [newton/_src/sim/builder.py:8804](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/builder.py#L8804-L8824)
- [docs/concepts/collisions.rst:1337](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/collisions.rst#L1337-L1354)
