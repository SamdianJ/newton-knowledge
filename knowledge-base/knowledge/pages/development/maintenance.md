# 维护、来源更新与版本差异

当前服务固定 Newton 1.7.0 / commit `7e75abe28b8d69522bc0b34837aaed2c303dff5a`。新版本先生成差异提案，再建设独立来源锁、版本 ID、内容与证据；本服务对其他版本返回 unsupported_version。这里只交付维护机制，没有引入另一个真实 Newton 版本。

## 更新当前知识

PowerShell 中设置 `$kb = 'D:\RAG\Newton knowledge'`。先运行：

```powershell
& "$kb\.venv\Scripts\python.exe" "$kb\scripts\maintain.py" check
& "$kb\.venv\Scripts\python.exe" "$kb\scripts\rebuild.py"
```

`rebuild.py` 只生成知识和索引，不隐式执行物理实验或联网下载。它在生成前检查锁中全部 1215 个源码文件；`build_platform.py` 独立再检查一次。修改知识请编辑对应 author 生成器；原始 VBD 程序与数据保持冻结。MuJoCo/Kamino 新实验遵守各自已保存协议，不能把旧实验换个版本标签。

发布先写 `knowledge/staging/`，关闭 SQLite 文件后校验完整 manifest，再原子移动到 builds，最后原子替换 current 指针。相同输入复用同一快照。中断留下的 staging 不可成为 current；直接重新构建即可，旧目录保留便于排查。失败的旧构建尝试不计发布。不要手工覆盖 immutable build 或修改 manifest 以消除错误。

源码、契约、程序、manifest、产物哈希或 SQLite 构建标识冲突会拒绝读取。游标绑定构建与查询；STALE_CURSOR 时从第一页重新检索。多版本扩展需独立契约/路由实现，本版不会自动把提案切换为线上知识。

## API 与默认值比较

```powershell
& "$kb\.venv\Scripts\python.exe" "$kb\scripts\maintain.py" inventory --out "$kb\knowledge\releases\1.7.0\source-inventory.json"
& "$kb\.venv\Scripts\python.exe" "$kb\scripts\maintain.py" compare --baseline "$kb\knowledge\releases\1.7.0\source-inventory.json" --candidate 'D:\path\to\candidate-newton' --out "$kb\evaluations\candidate-diff.json"
```

静态比较列出公开导出/方法/属性、签名、构造函数和配置声明的默认表达式，以及来源文件变化。不会导入 Newton。声明 None 可能是数组分配占位；声明默认不等于后端解析值。`source-inventory.json` 保存 1.7.0 的实际版本与 commit；fixture 差异报告明确标为合成测试，不是某个新版本的支持声明。

## 验证凭据与失效

任务凭据同时绑定正文 SHA256 和引用源码的 path/line/commit/SHA256。正文或引用变化后取消 task_validated；报告被篡改则拒绝构建。每条有效凭据有 validated_by 关系，MCP 可以读取对应的 validation_report；原报告与验证时 build 保留。任务验证是确定性工具证据检查，不表示执行了自由生成式 agent 或物理仿真。

真实任务回归通过后，仅接受已失效或缺失的凭据，避免把每次运行都变成新发布循环：

```powershell
& "$kb\mcp_service\.venv\Scripts\python.exe" "$kb\scripts\validate_p2_mcp.py"
& "$kb\mcp_service\.venv\Scripts\python.exe" "$kb\scripts\validate_p3_mcp.py"
& "$kb\.venv\Scripts\python.exe" "$kb\scripts\accept_validations.py" evaluations/p2-mcp-validation.json --only-stale
& "$kb\.venv\Scripts\python.exe" "$kb\scripts\accept_validations.py" evaluations/p3-mcp-validation.json --only-stale
& "$kb\.venv\Scripts\python.exe" "$kb\scripts\rebuild.py"
```

最终发布后再运行全部回归，记录 published build。原 P2/P3 报告格式的历史兼容升级只从其原验证快照提取源码指纹，不声称补做过历史测试。

## 回归与归档

```powershell
& "$kb\mcp_service\.venv\Scripts\python.exe" "$kb\scripts\validate_p4_mcp.py"
& "$kb\mcp_service\.venv\Scripts\python.exe" "$kb\scripts\validate_p5_mcp.py"
& "$kb\.venv\Scripts\python.exe" "$kb\scripts\validate_p3.py"
& "$kb\.venv\Scripts\python.exe" "$kb\scripts\validate_p4.py"
& "$kb\.venv\Scripts\python.exe" "$kb\scripts\validate_p5.py"
& "$kb\.venv\Scripts\python.exe" "$kb\scripts\maintain.py" check
```

网站检查需先 `site/start.ps1 -NoBrowser`。服务实现变化后使用 stop/start 重新载入；内容指针切换会由读取器检测。P2/P3/P4/P5 回归脚本覆盖报告前自动按原 build 与内容哈希归档，因此同 build 多次回归也不相互覆盖。重新分析物理实验前，用 `maintain.py archive` 显式归档 p4-physics-validation.json。历史没有保存下来的 trace 不重建、不伪造。

旧客户端保留 hit.kind/solver/next_call、parameters[].declared_default/source_refs/associated_experiments、实验平铺字段与 artifacts 字典、文本 content/next_start_line；规范字段继续保留。原始产物清单位于 raw_artifacts。兼容字段也计入 32000 字符预算，必要时缩短完整行窗口并返回可执行续读。文档列表按页返回 documents 和 items；不能再假定一次调用拿到全量清单。

当前覆盖台账见 `/files/evaluations/coverage-matrix.json`。12 API、14 Concepts、8 backend、8 跨阶段主题、7 实际阶段、6 基础配方使用独立分母，12 个新增配方另计。VBD 深入且有17组实测；MuJoCo/Kamino 深入且各有2组；另外5个 backend 为索引级。具体能力以每条记录的 coverage、support_status、适用范围与保存证据为准。
