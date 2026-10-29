# USD 解析与 Schema

USD 属性如何进入 Newton 模型。

## 机制与数据流

add_usd 解析 supported schemas，把几何、刚体、关节、sites、材料和可变形体数据写入 builder。解析阶段先做单位、up-axis 和拓扑检查。

## 诊断与边界

不支持的 Schema 或属性不应被视为已复现物理。可视模型与 collision/solver 的支持需要后续独立验收。



## Resolver优先级与回退

`schema_resolvers=None`时，实际列表仅为`[SchemaResolverNewton()]`。同一属性按三层解析：按列表优先级找第一个authored值；没有时用该属性的importer default；仍没有才使用resolver映射里近似的schema default。列表越靠前优先级越高；资产带PhysX/MJC命名空间不等于它会自动完整转换。

需要以PhysX authored值优先时，可以明确配置：

```python
from newton.usd import SchemaResolverNewton, SchemaResolverPhysx
builder.add_usd(
    source="asset.usda",
    schema_resolvers=[SchemaResolverPhysx(), SchemaResolverNewton()],
)
```

这只是配置示例，未加载上述占位资产。改变resolver顺序是语义干预，应记录解析后的属性，而不只保存文件名。依据：[实际默认列表](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/utils/import_usd.py#L474-L475)；[三层回退与顺序示例](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/usd_parsing.rst#L645-L693)。

## 单位与可变形体边界

v1.7.0的legacy rigid/collider导入仍要求`metersPerUnit=1`与`kilogramsPerUnit=1`，不能承诺所有USD路径自动转成SI。粒子路径会转换单位；混合rigid/particle资产可能走不同路径，因此应先把混合stage规范为单位元数据1，并检查warning。依据：[非单位及混合路径警告](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/utils/import_usd.py#L587-L614)。

AOUSD deformable仅支持文档列明的子集；Omni/PhysX原生deformable schema不由resolver系统全面翻译。先识别curve/surface/volume的离散化，再核查当前importer能读取的具体schema；把被保留的solver属性与实际被solver消费的属性分开记录。依据：[deformable schema支持边界](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/usd_parsing.rst#L145-L156)。质量优先级和密度回退另见[质量与惯量](#/record/concept%3Amass-inertia)。

## 证据与适用边界

本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。

官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档](https://newton-physics.github.io/newton/latest/concepts/usd_parsing.html)。

## 固定版本原始出处

- [docs/concepts/usd_parsing.rst:1](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/usd_parsing.rst#L1)
- [newton/_src/utils/import_usd.py:474](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/utils/import_usd.py#L474-L475)
- [docs/concepts/usd_parsing.rst:645](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/usd_parsing.rst#L645-L693)
- [newton/_src/utils/import_usd.py:587](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/newton/_src/utils/import_usd.py#L587-L614)
- [docs/concepts/usd_parsing.rst:145](https://github.com/newton-physics/newton/blob/7e75abe28b8d69522bc0b34837aaed2c303dff5a/docs/concepts/usd_parsing.rst#L145-L156)
