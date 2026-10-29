# 碰撞与 Contacts

几何候选、接触存储与求解消费。

## 机制与数据流

CollisionPipeline 用 world/collision filter、broad phase 和 narrow phase 产生 Contacts，再由 solver 计算响应。full surface 开关 enable_rigid_soft_full_surface_contact 属于公共管线，默认 False；现有 VBD A/B 检查粗三角面内接触。

## 诊断与边界

漏检、容量不足、初始穿透和 penalty 压入不同。VBD 开启 full surface 的案例仍有约 0.245 mm 终态压入。固定版本中 edge/face soft contacts 由 VBD 的受支持路径消费；XPBD、SemiImplicit、Style3D 的 particle-only 路径明确拒绝，VBD proxy-particle coupling 也不支持。不要把该边界泛化为所有仅消费 rigid_contacts 的后端都会抛错，也不要混同刚体 hydroelastic contact。



## 刚体碰撞：先选表示，再理解算法

下面描述Newton公共CollisionPipeline；native MuJoCo或MuJoCo Warp自带碰撞器有自己的支持与过滤规则，不能自动套用。

| 表示/阶段 | 核心工作 | 主要限制与选择 |
|---|---|---|
| broad phase | AABB剔除不相交候选 | 默认`explicit`使用预计算shape pairs；`nxn`全配对适合小场景；`sap`用空间排序削减候选。选择算法不改变被过滤掉的配对 |
| primitive/convex narrow phase | support mapping上的MPR处理穿透，GJK处理分离距离 | 不能把convex hull当作保留凹腔；不是EPA求穿透深度 |
| 无预计算SDF的triangle mesh | live BVH找到附近三角形/表面，产生距离查询接触 | 复杂网格查询成本较高；三角形CCW法线与背面剔除影响是否检出；此路径不提供hydroelastic |
| 预计算SDF | 网格距离查询及可选接触缩减 | 几何近似精度取决于SDF配置；烘焙/scale/padding在预处理阶段核对 |
| hydroelastic | 双侧SDF生成分布接触面积并缩减代表点 | 两侧都要is_hydroelastic=True和SDF；限有体积表示，非单位scale须烘焙；不是刚柔full-surface开关 |

依据：[几何表示与路由](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/collisions.rst#L31-L80)；[broad-phase选择](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/collisions.rst#L734-L780)；[MPR/GJK与mesh/BVH](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/collisions.rst#L991-L1068)；[hydroelastic前提](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/collisions.rst#L1838-L1880)。

## 过滤先于求解

不同非负world不相撞，global world=-1可与各world配对。collision_group=0关闭；正组只与同正组或任意负组相撞；负组与正/负组相撞，但同一个负组互不相撞。还要检查shape的collision flag、同body/static-static的固有排除、显式`add_shape_collision_filter_pair`以及导入时self-collision和默认parent-child过滤。过滤丢掉的是候选，增加solver迭代无效。依据：[world/group过滤](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/collisions.rst#L479-L605)与[固有排除和显式配对](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/collisions.rst#L665-L704)。

## margin决定接触面，gap决定何时检测

普通刚体对的真实表面距离为s，pair margin为m=margin_a+margin_b，pair gap为g=gap_a+gap_b。接触空间距离d=s-m，生成条件d<=g；AABB按各自margin+gap扩张。gap不直接移动接触面，增大margin会改变有效接触面的位置。solver的有限柔顺压入、求解误差和初始相交仍须另查，不能由该几何条件推出实际必无穿透。依据：[margin/gap公式](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/collisions.rst#L1291-L1319)。

opt-in `speculative_contact_gap_max`按接触点相对法向闭合速度扩展检测gap，`collide(...,dt=...)`的dt是到下一次碰撞更新的时间，包含被跳过的solver子步。它保留当前分离位置的候选，不计算time-of-impact、不把物体推进到撞击点；只适用于刚体非hydroelastic路径，不能当通用CCD或DAT。依据：[speculative admission与dt](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/collisions.rst#L1382-L1428)。

## 接触数据、缩减与历史

rigid_contact_point0/1是各body局部坐标点，normal是world-frame、从shape A指向B。shape id、margin/offset与采样state一起定义几何，不能只用body位置重建作用点。raw contact count在溢出时可超过capacity，存储访问须钳制并单独检查overflow；中间triangle-pair/reduction缓冲也可能先丢候选。CONTACT_F需要解析容量后绑定同一Contacts，冻结后扩容要新Model。

mesh/SDF/hydroelastic可能生成很多原始接触，默认reduction按法向、空间分布与深度选代表点；缩减不是求解器迭代预算。deterministic模式通过确定性选择/排序（hydro还需确定性聚合）稳定接触顺序，不能单独保证整个solver跨设备确定。matching默认disabled；latest保留本帧几何并给出匹配索引；experimental sticky在条件满足时复用上一帧几何，非disabled模式隐含deterministic。episode reset同时检查pipeline匹配历史与solver历史。

依据：[接触几何坐标](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/collisions.rst#L97-L119)；[contact reduction](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/collisions.rst#L1184-L1244)；[deterministic与matching语义](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/collisions.rst#L2167-L2270)。容量故障处理见[接触容量诊断](#/record/recipe%3Acontact-capacity-diagnosis)，三种软碰撞容器见[可变形体](#/record/concept%3Adeformables)。

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

## 精确 API 入口

- [newton.CollisionPipeline](#/record/symbol%3Anewton.CollisionPipeline)
- [newton.CollisionPipeline.collide](#/record/symbol%3Anewton.CollisionPipeline.collide)

## 相关知识

- [pipeline:enable_rigid_soft_full_surface_contact](#/record/pipeline%3Aenable_rigid_soft_full_surface_contact)
- [lab:full_surface](#/record/lab%3Afull_surface)
- [stage:collision](#/record/stage%3Acollision)

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/concepts/collisions.html)。

## 固定版本原始出处

- [docs/concepts/collisions.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/collisions.rst#L1)
- [docs/concepts/collisions.rst:31](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/collisions.rst#L31-L80)
- [docs/concepts/collisions.rst:734](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/collisions.rst#L734-L780)
- [docs/concepts/collisions.rst:991](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/collisions.rst#L991-L1068)
- [docs/concepts/collisions.rst:1838](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/collisions.rst#L1838-L1880)
- [docs/concepts/collisions.rst:479](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/collisions.rst#L479-L605)
- [docs/concepts/collisions.rst:665](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/collisions.rst#L665-L704)
- [docs/concepts/collisions.rst:1291](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/collisions.rst#L1291-L1319)
- [docs/concepts/collisions.rst:1382](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/collisions.rst#L1382-L1428)
- [docs/concepts/collisions.rst:97](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/collisions.rst#L97-L119)
- [docs/concepts/collisions.rst:1184](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/collisions.rst#L1184-L1244)
- [docs/concepts/collisions.rst:2167](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/collisions.rst#L2167-L2270)
- [newton/_src/sim/collide.py:142](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/collide.py#L142-L223)
- [newton/_src/sim/model.py:1966](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/model.py#L1966-L1975)
- [newton/_src/sim/collide.py:1250](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/collide.py#L1250)
- [newton/_src/sim/collide.py:2269](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/collide.py#L2269)
