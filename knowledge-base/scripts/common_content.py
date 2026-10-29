"""Source-grounded conceptual additions for the fixed Newton 1.7.0 release.

These are explanations and navigation, not additional physical experiments.
author_platform adds them to existing records before rendering/indexing.
"""

from plan_p0 import COMMIT


def source(label, path, line, end=None):
    anchor = f"L{line}" + (f"-L{end}" if end is not None else "")
    return f"[{label}](https://github.com/newton-physics/newton/blob/{COMMIT}/{path}#{anchor})"


COMMON_DETAILS = {
    "concept:articulations": {
        "body": f"""## 树、闭环与耦合关系

| 概念 | 如何表达 | 关键边界 |
|---|---|---|
| articulation tree | `add_joint_*` 建关节，树关节列表交给 `add_articulation` | 每个body至多一个树父关节；FK、IK和ArticulationView沿树遍历 |
| loop-closing joint | 另建连接两个已由树可达body的关节，但不把它加入articulation的joint_list | 它不是orphan joint，正常通过finalize；不额外出现在树的FK/IK坐标中。maximal solver按所支持关节类型求约束；MuJoCo编译为受限双边耦合；Featherstone不执行该闭环约束 |
| joint-owned mimic | `set_joint_mimic(follower, reference, coeffs=(offset, multiplier))` | 两端位置/速度维度相同，限PRISMATIC/REVOLUTE/D6；不能建立mimic链。四元数关节不能逐分量做这类仿射关系 |
| equality | MuJoCo专属约束通过注册的`mujoco:equality_constraint_*`自定义属性构建 | 不是所有solver共享的独立核心构件；不能因能写入字段就推断VBD等会消费 |
| tendon | fixed/spatial tendon通过MuJoCo命名空间的自定义属性与MJCF/USD导入保留 | core没有通用`add_tendon` API；转换和所支持的wrap表示见MuJoCo专区 |

独立设定初始或复位关节状态后，需要body姿态体现mimic时，先`eval_mimic(model,state)`，再`eval_fk(model,state.joint_q,state.joint_qd,state)`。支持mimic的solver在step内自行执行其约束；不要每步再投影一次。若maximal solver只更新body状态，要读求解后的关节坐标，应先`eval_ik`，不能对陈旧joint数组直接eval_mimic。

入口：{source('mimic维度、顺序和solver差异', 'docs/concepts/articulations.rst', 141, 237)}；{source('闭环、orphan和各后端处理', 'docs/concepts/articulations.rst', 1085, 1193)}；{source('MuJoCo equality与tendon authoring', 'docs/solvers/mujoco.rst', 411, 550)}。

## 谁负责写状态

| 身份 | 状态更新责任 | 接触与建模限制 |
|---|---|---|
| static | 世界附着shape或固定世界根，位置不积分 | 可以作为障碍或支撑 |
| kinematic | 用户规定位置和一致的速度；外力不驱动自身运动 | `is_kinematic=True`只允许root link/body；非root会在articulation构造时报错。可以推动dynamic物体 |
| dynamic | solver由力、关节和接触推进 | 必须建立适当质量/惯量，不能把零质量当作通用kinematic开关 |

广义坐标路径写`joint_q/joint_qd`，再用FK更新碰撞需要的body状态；最大坐标路径写`body_q/body_qd`。速度要与规定轨迹一致，FREE/BALL的四元数用流形一致的积分，不能直接把qd加到q。MuJoCo/Featherstone与XPBD/VBD/SemiImplicit的内部处理不同；例如SemiImplicit保留规定状态，但接触内没有同样清零逆质量/惯量，接触可能更软。Kamino专属FK与驱动约束见其专区，不从这张概念表推导所有后端支持。

依据：{source('static/kinematic/dynamic与状态写入', 'docs/concepts/articulations.rst', 292, 420)}。
""",
        "refs": [
            ("docs/concepts/articulations.rst", 141, 237),
            ("docs/concepts/articulations.rst", 292, 420),
            ("docs/concepts/articulations.rst", 1085, 1193),
            ("docs/solvers/mujoco.rst", 411, 550),
        ],
    },
    "stage:asset_import": {
        "body": f"""## 按资产语义选择导入入口

| 格式与入口 | 要保留的语义 | 导入后必须核查 |
|---|---|---|
| URDF：`ModelBuilder.add_urdf` | 机器人link/joint、碰撞与视觉几何、inertial | 显式inertial和几何推断的选择；`joint_damping_mode`默认None在1.7仍按drive映射并告警，显式`passive`写joint_damping，XPBD/VBD不消费该被动关节阻尼 |
| MJCF：`ModelBuilder.add_mjcf` | MuJoCo模型、compiler/default配置及支持的命名空间属性 | `<inertial>`和`compiler inertiafromgeom`共同决定质量来源；检查导出到目标solver后的关节、equality/tendon、几何和控制语义，不把导入成功当作任意solver支持 |
| USD：`ModelBuilder.add_usd` | 场景层级、UsdPhysics、受支持的Newton/扩展schema | 默认只启用Newton resolver；显式设resolver优先级，核对stage单位、排除articulation的loop joint以及deformable支持子集 |

URDF阻尼依据：{source('import_urdf参数与兼容默认', 'newton/_src/utils/import_urdf.py', 187, 203)}。MJCF质量来源：{source('import_mjcf inertiafromgeom与显式惯量', 'newton/_src/utils/import_mjcf.py', 2363, 2425)}。三种格式的质量规则由{source('质量导入规则', 'docs/concepts/mass_inertia.rst', 122, 160)}统一导航。

操作顺序：保存原资产与配置 → 选择格式/solver → 明确单位和轴向 → 检查解析warning与实际body/joint/shape数量 → 查看视觉/碰撞表示 → 核对质量与控制 → 再finalize并检查结果。USD resolver和单位限制见[USD解析](#/record/concept%3Ausd-parsing)，几何准备见[预处理](#/record/stage%3Apreprocess)。这里未新增资产导入端到端实测。
""",
        "refs": [
            ("newton/_src/utils/import_urdf.py", 187, 203),
            ("newton/_src/utils/import_mjcf.py", 2363, 2425),
            ("docs/concepts/mass_inertia.rst", 122, 160),
        ],
    },
    "concept:usd-parsing": {
        "body": f"""## Resolver优先级与回退

`schema_resolvers=None`时，实际列表仅为`[SchemaResolverNewton()]`。同一属性按三层解析：按列表优先级找第一个authored值；没有时用该属性的importer default；仍没有才使用resolver映射里近似的schema default。列表越靠前优先级越高；资产带PhysX/MJC命名空间不等于它会自动完整转换。

需要以PhysX authored值优先时，可以明确配置：

```python
from newton.usd import SchemaResolverNewton, SchemaResolverPhysx
builder.add_usd(
    source="asset.usda",
    schema_resolvers=[SchemaResolverPhysx(), SchemaResolverNewton()],
)
```

这只是配置示例，未加载上述占位资产。改变resolver顺序是语义干预，应记录解析后的属性，而不只保存文件名。依据：{source('实际默认列表', 'newton/_src/utils/import_usd.py', 474, 475)}；{source('三层回退与顺序示例', 'docs/concepts/usd_parsing.rst', 645, 693)}。

## 单位与可变形体边界

v1.7.0的legacy rigid/collider导入仍要求`metersPerUnit=1`与`kilogramsPerUnit=1`，不能承诺所有USD路径自动转成SI。粒子路径会转换单位；混合rigid/particle资产可能走不同路径，因此应先把混合stage规范为单位元数据1，并检查warning。依据：{source('非单位及混合路径警告', 'newton/_src/utils/import_usd.py', 587, 614)}。

AOUSD deformable仅支持文档列明的子集；Omni/PhysX原生deformable schema不由resolver系统全面翻译。先识别curve/surface/volume的离散化，再核查当前importer能读取的具体schema；把被保留的solver属性与实际被solver消费的属性分开记录。依据：{source('deformable schema支持边界', 'docs/concepts/usd_parsing.rst', 145, 156)}。质量优先级和密度回退另见[质量与惯量](#/record/concept%3Amass-inertia)。
""",
        "refs": [
            ("newton/_src/utils/import_usd.py", 474, 475),
            ("docs/concepts/usd_parsing.rst", 645, 693),
            ("newton/_src/utils/import_usd.py", 587, 614),
            ("docs/concepts/usd_parsing.rst", 145, 156),
        ],
    },
    "concept:mass-inertia": {
        "body": f"""## 质量来源不是简单的二选一

| 构建方式 | 实际规则 | 检查点 |
|---|---|---|
| 程序化`add_link(mass,inertia,com)` | 给出body初始质量属性；之后添加正密度shape会继续累加 | 显式mass默认不阻止shape贡献；避免不知情地重复计质量 |
| `lock_inertia=True` | 后续shape不再修改该body的mass、COM或inertia | 用于保护手工质量属性；不是只锁一个惯量矩阵字段 |
| shape密度推断 | 质量相加、COM按质量加权，原惯量和shape惯量平移到新COM后相加 | plane/heightfield不贡献质量；site强制density=0 |
| 文件导入 | 显式inertial通常优先，缺失时由几何推断；URDF/MJCF可用ignore_inertial_definitions改策略 | 仍须服从格式特有compiler/属性规则；视觉shape默认不贡献，但被提升为collider后可能贡献 |

例如先设body质量2kg，再添加正密度球形状，未锁定时最终质量是2kg加球的质量，而非仍为2kg。`com`是相对body origin的偏移，`inertia`是关于COM的张量；不要把模型惯量当world-frame张量。规则与例子见{source('质量指定、累加与lock', 'docs/concepts/mass_inertia.rst', 44, 160)}，执行入口见{source('shape质量累加', 'newton/_src/sim/builder.py', 11704, 11728)}。

## finalize会检查，也可能修改

`balance_inertia=True`默认修正主惯量三角不等式；可选`bound_mass`和`bound_inertia`设置下界。验证还处理负质量、零质量与非零惯量、对称性和负特征值。开发时设`builder.validate_inertia_detailed=True`获得每body警告，并比较finalize前后的实际质量/惯量。`collapse_fixed_joints`的质量合并发生在这些验证之前。

因此应保存导入/密度/lock/验证配置与最终`Model.body_mass/body_com/body_inertia`，再核对solver转换。不要以“没有异常”推断数值未变，也不要用零质量替代`is_kinematic=True`。依据：{source('验证与修正设置', 'docs/concepts/mass_inertia.rst', 163, 218)}；{source('finalize实际处理', 'newton/_src/sim/builder.py', 14309, 14367)}。
""",
        "refs": [
            ("docs/concepts/mass_inertia.rst", 44, 160),
            ("newton/_src/sim/builder.py", 11704, 11728),
            ("docs/concepts/mass_inertia.rst", 163, 218),
            ("newton/_src/sim/builder.py", 14309, 14367),
        ],
    },
    "stage:preprocess": {
        "body": f"""## 几何表示与前置条件

| 要模拟的对象 | 输入与准备 | 不应混淆的边界 |
|---|---|---|
| cloth/surface | 粒子、三角形、弯曲边；`add_cloth_mesh/grid` | 表面三角网格不自动成为tet体网格；VBD需要正确着色 |
| soft volume | 真正的顶点+tetra cells；`TetMesh.create_from_file`后交给体网格构建路径 | 该读取函数不对任意triangle mesh执行四面体化；体网格生成需先由适当工具完成 |
| rigid collision mesh | 原始mesh/BVH，或`ModelBuilder.approximate_meshes`生成的凸近似 | convex_hull填平凹腔；CoACD/V-HACD需依赖及失败策略，详见碰撞预检配方 |
| SDF collision representation | `Mesh.build_sdf`或ShapeConfig SDF配置；可由finalize执行deferred生成 | SDF是几何距离表示，不是tet离散材料，也不是启用所有solver支持的开关 |

tet导入要求见{source('TetMesh.create_from_file', 'newton/_src/geometry/types.py', 2132, 2139)}与{source('tetra cells读取', 'newton/_src/geometry/types.py', 2198, 2208)}。`add_soft_mesh(validate_mesh=True)`会检查反向或过小体积等单元，默认False，不能假设未显式开启时已验网格质量；参见{source('体网格验证入口', 'newton/_src/sim/builder.py', 11540, 11587)}。

## SDF烘焙与资源分配

`Mesh.build_sdf(target_voxel_size=...)`的voxel size优先于`max_resolution`，后者要求8的倍数。符号策略`auto`按watertight选择parity/winding，开放薄面可显式考虑normal，但这不使开放面自动满足hydroelastic体积前提。非单位缩放的hydroelastic形状要求scale-baked SDF；纹理SDF分配/生成路径要求CUDA，CPU-only环境不能把配置成功当烘焙成功。保存网格内容、scale、voxel、narrow band、padding和cache配置。

对于hydroelastic，SDF construction padding必须覆盖shape的margin+gap；外部预计算SDF也需声明原始construction_padding供验证。带SDF/hydro配置的mesh不能盲目再近似为不支持该配置的非mesh形状。依据：{source('SDF参数与符号/缩放策略', 'newton/_src/geometry/types.py', 848, 918)}；{source('deferred SDF与CUDA检查', 'newton/_src/sim/builder.py', 13764, 13816)}；{source('近似与SDF配置限制', 'newton/_src/sim/builder.py', 8804, 8824)}；{source('SDF contact-band padding要求', 'docs/concepts/collisions.rst', 1337, 1354)}。

显式近似和着色在finalize前完成；finalize还生成部分派生资源并修正质量惯量，之后检查实际Model和warning。相关入口：[质量惯量](#/record/concept%3Amass-inertia)、[碰撞预检](#/record/recipe%3Acollision-preflight)、[可变形体数据路径](#/record/concept%3Adeformables)。本页没有新增网格转换或SDF物理实测。
""",
        "refs": [
            ("newton/_src/geometry/types.py", 2132, 2139),
            ("newton/_src/geometry/types.py", 2198, 2208),
            ("newton/_src/sim/builder.py", 11540, 11587),
            ("newton/_src/geometry/types.py", 848, 918),
            ("newton/_src/sim/builder.py", 13764, 13816),
            ("newton/_src/sim/builder.py", 8804, 8824),
            ("docs/concepts/collisions.rst", 1337, 1354),
        ],
    },
    "concept:collisions": {
        "body": f"""## 刚体碰撞：先选表示，再理解算法

下面描述Newton公共CollisionPipeline；native MuJoCo或MuJoCo Warp自带碰撞器有自己的支持与过滤规则，不能自动套用。

| 表示/阶段 | 核心工作 | 主要限制与选择 |
|---|---|---|
| broad phase | AABB剔除不相交候选 | 默认`explicit`使用预计算shape pairs；`nxn`全配对适合小场景；`sap`用空间排序削减候选。选择算法不改变被过滤掉的配对 |
| primitive/convex narrow phase | support mapping上的MPR处理穿透，GJK处理分离距离 | 不能把convex hull当作保留凹腔；不是EPA求穿透深度 |
| 无预计算SDF的triangle mesh | live BVH找到附近三角形/表面，产生距离查询接触 | 复杂网格查询成本较高；三角形CCW法线与背面剔除影响是否检出；此路径不提供hydroelastic |
| 预计算SDF | 网格距离查询及可选接触缩减 | 几何近似精度取决于SDF配置；烘焙/scale/padding在预处理阶段核对 |
| hydroelastic | 双侧SDF生成分布接触面积并缩减代表点 | 两侧都要is_hydroelastic=True和SDF；限有体积表示，非单位scale须烘焙；不是刚柔full-surface开关 |

依据：{source('几何表示与路由', 'docs/concepts/collisions.rst', 31, 80)}；{source('broad-phase选择', 'docs/concepts/collisions.rst', 734, 780)}；{source('MPR/GJK与mesh/BVH', 'docs/concepts/collisions.rst', 991, 1068)}；{source('hydroelastic前提', 'docs/concepts/collisions.rst', 1838, 1880)}。

## 过滤先于求解

不同非负world不相撞，global world=-1可与各world配对。collision_group=0关闭；正组只与同正组或任意负组相撞；负组与正/负组相撞，但同一个负组互不相撞。还要检查shape的collision flag、同body/static-static的固有排除、显式`add_shape_collision_filter_pair`以及导入时self-collision和默认parent-child过滤。过滤丢掉的是候选，增加solver迭代无效。依据：{source('world/group过滤', 'docs/concepts/collisions.rst', 479, 605)}与{source('固有排除和显式配对', 'docs/concepts/collisions.rst', 665, 704)}。

## margin决定接触面，gap决定何时检测

普通刚体对的真实表面距离为s，pair margin为m=margin_a+margin_b，pair gap为g=gap_a+gap_b。接触空间距离d=s-m，生成条件d<=g；AABB按各自margin+gap扩张。gap不直接移动接触面，增大margin会改变有效接触面的位置。solver的有限柔顺压入、求解误差和初始相交仍须另查，不能由该几何条件推出实际必无穿透。依据：{source('margin/gap公式', 'docs/concepts/collisions.rst', 1291, 1319)}。

opt-in `speculative_contact_gap_max`按接触点相对法向闭合速度扩展检测gap，`collide(...,dt=...)`的dt是到下一次碰撞更新的时间，包含被跳过的solver子步。它保留当前分离位置的候选，不计算time-of-impact、不把物体推进到撞击点；只适用于刚体非hydroelastic路径，不能当通用CCD或DAT。依据：{source('speculative admission与dt', 'docs/concepts/collisions.rst', 1382, 1428)}。

## 接触数据、缩减与历史

rigid_contact_point0/1是各body局部坐标点，normal是world-frame、从shape A指向B。shape id、margin/offset与采样state一起定义几何，不能只用body位置重建作用点。raw contact count在溢出时可超过capacity，存储访问须钳制并单独检查overflow；中间triangle-pair/reduction缓冲也可能先丢候选。CONTACT_F需要解析容量后绑定同一Contacts，冻结后扩容要新Model。

mesh/SDF/hydroelastic可能生成很多原始接触，默认reduction按法向、空间分布与深度选代表点；缩减不是求解器迭代预算。deterministic模式通过确定性选择/排序（hydro还需确定性聚合）稳定接触顺序，不能单独保证整个solver跨设备确定。matching默认disabled；latest保留本帧几何并给出匹配索引；experimental sticky在条件满足时复用上一帧几何，非disabled模式隐含deterministic。episode reset同时检查pipeline匹配历史与solver历史。

依据：{source('接触几何坐标', 'docs/concepts/collisions.rst', 97, 119)}；{source('contact reduction', 'docs/concepts/collisions.rst', 1184, 1244)}；{source('deterministic与matching语义', 'docs/concepts/collisions.rst', 2167, 2270)}。容量故障处理见[接触容量诊断](#/record/recipe%3Acontact-capacity-diagnosis)，三种软碰撞容器见[可变形体](#/record/concept%3Adeformables)。
""",
        "refs": [
            ("docs/concepts/collisions.rst", 31, 80),
            ("docs/concepts/collisions.rst", 734, 780),
            ("docs/concepts/collisions.rst", 991, 1068),
            ("docs/concepts/collisions.rst", 1838, 1880),
            ("docs/concepts/collisions.rst", 479, 605),
            ("docs/concepts/collisions.rst", 665, 704),
            ("docs/concepts/collisions.rst", 1291, 1319),
            ("docs/concepts/collisions.rst", 1382, 1428),
            ("docs/concepts/collisions.rst", 97, 119),
            ("docs/concepts/collisions.rst", 1184, 1244),
            ("docs/concepts/collisions.rst", 2167, 2270),
            ("newton/_src/sim/collide.py", 142, 223),
            ("newton/_src/sim/model.py", 1966, 1975),
        ],
    },
    "concept:deformables": {
        "body": f"""## 表面、体积与碰撞表示

三角surface通过面内材料和bending描述薄片；tet volume通过体单元描述体积材料。体网格必须有真实tetra cells，表面网格文件不能直接冒充体网格。Rod curve使用body/joint离散，与粒子三角网格的检测/材料路径不同。输入质量与SDF准备见[预处理](#/record/stage%3Apreprocess)。

## 三条软碰撞数据路径

| 对象对 | 检测与配置 | 输出及消费 |
|---|---|---|
| particle–shape | 公共pipeline的粒子查询，使用particle radius、shape margin与soft_contact_gap | 普通soft-contact数组：soft_contact_indices=(p,-1,-1)；由支持粒子接触的solver消费 |
| full-surface edge/face–shape | enable_rigid_soft_full_surface_contact补足顶点间区域对rigid SDF的检测；mesh/convex需配置SDF，解析原语可用解析SDF | 与particle contact共用soft-contact数组和soft_contact_count；edge/face记录通过indices+barycentric区分。v1.7消费限VBD指定路径；particle-only guard拒绝，不是unknown |
| tri-mesh self-contact | TriMeshCollisionDetector产生vertex–triangle (VT)与edge–edge (EE)候选；margin是交互距离、gap是额外检测距离 | 独立的soft_self_contact_data / TriMeshCollisionInfo容器（存储属性仍为experimental），不计入普通soft_contact_count，也不包含在VBD CONTACT_F输出中 |

full-surface edge记录indices=(v0,v1,-1)，face记录=(v0,v1,v2)，结合barycentric对非负索引求接触点。兼容字段soft_contact_particle在edge/face为-1，这不是漏检，也不能将-1用于粒子数组访问。依据：{source('soft-contact结构与兼容字段', 'newton/_src/sim/contacts.py', 386, 421)}；{source('full-surface刚体SDF与消费前提', 'newton/_src/sim/collide.py', 1327, 1347)}。

公共self-contact流程是`pipeline.init_soft_self_contact(...)` → `contacts=pipeline.contacts()` → `pipeline.collide(state,contacts,soft_self_contact=True)`。该接口只检测，不自动赋予任意solver自接触响应。VBD拥有pipeline时按solver参数配置并借用该buffer；非owned路径创建私有detector，因此solver.contacts可能为None但仍有自接触。self-contact配置要求model有triangles；拓扑ring、rest_shape_exclusion_radius和外部VT/EE过滤决定哪些候选被排除，过滤可以排除静止时本就接近的seam/层叠区域，也可能排除用户本想检测的对。

VT/EE每顶点/边buffer是独立容量；raw row count可能超过容量，使用TriMeshCollisionInfo的钳制accessor并检查溢出，不能拿普通soft_contact_count诊断self-contact有无。已有self_contact实验的旧contacts列没有采VT/EE，所以零列不否定其高度轨迹；它也不能证明候选容量充分。依据：{source('公共self-contact配置与容器', 'newton/_src/sim/collide.py', 2068, 2139)}；{source('VBD owned与私有detector', 'newton/_src/solvers/vbd/solver_vbd.py', 1064, 1082)}；{source('自接触计数accessor', 'newton/_src/geometry/tri_mesh_collision.py', 31, 90)}；{source('experimental容器边界', 'newton/_src/sim/contacts.py', 464, 472)}。

DAT只限制被候选覆盖的运动；初始合法性、预算、容量和调度仍是前提，同时启用两种DAT需等价调度。详见[VBD DAT配方](#/record/recipe%3Avbd-dat-preconditions)。检测、几何保护和接触响应分开核查；本页没有把最小自接触/full-surface实验提升为复杂网格或全部solver已验证。
""",
        "refs": [
            ("newton/_src/sim/contacts.py", 386, 421),
            ("newton/_src/sim/collide.py", 1327, 1347),
            ("newton/_src/sim/collide.py", 2068, 2139),
            ("newton/_src/solvers/vbd/solver_vbd.py", 1064, 1082),
            ("newton/_src/geometry/tri_mesh_collision.py", 31, 90),
            ("newton/_src/sim/contacts.py", 464, 472),
        ],
    },
    "module:geometry": {
        "body": """## 选择路线

建模先区分surface/tet与rigid碰撞表示，再决定凸近似、BVH或SDF。概念与固定出处分别见[几何/SDF/tet准备](#/record/stage%3Apreprocess)、[刚体碰撞表示与算法](#/record/concept%3Acollisions)、[三条软碰撞数据路径](#/record/concept%3Adeformables)。`ModelBuilder.approximate_meshes`负责模型级凸分解，`newton.utils.remesh_mesh`负责其声明方法范围内的网格重建；二者不是同一公开API。
""",
        "refs": [
            ("newton/_src/sim/builder.py", 8712, 8737),
            ("newton/_src/geometry/utils.py", 947, 974),
        ],
    },
    "module:usd": {
        "body": """## 从导入接口进入语义检查

`add_usd`默认仅Newton resolver；PhysX/MJC来源需要显式配置解析优先级。当前版本的legacy rigid/collider与particle单位转换路径不同，不应假定所有USD内容自动按stage元数据转SI。详见[resolver、单位与deformable支持](#/record/concept%3Ausd-parsing)；与URDF/MJCF的选择和质量语义比较见[资产导入](#/record/stage%3Aasset_import)。
""",
        "refs": [
            ("newton/_src/utils/import_usd.py", 474, 475),
            ("newton/_src/utils/import_usd.py", 587, 614),
        ],
    },
    "concept:conventions": {
        "body": f"""## 最小布局速查

| 数组 | 分量顺序 | 表达参考系 / 参考点 |
|---|---|---|
| body_q | 位置XYZ + 四元数XYZW | body origin的world姿态 |
| body_qd | 线速度3 + 角速度3 | world / COM |
| body_f | 力3 + 力矩3 | world / COM |
| FREE/DISTANCE joint_qd | child线速度3 + 角速度3 | joint parent frame / child COM |
| FREE/DISTANCE joint_f | 力3 + 力矩3 | world / child COM |

旋转分量到另一个参考系和把twist/wrench平移到另一个参考点是不同变换。质心COM与body origin通常不同，但上表两种FREE/DISTANCE数组之间的区别是frame，不能重复施加COM平移。依据：{source('State的body与joint布局', 'newton/_src/sim/state.py', 109, 165)}；{source('Control wrench约定', 'newton/_src/sim/control.py', 32, 42)}。
""",
        "refs": [
            ("newton/_src/sim/state.py", 109, 165),
            ("newton/_src/sim/control.py", 32, 42),
        ],
    },
}
