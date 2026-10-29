# Newton 知识库：只读本地 MCP

服务固定 Newton 1.7.0，提交 `7e75abe28b8d69522bc0b34837aaed2c303dff5a`。采用 stdio，由客户端管理 Python 子进程；无需网站、模型密钥或网络请求。查询不运行仿真，不修改知识文件，不监听 MCP HTTP 端口。

## 接入

- 解释器：`D:\RAG\Newton knowledge\mcp_service\.venv\Scripts\python.exe`
- 入口：`D:\RAG\Newton knowledge\mcp_service\server.py`
- 运行依赖：[requirements.lock.txt](requirements.lock.txt)，官方 Python MCP SDK 2.3.0。
- 通用客户端配置：[configs/mcp.json](configs/mcp.json)。支持 TOML 的本机客户端参考现有 [configs/codex.toml](configs/codex.toml)。合并同名服务项并保留其他服务；本项目未修改用户全局配置。

```json
{
  "mcpServers": {
    "newton_knowledge": {
      "command": "D:\\RAG\\Newton knowledge\\mcp_service\\.venv\\Scripts\\python.exe",
      "args": ["-B", "-X", "utf8", "D:\\RAG\\Newton knowledge\\mcp_service\\server.py"],
      "env": {"PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"}
    }
  }
}
```

客户端须能访问这些 Windows 路径。stdio 服务进程由客户端启动/结束；网页地址 `http://127.0.0.1:18448/` 是给人浏览的入口，不能作为此 stdio 服务的连接 URL。配置后重新加载 MCP 客户端。

## 内容和证据范围

公共层包括 12 个公开 API 模块、14 个 Concepts、8 个跨阶段主题、7 个实际阶段和 6 条调用配方；8 个具体 backend 均有入口。VBD、MuJoCo、Kamino 有深入静态知识；另外五个为源码索引级。以每条记录的 coverage 判断已索引、已解释、任务验证、实验验证，不能由总条目数推断全面程度。

原有 VBD 47 个可选构造参数（加必填 model 共48记录）、20 个模型输入、17 组 A/B 保留；MuJoCo 34 个可选构造参数（加 model 共35记录）、15 个重点输入；Kamino 1 个可选构造参数、80 个配置字段、4 个 reset 字段（加 model 共86记录）、10 个重点输入。full surface contact 归 CollisionPipeline；substeps 归调用方循环，均非 VBD 构造参数。

P4 已保存 MuJoCo/Kamino 各两组有效 CPU A/B，每个参数值独立进程复现两次；实验、参数关联、原始哈希与三维回放均可由六工具读取。低预算失稳压力测试另行归档，不计有效组数。proposed 诊断是待验证计划。VBD 的 A/B 是有限场景的 CPU 观察，不能证明其他后端支持或给出通用推荐区间。MuJoCo native CPU 不支持 CONTACT_F，接触力量测配方选择 MuJoCo Warp；Warp 路径和 cpu/cuda 设备是两个维度。

## 六个工具和最小契约

六个名称与启动配置保留。未知字段、非法枚举或冲突 ID 不静默忽略。

| 工具 | 输入与返回 |
|---|---|
| search_knowledge | query，kind/domain/stage/solver/include_shared/limit/cursor。先限制候选范围再排序，命中含 read_next_call、source_next_call、owner 与 coverage。默认6条，最多20条。 |
| get_parameter | name 或 record_id，加 solver。返回声明默认、条件解析、单位、owner、固定来源与独立列出的实验。旧调用省略 solver 保留 VBD，并标 scope_resolution=legacy_default。 |
| get_experiment | experiment_id、solver、detail。读取保存的 A/B 配置、指标、raw hash、环境与回放；summary 无轨迹，full 加有界初始几何和完整产物引用，显式标注截断。 |
| get_relations | node_id、limit/offset/cursor/edge_cursor。一跳稳定边流，邻居首次出现时返回；每条边也携带精确邻居读取。next_cursor/edge_cursor 同步恢复，不截断后丢失剩余边。 |
| get_document | path 或 record_id。可读文档、claim、诊断、映射、论文元数据、模块、配方等。空参数分页列目录；文本用 section/start_line/max_lines 与 next_call 续读，可请求 include_outline。 |
| get_source | path 或 symbol_id，start_line/max_lines/scope。返回精确行号、固定 commit、当前及基线 SHA256。newton 根下仅允许 manifest 中的文本文件；experiment 只允许锁定的 run_lab.py/analyze_lab.py。 |

所有结果带 status、version、source_commit、build_id、read_only、requested_scope、resolved_scope、applied_filters。不同客户端不应把不同 build_id 的分页结果拼成一个世代。

