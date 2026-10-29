# Newton Knowledge 本地网站

地址：[http://127.0.0.1:18448/](http://127.0.0.1:18448/)。双击根目录 `启动知识库.cmd` 构建并后台启动；`停止知识库.cmd` 停止此服务。只监听127.0.0.1，不设置开机自启动，关闭网页不会停止后台进程。

## 导航结构

Newton总览包含核心对象、经典流程和开发测试摘要。仿真流程提供5个主阶段和3个循环子阶段的可展开摘要、知识入口和官方文档链接。模块与主题页分别列出12个API、14个Concepts、8个跨阶段主题和6条配方；Solver中心展示8个后端。

VBD、MuJoCo、Kamino 使用相同的总览、原理、参数、模型输入、诊断、实验、论文与源码导航。另五个后端是源码索引级，明确列出未整理的参数或实验。切换solver不会隐式使用VBD数据。共享管线参数显示公共归属；面包屑保留流程/solver位置。

原有31篇文档、169条solver参数和17组VBD A/B保留；MuJoCo/Kamino实测在P4交付之前显示空缺状态。9/47表示VBD可选构造参数的直接干预覆盖，不能把材料组或流程设置计入这个分母。

## 启动与更新

```powershell
Set-Location 'D:\RAG\Newton knowledge'
.\site\start.ps1
.\site\stop.ps1
.\.venv\Scripts\python.exe -B -X utf8 scripts\rebuild.py
```

`start.ps1 -NoBrowser` 后台启动而不打开窗口；`-Port 18449` 可换端口，先停止已有单实例。默认18448与原实验预览18447独立。服务状态和日志在 site/run，停止脚本核对进程身份。

`更新知识库网站.cmd` 或 `site/build_site.py` 只发布统一数据快照；完整日常内容构建使用 scripts/rebuild.py。公共知识源为 scripts/author_platform.py；既有solver记录的重提取用 rebuild.py --legacy-records。构建不下载、解析或运行新的物理实验。

前端编辑入口是 dist/platform.js、platform.css、index.html；style.css和本地vendor库保留。构建不覆盖前端源码。刷新浏览器加载前端/数据更新；修改 server.py 或 knowledge_store.py 后停止再启动服务。原 app.js/multi-solver.js 保留为迁移历史，不再由入口页面加载。

## 数据与证据

网站、CLI和MCP从 knowledge/current.json 读取同一不可变快照，catalog、graph、SQLite、记录和文档使用共同build_id。site/dist的JSON和site/data/site.sqlite是兼容镜像，不能作为新的编辑入口。源码片段与source-lock的SHA256核对。

VBD三维页面直接使用原实验资源，没有复制轨迹或重算物理。公式、Mermaid、PDF、源码和实验均在本机；点击官方latest链接才需要外网，latest可能已变化，结论以固定commit为准。

本地API只读：/api/health、/api/catalog、/api/graph、/api/coverage、/api/search、/api/record、/api/relations、/api/document、/api/source。/files只提供允许的知识产物；配置、隐藏目录和路径越界被拒绝。

## 验收

MuJoCo 与 Kamino 的实验室现各有两组真实 CPU A/B，同步三维回放来自已保存位姿。VBD 的原始17组保留。完整的更新、版本差异、证据失效、回归归档和故障恢复流程见 [维护说明](../knowledge/pages/development/maintenance.md)。

```powershell
.\mcp_service\.venv\Scripts\python.exe -B -X utf8 scripts\validate_p2_mcp.py
.\.venv\Scripts\python.exe -B -X utf8 scripts\validate_p2.py
```

[P2网站与覆盖验收](../evaluations/p2-validation.json)、[真实stdio任务报告](../evaluations/p2-mcp-validation.json)分别记录范围、构建和证据。旧 validate_site.py 描述改版前的页面结构，历史报告保留；当前改版按阶段验收脚本检查。P0/P1历史证据不表示此后每个版本自动通过。
