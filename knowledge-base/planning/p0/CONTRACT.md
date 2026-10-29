# P0 冻结的范围与调用契约

依据 PRD 0.2 与固定 Newton 1.7.0 快照。知识内容的目标深度和当前达成状态分别记录。

- `knowledge/registry.json`：12 API、14 Concepts、8 backend、8 跨阶段主题、7 阶段与6配方的稳定目标、公共导出、来源和深度。
- `manifests/source-lock.json`：干净固定源码快照的全部已跟踪文件哈希。
- `record.schema.json`：公共/solver归属、定义所有者、适用性、证据与覆盖状态的共同字段。
- `mcp-contract.json`：六工具输入输出契约、严格参数、版本、范围、分页、明确错误与响应预算。
- `migration-baseline.json` / `migration-map.json`：现有全部文档、参数、图ID、检索ID、A/B原始数据及生成链、路由和兼容映射。
- `required-paths.json`：R01–R06，验收端点和来源；关系仅表示有出处的对应，不推断因果。
- `acceptance-tasks.json`：T01–T12，必需记录、答案要点、禁止结论、预算与边界用例。

## 首版范围语义

`solver=all` 发现公共及全部八 backend；`solver=shared` 仅公共内容；`solver=X` 为X专属，显式 `include_shared=true` 加入有来源支持的适用公共记录。unknown不等于unsupported。旧参数查询省略solver保留VBD，但必须标明legacy_default。

每次命中和图邻居都有可执行精确读取；文档/记录、源码、搜索和关系分页标明剩余内容。先过滤再排序，cursor绑定构建世代和查询。未知输入不静默忽略。no_match、not_indexed、no_measured_evidence、unsupported_feature、unsupported_version分别处理。

输出保留旧成功记录字段，新增status、build_id、范围与应用过滤；业务错误必须机器可解析。错误和未知条件只在有来源时判定，不从空命中猜测。JSONschema约束后仍需校验互斥path/record_id或path/symbol_id、分页条件和范围冲突。

## 构建与发布

源记录是唯一编辑入口。构建输出的catalog、graph与SQLite拥有共同build_id；部分构建不一致要明确拒绝。被引用文件核对source-lock，无法核对的来源只能标local_snapshot_unverified_file。

P1通过范围、导航、旧ID/路径、原始实验不变和构建一致性；P2通过全部模块入口、R01–R06、T01–T12及真实stdio契约测试。P3增加任务深度，P4新增物理A/B，P5持续维护并交付可重复执行的更新检查。
