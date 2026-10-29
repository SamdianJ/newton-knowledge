# 资产导入

把真实资产变成可审查的 builder 输入。

输入：原语/URDF/MJCF/USD、尺度、坐标和初态。输出：ModelBuilder 的刚体、关节、形状、sites、材料与驱动。先核对单位、轴向、labels、碰撞/视觉几何和导入 warning；保留资产哈希与 importer 配置。

## 按资产语义选择导入入口

| 格式与入口 | 要保留的语义 | 导入后必须核查 |
|---|---|---|
| URDF：`ModelBuilder.add_urdf` | 机器人link/joint、碰撞与视觉几何、inertial | 显式inertial和几何推断的选择；`joint_damping_mode`默认None在1.7仍按drive映射并告警，显式`passive`写joint_damping，XPBD/VBD不消费该被动关节阻尼 |
| MJCF：`ModelBuilder.add_mjcf` | MuJoCo模型、compiler/default配置及支持的命名空间属性 | `<inertial>`和`compiler inertiafromgeom`共同决定质量来源；检查导出到目标solver后的关节、equality/tendon、几何和控制语义，不把导入成功当作任意solver支持 |
| USD：`ModelBuilder.add_usd` | 场景层级、UsdPhysics、受支持的Newton/扩展schema | 默认只启用Newton resolver；显式设resolver优先级，核对stage单位、排除articulation的loop joint以及deformable支持子集 |

URDF阻尼依据：[import_urdf参数与兼容默认](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/utils/import_urdf.py#L187-L203)。MJCF质量来源：[import_mjcf inertiafromgeom与显式惯量](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/utils/import_mjcf.py#L2363-L2425)。三种格式的质量规则由[质量导入规则](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/mass_inertia.rst#L122-L160)统一导航。

操作顺序：保存原资产与配置 → 选择格式/solver → 明确单位和轴向 → 检查解析warning与实际body/joint/shape数量 → 查看视觉/碰撞表示 → 核对质量与控制 → 再finalize并检查结果。USD resolver和单位限制见[USD解析](#/record/concept%3Ausd-parsing)，几何准备见[预处理](#/record/stage%3Apreprocess)。这里未新增资产导入端到端实测。

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

## 相关知识

- [module:usd](#/record/module%3Ausd)
- [concept:usd-parsing](#/record/concept%3Ausd-parsing)
- [concept:conventions](#/record/concept%3Aconventions)
- [concept:articulations](#/record/concept%3Aarticulations)

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/guide/overview.html)。

## 固定版本原始出处

- [docs/guide/overview.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/guide/overview.rst#L1)
- [docs/concepts/usd_parsing.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/usd_parsing.rst#L1)
- [newton/_src/utils/import_urdf.py:187](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/utils/import_urdf.py#L187-L203)
- [newton/_src/utils/import_mjcf.py:2363](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/utils/import_mjcf.py#L2363-L2425)
- [docs/concepts/mass_inertia.rst:122](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/mass_inertia.rst#L122-L160)
