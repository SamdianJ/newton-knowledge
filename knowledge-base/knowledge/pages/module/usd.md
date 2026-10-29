# USD 资产与 Schema

USD 资产、Schema 与物理属性解析。

## 职责、输入与输出

通过 ModelBuilder.add_usd 和 newton.usd 公开 Schema 工具把 USD 层级及物理属性转入 builder。解析结果受 schema、单位、坐标轴、刚体/关节/可变形体表达与 importer 支持范围影响。

## 失败模式与限制

import 成功只证明解析；还要检查导入后的质量、碰撞表示、驱动、自定义属性和 solver 支持。不要把 viewer 导出的 USD 视为逐项保真 roundtrip。

## 模块公开导出索引

- [DEFORMABLE_LEGACY_NAMESPACES](#/record/symbol%3Anewton.usd.DEFORMABLE_LEGACY_NAMESPACES)
- [find_tetmesh_prims](#/record/symbol%3Anewton.usd.find_tetmesh_prims)
- [get_attribute](#/record/symbol%3Anewton.usd.get_attribute)
- [get_attributes_in_namespace](#/record/symbol%3Anewton.usd.get_attributes_in_namespace)
- [get_custom_attribute_declarations](#/record/symbol%3Anewton.usd.get_custom_attribute_declarations)
- [get_custom_attribute_values](#/record/symbol%3Anewton.usd.get_custom_attribute_values)
- [get_float](#/record/symbol%3Anewton.usd.get_float)
- [get_gprim_axis](#/record/symbol%3Anewton.usd.get_gprim_axis)
- [get_mesh](#/record/symbol%3Anewton.usd.get_mesh)
- [get_physics_scenes](#/record/symbol%3Anewton.usd.get_physics_scenes)
- [get_quat](#/record/symbol%3Anewton.usd.get_quat)
- [get_scale](#/record/symbol%3Anewton.usd.get_scale)
- [get_tetmesh](#/record/symbol%3Anewton.usd.get_tetmesh)
- [get_transform](#/record/symbol%3Anewton.usd.get_transform)
- [has_applied_api_schema](#/record/symbol%3Anewton.usd.has_applied_api_schema)
- [has_attribute](#/record/symbol%3Anewton.usd.has_attribute)
- [type_to_warp](#/record/symbol%3Anewton.usd.type_to_warp)
- [value_to_warp](#/record/symbol%3Anewton.usd.value_to_warp)
- [PrimType](#/record/symbol%3Anewton.usd.PrimType)
- [SchemaResolver](#/record/symbol%3Anewton.usd.SchemaResolver)
- [SchemaResolverMjc](#/record/symbol%3Anewton.usd.SchemaResolverMjc)
- [SchemaResolverNewton](#/record/symbol%3Anewton.usd.SchemaResolverNewton)
- [SchemaResolverPhysx](#/record/symbol%3Anewton.usd.SchemaResolverPhysx)

## 从导入接口进入语义检查

`add_usd`默认仅Newton resolver；PhysX/MJC来源需要显式配置解析优先级。当前版本的legacy rigid/collider与particle单位转换路径不同，不应假定所有USD内容自动按stage元数据转SI。详见[resolver、单位与deformable支持](#/record/concept%3Ausd-parsing)；与URDF/MJCF的选择和质量语义比较见[资产导入](#/record/stage%3Aasset_import)。

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

## 精确 API 入口

- [newton.ModelBuilder.add_usd](#/record/symbol%3Anewton.ModelBuilder.add_usd)

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/concepts/usd_parsing.html)。

## 固定版本原始出处

- [newton/usd.py:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/usd.py#L1)
- [docs/concepts/usd_parsing.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/usd_parsing.rst#L1)
- [docs/api/newton_usd.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/api/newton_usd.rst#L1)
- [newton/_src/utils/import_usd.py:474](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/utils/import_usd.py#L474-L475)
- [newton/_src/utils/import_usd.py:587](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/utils/import_usd.py#L587-L614)
- [newton/_src/sim/builder.py:4257](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/sim/builder.py#L4257)