- `solver=all`：公共内容和全部8后端；`shared`：仅公共内容；指定某 solver：仅其专属内容。`include_shared=true` 才加入明确适用于该 solver 的公共记录，不从 unknown 推断支持。
- `domain`：all/framework/workflow/solver/development；`stage`：all/asset_import/preprocess/initialization/control/collision/solver_step/output。
- `get_parameter` 和 `get_experiment` 默认 vbd 仅为旧调用兼容；新 agent 应显式传 solver，或直接执行返回的精确调用。
- 状态区分 ok、no_match、not_indexed、no_measured_evidence、unsupported_feature、unsupported_version；只有存在性已确认但所请求知识未整理时返回 not_indexed，随机未知词为 no_match。未知不等于 unsupported。
- 错误为 isError=true，并有 structuredContent.error.code/message；常见 SCOPE_CONFLICT、INVALID_ARGUMENT、SOURCE_HASH_MISMATCH、CURSOR_QUERY_MISMATCH、STALE_CURSOR。未知版本不回退至1.7.0。
- cursor 绑定查询条件、页大小和构建；换条件应重新检索，STALE_CURSOR 应从首项重新遍历。文档文本用原始行号续读，cursor 用于目录。
- 文本最多200行/18,000逻辑字符；完整工具 JSON 最多32,000逻辑字符。超限明确报 RESPONSE_BUDGET，可减小 limit/max_lines；原始轨迹、PDF 和数组保留为本地产物引用。
- Schema 以服务 tools/list 与 [冻结契约](../planning/p0/mcp-contract.json) 为准。JSON 字符、UTF-8 bytes、tokenizer token 是不同计量，测试报告分别记录。

## Agent 调用方式

从问题检索，根据返回的精确调用继续，避免猜测内部文件路径：

```json
{"tool":"search_knowledge","arguments":{"query":"球穿过粗三角布面 full surface 穿模","limit":5}}
{"tool":"get_parameter","arguments":{"record_id":"pipeline:enable_rigid_soft_full_surface_contact","solver":"shared"}}
{"tool":"get_experiment","arguments":{"experiment_id":"full_surface","solver":"vbd"}}
{"tool":"get_relations","arguments":{"node_id":"concept:collisions","limit":12}}
```

参数结果中的 source_next_call 带实际声明行；先检查 owner/default，再把量测与机制对应。不要把定义在公共管线中的开关归为某个 solver 的构造参数。

```json
{"tool":"search_knowledge","arguments":{"query":"多机器人 IK controller MuJoCo 接触力","kind":"recipe","limit":5}}
{"tool":"get_document","arguments":{"record_id":"recipe:ik-mujoco-contact"}}
{"tool":"get_relations","arguments":{"node_id":"recipe:ik-mujoco-contact","limit":12}}
```

配方分别说明 setup、每仿真子步、每控制帧、每输出帧和 reset/模型更新；有官方源码出处，但不表示本库执行了这条物理任务。路径和 API 应继续从精确读取的返回值中取得。

跨 solver 默认值：

```json
{"tool":"get_parameter","arguments":{"solver":"vbd","name":"iterations"}}
{"tool":"get_parameter","arguments":{"solver":"mujoco","name":"iterations"}}
{"tool":"get_parameter","arguments":{"solver":"kamino","name":"config.padmm.max_iterations"}}
```

VBD 声明10，MuJoCo 声明None并有条件解析，Kamino PADMM200是另一种预算；不能按相同迭代数字给性能排次。未整理的 XPBD iterations 返回 not_indexed 和可继续读的源码，而不是借用 VBD 参数。

## 构建和验证

旧读取字段与规范字段同时保留：hit 的 kind/solver/next_call，参数的 declared_default/associated_experiments，实验的平铺字段与 artifacts 字典，以及 content/next_start_line。规范原始产物列表为 raw_artifacts；文档目录仍需分页读取，full 初始几何明确标注截断。兼容字段也计入响应预算。验证凭据可沿 validated_by 关系读取，其正文与源码指纹变化后失效。见 [维护与版本比较](../knowledge/pages/development/maintenance.md) 和 [真实兼容客户端检查](../evaluations/p5-mcp-validation.json)。

唯一数据发布入口：`site/build_site.py` → `scripts/build_platform.py`。catalog、graph、记录、文档和 SQLite 写入不可变的 `knowledge/builds/<build_id>/`，完成校验后替换 current 指针；相同输入复用原世代。网站、CLI 和 MCP 读取同一快照。源记录改动后重新构建，并重启本地网页进程以加载服务代码更新；MCP 客户端重新加载工具 schema。

```powershell
& 'D:\RAG\Newton knowledge\.venv\Scripts\python.exe' -B -X utf8 'D:\RAG\Newton knowledge\site\build_site.py'
& 'D:\RAG\Newton knowledge\mcp_service\.venv\Scripts\python.exe' -B -X utf8 'D:\RAG\Newton knowledge\scripts\validate_p2_mcp.py'
```

真实 stdio 任务与过滤、分页、负面边界报告见 [P2 MCP 验收](../evaluations/p2-mcp-validation.json)。报告记录实际工具 JSON 的 tokenizer 数量，不将其冒充宿主 agent 的隐藏上下文或模型账单用量。上游 Newton 测试、知识结构验收、网页验收和物理实验分开报告。
