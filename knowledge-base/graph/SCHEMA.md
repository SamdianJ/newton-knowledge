# 关系图与证据模式

入口：`knowledge-graph.json`，`schema_version=1.0`。所有节点 ID 稳定，所有边目标必须存在。

| 类型 | 示例 | 必要语义 |
|---|---|---|
| solver | solver:VBD:1.7.0 | 版本和 commit |
| parameter | newton:1.7.0:SolverVBD:iterations | 类型、声明默认、解析、状态、出处 |
| model_input | model:tet_materials | Model 定义、单位/约定、消费者 |
| claim | c:margin | 带范围结论、证据类别、版本 |
| code_symbol | code:1.7.0:文件路径::函数名@L行号 | commit + 路径 + 起止行；区分同名 getter/setter |
| paper | paper:dat2026 | 原始 PDF、哈希、页/公式定位 |
| mechanism_mapping | map:dat | 论文机制与实现的一致/扩展/非等价关系 |
| experiment | exp:implicit_spring | 运行条件、实际结果、适用范围 |
| diagnostic | diag:slip | 待验证方案，不自动标成功经验 |

`background_method`、`implemented_or_extended_at` 不能解读为逐行复刻或证明。`narrow_probe` 不能解读为整个机制通过全面物理验证。`supported_by_source` 表示源码阅读证据，不是性能实验。

源码函数调用清单另保存在 `indexes/source_symbols.json` 的 `calls_syntactic`，明确不作为已解析调用边导入图。如此避免把同名变量、条件分支、动态 kernel launch 误解析为确定依赖。

文件哈希校验、参数全集校验、图无悬挂边、来源行号范围与检索回归由 `scripts/validate.py` 实现。它验证知识制品的一致性，不验证每个物理陈述在任意场景成立。
