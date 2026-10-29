# Newton 1.7.0 · 仿真知识平台

本地网站：[Newton Knowledge](http://127.0.0.1:18448/)。双击 `启动知识库.cmd` 启动，`停止知识库.cmd` 停止；[部署与更新说明](site/README.md)。Agent 使用 [只读 stdio MCP](mcp_service/README.md)，与网站、CLI 共用同一版本化数据快照。

固定正式版本 v1.7.0，commit `7e75abe28b8d69522bc0b34837aaed2c303dff5a`。最新在线文档用于阅读导航，本库事实以固定源码、论文和保存的实验为准。

## 知识结构

从核心对象和仿真流程进入：资产导入 → 预处理 → Model/State 初始化 → 求解循环 → 观测、导出与渲染；循环展开为 Control → Collision detection → solver.step()。

| 内容 | 入口与覆盖 |
|---|---|
| 公共层 | 12 API 模块、14 Concepts、8 跨阶段主题、7 实际阶段；6条基础配方与12条新增任务配方另计，见 [覆盖注册表](knowledge/registry.json) |
| Solver 中心 | VBD、MuJoCo、Kamino 深入专区；Featherstone、ImplicitMPM、SemiImplicit、Style3D、XPBD 源码索引入口 |
| 原理、论文、源码 | [VBD](solvers/vbd/theory.md)、[MuJoCo](solvers/mujoco/theory.md)、[Kamino](solvers/kamino/theory.md)，共7篇本地原始论文 |
| 参数 | 三 solver 共169条构造/配置/reset记录（含必填model），45条重点Model输入；公共碰撞和子步设置单列 |
| 实验 | [VBD 三维 A/B](experiments/vbd_parameter_lab/index-3d.html)，17组34次CPU运行；直接变化的VBD可选构造参数9/47；[MuJoCo/Kamino 三维实验](experiments/solver_parameter_lab/index.html)，各2组、每个值独立复现两次 |
| Agent | [检索、精确读取与证据约定](agent/WORKFLOW.md)、[MCP 配置与示例](mcp_service/README.md) |
| 进度与验收 | [PRD](planning/PRD.md)、[阶段进度](planning/PROGRESS.md)、[P2 MCP任务报告](evaluations/p2-mcp-validation.json) |
| 持续维护 | [来源更新与版本差异](knowledge/pages/development/maintenance.md)、[版本范围](knowledge/releases.json)、[当前覆盖矩阵](evaluations/coverage-matrix.json) |

已索引、已解释、任务验证与实验验证分开标注。proposed 诊断不表示实测；其他 solver 的实验不能借作当前 solver 的证明。full surface contact 定义归 CollisionPipeline，substeps 属于调用方循环。

## 构建与使用

```powershell
Set-Location 'D:\RAG\Newton knowledge'
.\.venv\Scripts\python.exe -B -X utf8 scripts\retrieve.py --query 'CONTACT_F 初始化' --solver mujoco --include-shared
.\.venv\Scripts\python.exe -B -X utf8 scripts\rebuild.py
```

日常 rebuild 从 `scripts/author_platform.py` 和已有结构化源记录重建统一快照，不下载源码、不运行物理。原有 solver 源记录的重新提取显式使用 `--legacy-records`，其人工编辑入口为 curated.py、model_and_cases.py、author_docs.py、extend_solvers.py；不要只修改会被生成器覆盖的手册。公共层编辑 author_platform.py；接入与部署文档直接编辑原文件。

`knowledge/builds/<build_id>/` 保存不可变 catalog、records、documents、graph、SQLite 和校验 manifest；`knowledge/current.json` 是当前指针。同一内容复用同一世代；任务验证凭证绑定实际正文哈希，改动后的内容不会静默继承旧验证。

| 目录 | 用途 |
|---|---|
| sources / manifests | 固定源码、论文、依赖和哈希 |
| solvers | 深入solver的结构化知识和手册 |
| knowledge | 公共层、统一注册表、快照、任务凭证 |
| experiments | 实验程序、配置、原始数组、量测和回放 |
| scripts / site / mcp_service | 内容构建、网页、共享检索及只读工具 |
| evaluations / planning | 独立验收、任务轨迹、PRD、阶段记录 |

没有向量 embedding 或外部 LLM 检索依赖，图边表示有出处的对应关系，不自动生成因果。旧调参经验仍需带版本、场景、对照和原始产物审查后接入；[经验模板](experience/experiment-template.json) 不是已执行结果。
