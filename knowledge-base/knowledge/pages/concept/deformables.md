# 可变形体与离散化

curve / surface / volume 的离散化与材料归属。

## 机制与数据流

Rod-backed curve 记录 bodies/joints；三角 surface 记录 particles/triangles/bending edges；四面体 volume 记录 particles/tets。add_cloth_mesh/grid 与 add_soft_mesh/grid 等分别写入对象范围。

## 诊断与边界

网格分辨率、材料数组、质量和着色都影响响应。每个 solver 消费的材料字段不同，参数记录与网格建模应分别检查。



## 表面、体积与碰撞表示

三角surface通过面内材料和bending描述薄片；tet volume通过体单元描述体积材料。体网格必须有真实tetra cells，表面网格文件不能直接冒充体网格。Rod curve使用body/joint离散，与粒子三角网格的检测/材料路径不同。输入质量与SDF准备见[预处理](#/record/stage%3Apreprocess)。

## 三条软碰撞数据路径

| 对象对 | 检测与配置 | 输出及消费 |
|---|---|---|
| particle–shape | 公共pipeline的粒子查询，使用particle radius、shape margin与soft_contact_gap | 普通soft-contact数组：soft_contact_indices=(p,-1,-1)；由支持粒子接触的solver消费 |
| full-surface edge/face–shape | enable_rigid_soft_full_surface_contact补足顶点间区域对rigid SDF的检测；mesh/convex需配置SDF，解析原语可用解析SDF | 与particle contact共用soft-contact数组和soft_contact_count；edge/face记录通过indices+barycentric区分。v1.7消费限VBD指定路径；particle-only guard拒绝，不是unknown |
| tri-mesh self-contact | TriMeshCollisionDetector产生vertex–triangle (VT)与edge–edge (EE)候选；margin是交互距离、gap是额外检测距离 | 独立的soft_self_contact_data / TriMeshCollisionInfo容器（存储属性仍为experimental），不计入普通soft_contact_count，也不包含在VBD CONTACT_F输出中 |

full-surface edge记录indices=(v0,v1,-1)，face记录=(v0,v1,v2)，结合barycentric对非负索引求接触点。兼容字段soft_contact_particle在edge/face为-1，这不是漏检，也不能将-1用于粒子数组访问。依据：[soft-contact结构与兼容字段](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/contacts.py#L386-L421)；[full-surface刚体SDF与消费前提](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/collide.py#L1327-L1347)。

公共self-contact流程是`pipeline.init_soft_self_contact(...)` → `contacts=pipeline.contacts()` → `pipeline.collide(state,contacts,soft_self_contact=True)`。该接口只检测，不自动赋予任意solver自接触响应。VBD拥有pipeline时按solver参数配置并借用该buffer；非owned路径创建私有detector，因此solver.contacts可能为None但仍有自接触。self-contact配置要求model有triangles；拓扑ring、rest_shape_exclusion_radius和外部VT/EE过滤决定哪些候选被排除，过滤可以排除静止时本就接近的seam/层叠区域，也可能排除用户本想检测的对。

VT/EE每顶点/边buffer是独立容量；raw row count可能超过容量，使用TriMeshCollisionInfo的钳制accessor并检查溢出，不能拿普通soft_contact_count诊断self-contact有无。已有self_contact实验的旧contacts列没有采VT/EE，所以零列不否定其高度轨迹；它也不能证明候选容量充分。依据：[公共self-contact配置与容器](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/collide.py#L2068-L2139)；[VBD owned与私有detector](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L1064-L1082)；[自接触计数accessor](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/geometry/tri_mesh_collision.py#L31-L90)；[experimental容器边界](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/contacts.py#L464-L472)。

DAT只限制被候选覆盖的运动；初始合法性、预算、容量和调度仍是前提，同时启用两种DAT需等价调度。详见[VBD DAT配方](#/record/recipe%3Avbd-dat-preconditions)。检测、几何保护和接触响应分开核查；本页没有把最小自接触/full-surface实验提升为复杂网格或全部solver已验证。

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/concepts/deformable_objects.html)。

## 固定版本原始出处

- [docs/concepts/deformable_objects.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/deformable_objects.rst#L1)
- [newton/_src/sim/contacts.py:386](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/contacts.py#L386-L421)
- [newton/_src/sim/collide.py:1327](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/collide.py#L1327-L1347)
- [newton/_src/sim/collide.py:2068](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/collide.py#L2068-L2139)
- [newton/_src/solvers/vbd/solver_vbd.py:1064](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/solvers/vbd/solver_vbd.py#L1064-L1082)
- [newton/_src/geometry/tri_mesh_collision.py:31](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/geometry/tri_mesh_collision.py#L31-L90)
- [newton/_src/sim/contacts.py:464](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/contacts.py#L464-L472)
