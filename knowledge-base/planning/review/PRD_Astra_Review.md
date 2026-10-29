# Newton 知识库重构 PRD 独立审核

审核日期：2026-10-28  
审核对象：[PRD v0.1](<D:/RAG/Newton knowledge/planning/PRD.md>)  
事实基线：本地 Newton 1.7.0 快照，commit `7e75abe28b8d69522bc0b34837aaed2c303dff5a`。  
审核方式：公开 API、官方文档导航、主要源码模块静态盘点；现有网站构建与 MCP 实现审查；独立 Python stdio 客户端实际调用。没有启动物理仿真。

## 1. 总体判断

**建议有条件通过方向评审，补齐范围清单与 MCP 最小契约后再冻结实施版。**

PRD 的主体方向正确：公共流程与 solver 专区分离、统一三个 solver 的目录、参数定义和实验适用范围分开、固定版本与在线 latest 区分、待验证诊断与实测不混用。这些设计直接针对现有实现中的真实问题。当前 `site/dist/app.js:46–47` 的文档侧栏仍统一链接到 `#parameters`、`#experiments`，而这些入口默认读取 VBD 数据，说明导航重构有明确价值。

但三项目标的成熟度不同：

| 审核目标 | 判断 | 核心原因 |
|---|---|---|
| Newton 主要模块全面性 | **PRD 尚无足以验收的覆盖承诺** | 有流程骨架，但没有与实际公开 API、官方 Concepts、全部具体 solver 对齐的范围清单；IK、批量选择、耦合、可微仿真等易被漏掉 |
| 信息结构清晰度 | **方向清晰，数据语义仍不够具体** | 两条路径适合人阅读；`solver 归属` 尚混合定义所有者、适用 solver 和实验证据来源；缺少跨阶段主题的明确归档规则 |
| MCP 对 agent 的实际有效性 | **局部有效，跨模块任务尚不闭环** | 参数精确读取、实测边界与源码阅读可用；公共 API 发现、共享范围、搜索翻页、关系到正文的精确续读与空缺反馈不足 |

**这不是要求首期把整个 Newton 做成与 VBD 相同深度。** 合理边界应是：首期对全部主要模块提供可发现、可定位、明确深浅和缺口的覆盖地图；只对 VBD、MuJoCo、Kamino 做深入知识整理，新增物理实验继续后置。当前三个 solver 的深入范围是合理产品取舍，不能直接当作 Newton 整体覆盖率的分母。

现有能力值得保留：

- `get_parameter` 正确区分 VBD `iterations=10` 与 MuJoCo 的 `None → 模型属性 → 后端默认` 解析；Kamino 限定配置名可读取。
- `get_experiment(..., solver="mujoco")` 明确返回 `NO_MEASURED_EXPERIMENTS`，未借用 VBD 实验。
- 请求 `version="latest"` 明确拒绝；源码提供行号、当前 SHA-256、固定 commit 链接，并区分是否存在已记录哈希。
- 文档行号分页、关系邻居分页实际可用；工具限制路径和返回窗口，服务不依赖网站 HTTP 运行。
- 记录已有 CPU A/B 条件与证据边界，不把更多迭代、关联实验或关系图邻接当成通用调参建议或因果证明。

## 2. 验证范围、口径与产物

本次读取了 PRD、现有构建/检索/MCP 核心实现、生成目录与关系图，以及固定快照的公开导出、文档导航和相关源码。目标目录及上级没有发现额外 `AGENTS.md`；源码快照中的 `AGENTS.md` 已读取。本次审核产品需求与知识服务，不修改或提交 Newton 源码，不进行 Newton 代码改动评审。

独立客户端使用 `mcp_service/.venv/Scripts/python.exe` 启动 `server.py` 子进程，在 `planning/review` 下执行，未依赖父会话已连接的 MCP。服务发现为 `newton_knowledge 1.1.0`，协商协议为 `2025-11-25`。共 **50 次 tools/call**，其中 6 次返回预期错误，其余 44 次协议成功；协议成功包含空命中，不能算任务成功。

可复查产物：

- [公开 API 与现有数据盘点](<D:/RAG/Newton knowledge/planning/review/inventory.json>)
- [MCP 工具实际 schema](<D:/RAG/Newton knowledge/planning/review/mcp-schema.json>)
- [首批 34 次调用原始结果](<D:/RAG/Newton knowledge/planning/review/mcp-call-results.json>)
- [补充 16 次调用原始结果](<D:/RAG/Newton knowledge/planning/review/mcp-extra-results.json>)
- [独立客户端](<D:/RAG/Newton knowledge/planning/review/audit_mcp.py>)、[补充客户端](<D:/RAG/Newton knowledge/planning/review/audit_mcp_extra.py>)

PRD 审核时 SHA-256 为 `1c31e25e70aeebdc6cda0d37e1829f0872ace3f742e1161cb72a89a93f0c352d`，与父任务记录一致。只新建审核文档及辅助产物；没有重建网站/索引，没有修改 PRD、服务或固定快照，没有注册全局 MCP。

**限制：** 没有执行完整物理测试、GPU 或新 A/B 实验；没有做浏览器交互与回放视觉验收；没有联网核验 latest；没有重新认证整个快照的 Git 对象。源码事实按给定固定本地快照核对。以下“当前缺口”指整理/索引/任务路径的缺口，不表示源码本身不存在相关能力。

## 3. 覆盖分母与主要模块矩阵

### 3.1 使用三个互补分母，不混成百分比

1. **公开 API 入口：12 个。** 来自 `docs/api/_toctree.rst:9–20`：`newton` 顶层，加 `actuators/controllers/geometry/ik/math/selection/sensors/solvers/usd/utils/viewer`。这衡量模块入口是否被覆盖，不代表每个 API 符号同等重要或已深入解释。
2. **官方 Concepts 主题：14 个。** 来自 `docs/index.rst:31–44`：Worlds、Articulations、Deformable Objects、Mass and Inertia、Sites、Sensors、Conventions、USD Parsing、Custom Attributes、Solver Observables、Collisions and Contacts、Simulation Tuning、Coupled Solvers、Actuators。每项至少要有目标页面/可检索记录，或明确“仅索引/待收录”。
3. **具体 solver backend：8 个。** 来自 `newton/_src/solvers/__init__.py:19–30` 及 `docs/solvers/index.rst`：Featherstone、ImplicitMPM、Kamino、MuJoCo、SemiImplicit、Style3D、VBD、XPBD。**不计 SolverBase 抽象基类；不把 `style3d` 模块重复计为 solver；experimental coupled 框架单独审核，不硬塞进八个 backend 的分母。**

官方只为 MuJoCo、Kamino、VBD 设置独立 solver guide，不表示其他五个 backend 不属于公开范围。PRD §2 允许其他 solver 作为待收录入口是合理的，但应把“可作为”改为可验收的入口清单。

当前生成数据的实际规模为：31 篇可读文档（每个 solver 8 篇，shared 7 篇）、367 条搜索记录、169 条参数记录（包含必填 model 及不同层级配置）、45 条模型输入、968 个图节点、776 条边。VBD 有 17 组/34 次保存的 A/B；MuJoCo/Kamino 均没有保存的 A/B。169 不是“169 个可选构造参数”，968 也不是“968 个已解释知识点”。图中 650 个节点为源码符号；没有 `stage`、`concept`、`document` 节点。shared 的 7 篇主要是接入、维护、验证及 VBD 实验说明，不是 Newton 公共概念知识全集。

### 3.2 模块覆盖矩阵

表中“完整库”表示长期应该具备的知识面；“首期”是建议最小交付深度。当前“未建立独立入口”不排除某篇 solver 文档中零散提及，也不否认 `get_source` 能在已知路径时读到源码。

| 模块/主题 | 固定版本证据 | PRD 当前承诺与当前实现 | 完整库应覆盖 | 建议首期深度 |
|---|---|---|---|---|
| 核心对象与生命周期 | `newton/__init__.py:85` 起；`_src/sim/{builder,model,state,control,contacts}.py` | §3/4 明确规划；当前以 solver 文档零散解释 | Builder→Model→State/Control/Contacts/Observables，分配、复位、更新 | 一篇公共契约页与三种接触路径配方 |
| 几何、质量惯量、碰撞 | `newton/geometry.py`；`docs/concepts/{collisions,mass_inertia}.rst` | §4/5 明确；现有 full-surface 和 VBD 参数较深 | Mesh/TetMesh/SDF/Heightfield、broad/narrow phase、材料、过滤、容量、hydroelastic | 公共定义+能力表；full-surface 深入样板 |
| 资产与 USD | `ModelBuilder.add_urdf/add_mjcf/add_usd`；`newton/usd.py`；`usd_parsing.rst` | §4 明确规划；F6 查询 URDF 无命中 | URDF/MJCF/USD 语义、schema、坐标/单位、视觉碰撞差异 | 导入入口、常见陷阱、固定 API/示例索引 |
| 约定与数值/空间数学 | `conventions.rst`；`newton/math.py` | §4/6 提及单位，math 无明确归档 | 变换、四元数、twist/wrench、质心/原点、力和速度表达 | 约定速查；数学函数索引，不要求逐函数教程 |
| Worlds 与批量选择 | `worlds.rst`；`newton/selection.py` → ArticulationView | §3/4 仅点到 worlds；selection 未列；B2 无命中 | replicate、全局 world=-1、异构支持、索引/视图、掩码 reset | 公共专题与 solver 支持表 |
| Articulations 与约束 | `articulations.rst`；`docs/solvers/index.rst:191` 起 | §4 模型层级与关节姿态，主题粒度不足 | 关节树/闭环、坐标表示、mimic/equality/tendon、关节支持 | 基本模型页+八 solver 关节能力索引 |
| FK/IK 与动力学辅助 | 顶层 eval_fk/eval_ik/eval_jacobian/eval_mass_matrix；`newton/ik.py` | 无明确独立承诺 | 运动学目标、IK 求解器、雅可比/质量矩阵、初始化与控制衔接 | 概述+API/例子定位，必须可搜 |
| Controllers | `newton/controllers.py:13–32` | §5 写“控制器”，未列具体模块；B1 无命中 | DifferentialIK、JointImpedance、OperationalSpace、model-free 差异 | 与 Control、IK、selection 的关系配方 |
| Actuators | `newton/actuators.py`；`actuators.rst` | §5/8 明确；当前主要为 solver 驱动参数 | Drive/Clamping/Delay、解析、显隐式支持、神经驱动依赖 | 模块入口与执行链；复杂神经驱动后置 |
| Deformable objects 与 Rod | `deformable_objects.rst`；顶层 Rod、TetMesh；builder | VBD 内容较深，但整体对象建模未明确独立主题 | cloth/soft/particles/rod、材料与离散化、MPM 边界 | 公共对象概述+VBD 深入+MPM/Style3D 入口 |
| 八个具体 solver | `newton/_src/solvers/__init__.py`；`docs/solvers/index.rst` | §2 三个深入、其余“可”待收录；当前仅三者注册 | 能力/关节/材料/设备/可微限制，独立版本证据 | 八者都可发现；三者深入、五者明确索引级 |
| Coupled solvers | `docs/concepts/coupling.rst:11–42`；`solvers.experimental.coupled` | §2 分类交叉不等于耦合；未明确列入；C1 无命中 | ModelView、ownership、Proxy/ADMM、子步与反馈、接触/attachment | 独立跨 solver 主题，先机制与例子，无须新物理实验 |
| 可微仿真 | `docs/solvers/index.rst:462` 起；`newton/examples/diffsim` | 未明确列入；F5 requires_grad 无命中 | requires_grad、Tape、状态历史、可微能力限制 | 选型与可微流程概述，深度实验后置 |
| Sites、Sensors、Observables | `sites.rst`、`sensors.rst:184`、`solver_observables.rst`；`newton/sensors.py` | §4 提及 sensors/observables，Sites 未明确；B5/F13 无命中 | 相机/IMU/Contact/FrameTransform，结果分配与采样时间 | 从初始化到量测的完整配方，不只列输出名词 |
| Viewer/记录/回放 | `newton/viewer.py`；`docs/guide/visualization.rst` | §4/8 明确；现有主要是自建 VBD 回放 | GL/RTX/USD/Rerun/Viser/File/Null 的用途、依赖与调试 | 官方 viewer 选择索引，区分知识库实验回放 |
| 自定义属性与运行期更新 | `custom_attributes.rst`；SolverBase.register_custom_attributes/notify_model_changed/reset | §3/5 已点到，缺时序与字段约束 | 注册前置、构建解析、ModelFlags/StateFlags、缓存与图重建 | 生命周期配方与各 backend 的更新限制 |
| Utils、资产和性能工具 | `newton/utils.py`，含 color_graph、mesh、cable、download_asset、EventTracer | §4 着色/网格、§7 性能计时部分覆盖；无总体入口 | 预处理工具、资产依赖、基准、性能与调试 | 工具地图；只对流程必需项做深 |
| 安装、兼容、开发测试、迁移/集成 | `docs/guide/{installation,compatibility,development}.rst`；`migration.rst`；`lab/isaac-lab.rst`；tests/examples | §6 开发测试清楚，安装/兼容/迁移/集成覆盖不明确 | 可运行环境、公共 API、测试、版本迁移、外部集成边界 | 环境/兼容/官方测试入口必有；集成先链接级 |

以上矩阵不是按 18 行算覆盖率。行是便于审核的主题聚合，底层 12 个 API 入口与 14 个官方概念必须逐项映射；同一条知识可以服务多个主题。建议为每项记录 `indexed / explained / task_validated / experiment_validated / explicitly_deferred` 等覆盖状态，分别统计入口覆盖与任务深度。

## 4. 按优先级排序的问题与修改要求

此处 **P0 表示实施版冻结前需决策的产品契约问题**，不是已发现物理引擎崩溃或安全事故；P1 是首个可用版本应修复的任务断点；P2 是扩展效率与维护质量。

### P0-01：范围目标没有可验收的模块分母

- **PRD 位置：** §1、§2、§4、§11–13，特别是 §2“其他 solver 可作为……待收录项”、§11 P2“每阶段一篇概述”。
- **证据：** 官方 API 有 12 个入口，Concepts 有 14 个主题；八 backend 中仅三个有专属 guide。当前目录 31 篇，shared 7 篇尚不是公共 Newton 核心内容。B1/B2/B5/C1/F3/F5/F6 分别暴露 controllers、selection、sensors、coupled、XPBD、可微、导入的发现缺口。
- **影响：** 即使五阶段各写一篇，仍可能通过 PRD 验收却无法回答大量 Newton 任务；也会让团队误把“三 solver 深度”与“整体知识覆盖”混为一谈。
- **可执行修改：** 在 §2 后增加覆盖清单附件，逐项列 12 API 入口、14 Concepts、八 backend 和耦合框架；每项填写首期深度、目标稳定 ID/页面、来源、明确延后项。其他 backend 至少必须可搜、可定位、显示未深入状态；不要求首期增加其参数实验。

### P0-02：首版含 agent 目标，却把最小 MCP 任务能力整体后置

- **PRD 位置：** §1 的人/agent 双用户目标，§9“逐步支持”，§11 首版 P1+P2，§12 场景 9。
- **证据：** `server.py:44` 起的 search schema 只有 query/kind/limit/version/solver，没有 domain/stage；当前三个跨模块场景均不能完整沿检索路径完成。§12“返回正确范围与出处”没有定义怎样证明正确、零结果意味着什么、如何继续读取。
- **影响：** 网站可上线公共页，但 agent 仍只能围绕旧 solver 目录工作；“第一版可用”对两类用户的含义不一致。
- **可执行修改：** 保留物理实验后置，将公共模块发现、范围语义、稳定 ID、精确续读、搜索翻页、空缺反馈及下述场景集移到首版验收。P3 保留深层算法/诊断扩充，不再承担基础 MCP 契约首次落地。若首版确实只面向人，应在 §1/§11 明示该版本 agent 范围，而非笼统称双用户可用。

### P1-01：定义所有者、适用 solver 与证据来源尚未成为不同字段

- **PRD 位置：** §5 full surface 样板、§7 参数归属、§9 `solver 归属与适用条件`。
- **证据：** A2 已正确返回 owner=`CollisionPipeline.__init__`、layer=`collision_pipeline`，但 envelope 仍是 VBD；A3 公共 pipeline 节点无 solver 字段，`knowledge.py:435` 默认标成 VBD。`knowledge_search.py:44–45` 仅允许 `row.solver == requested_solver`，shared 文档被过滤；E7 与 E8 实测确认。当前 schema 也不能单独请求 shared。
- **影响：** 公共定义可能找不到或被误判为 VBD 专属；反方向把 shared 当全 solver 支持同样错误。现有 VBD 实测不能自动证明 MuJoCo full-surface 支持，A5/A6 的空缺也不能证明不支持。
- **可执行修改：** 明确 `owner`、`module`、`applicable_solvers[]`、`backend_conditions`、`support_status`、`experiment.solver`；`stages[]` 允许跨阶段。定义 `solver=X` 是精确归属查询还是“X 加适用公共内容”，推荐提供显式 `include_shared`，并依据适用条件纳入，不能无条件混入全部 shared。公共参数支持稳定 ID 或 `scope=shared` 精确读取；旧隐式 VBD 返回 `scope_resolution=legacy_default`，每条 next_call 显式带 solver/version。公共定义与 VBD 实验通过边连接。

### P1-02：耦合与运动学等跨模块知识没有第一归属

- **PRD 位置：** §2 目录、§3 核心对象、§4/5 流程、§11 P2。
- **证据：** `coupling.rst:11–42` 公开 ModelView、CouplingInterface、SolverCoupled、Proxy/ADMM；现有 C4 正确说明 external-rigid 选项本身不是双向耦合，但 C5 图只到 VBD 的两个结论、构造源码与 solver，没有耦合框架。Controllers、IK、selection 是分别公开的模块。
- **影响：** 用户要 MuJoCo 刚体带 VBD 布料时，会得到局部限制却找不到实际组合路径；把控制器仅归入 Control 小节，容易遗漏 IK→视图选择→目标布局→执行器的接口链。
- **可执行修改：** 流程主导航不必再增大量一级栏目，但需增加独立“跨阶段主题索引”：机器人运动学与控制、Worlds/批量、耦合、可微、模型更新/复位。耦合同时被 solver 能力页和 step 页引用；解释 ownership、每 entry 子步、force/pose 交换、contacts 和 attachment 支持。配方的 `solver_ids` 应允许数组，不能只有一个当前 solver。

### P1-03：搜索不能穷尽结果，范围过滤与排序也需要明确契约

- **PRD 位置：** §9、§12 场景 9。
- **证据：** E1 `iterations, limit=2` 和 E2 `limit=20` 均 `has_more=true`，但 search schema 没有 offset/cursor；`knowledge.py:124/163` 只返回布尔值。`knowledge_search.py:38` 先取全局 FTS 前 300，再在第 44 行按 solver 过滤。`build_index.py` 与 `site/build_site.py` 对 VBD 同时建立章节与整页记录，C2 出现 implementation 章节+整页重复。
- **影响：** agent 不能完整盘点某类型内容；扩大 limit 增加 token 但仍可能漏掉结果。语料扩展后先全局截断再筛范围存在漏召回风险；这一风险是代码推断，当前未通过构造大语料重现。
- **可执行修改：** search 增加稳定分页 cursor、`next_cursor`、`applied_filters`、匹配范围说明；先做范围/类型过滤再排序；章节命中返回精确 section/line，避免整页抢占结果。分页稳定键绑定 index build ID。至少让所有 hits 可遍历，空结果明确说明搜索的是整理索引而非整个源码仓库。

### P1-04：搜索与关系图尚不能为所有记录提供完整续读

- **PRD 位置：** §8、§9、§12 场景 7/9。
- **证据：** `knowledge.py:143–156` 只为实验、参数、文档设置 next_call；claim/diagnostic/mapping/paper 没有统一精确读取工具，source_refs 最多取两条。图节点含 `record_file` 但 `get_document` 只接受目录内 Markdown，不能直接按该 JSON 文件或记录 ID 取完整正文。A3 只有一条 experiment 边，没有公共流程/源码节点。图整体没有 stage/concept/document 节点。
- **影响：** 命中诊断后可能只能读 500 字符摘要、邻接标签或另行猜文档路径；标题路径虽可供人点网页，agent 无法稳定恢复完整诊断步骤与证据链。
- **可执行修改：** 不必增加第七工具：可扩展 `get_document(record_id=...)` 返回规范正文或章节，或给所有 hit 生成可执行 document/section 读取参数；图邻居同样携带 read/relations/source 的 next_call。约定公共概念→API/参数→来源，以及参数→诊断/实验的必需边；没有实验的边应返回明确缺口，不生成虚构关联。对返回的全部 next_call 做自动可执行性校验。

### P1-05：流水线讲解缺少跨阶段分配与更新顺序的验收

- **PRD 位置：** §3、§4 初始化/输出、§5 solver step。
- **证据：** `solver_observables.rst:39–88` 要求 contact-indexed observables 在容量已解析后分配，绑定同一个 contacts，容量被冻结；`sensors.rst:184–207` 把 SensorContact/IMU 与 observables、step、state_out 连接。`SolverBase.step` 的 observables 参数在 `solver.py:1031`，`reset:1003`、`notify_model_changed:1056`、旧 `update_contacts:1109` 弃用也影响正确用法。PRD 已正确提示外部/内置 collision，仍未把这些依赖写入交付要求。
- **影响：** 五段概述都正确，但 agent 按分散片段拼接代码仍可能在容量、buffer 身份、采样时点、reset 或缓存更新上出错。
- **可执行修改：** P2 至少交付外部碰撞、solver 持有碰撞、MuJoCo 原生碰撞导出三条带顺序的 recipe，并加一条跨 solver 耦合索引；每条说明 setup/每子步/每控制帧/每输出帧/复位更新。Sensors 是输出消费者，但其分配请求必须回链初始化阶段。加入 target_q 的坐标布局与 target_qd 的 DOF 布局区别，引用顶层 `use_coord_layout_targets`，避免仅写“关节目标”。

### P1-06：规划筛选字段被静默忽略，错误/空缺状态未定义

- **PRD 位置：** §9 兼容策略、§12 场景 9。
- **证据：** E9 传 `stage="collision"` 得到协议成功；F2 不传 stage 的返回与 E9 **完全相同**。发现 schema 中没有 stage，所以这不是“已实现 stage 筛选的回归”，而是现有 SDK/服务对未知参数静默忽略的契约缺口。未知 solver `xpbd` 返回枚举验证错误；未知版本与无实测返回明确错误，表现较好。B1/C1/F3 等真实能力名与 E3 随机构造词均返回相同形态的 `hits=[]`。
- **影响：** 新旧客户端或手写调用可能以为筛选已生效；agent 无法区分未整理、词未匹配、solver 不支持、没有实测、读取不支持。
- **可执行修改：** 未支持字段必须明确拒绝或返回 `ignored_arguments`，不能悄悄成功；返回 `applied_filters`。定义 `not_indexed / no_match / unsupported_feature / no_measured_evidence / unsupported_version` 等机器可读状态与建议下一步，只有有能力证据时才能返回 unsupported_feature。覆盖清单驱动未整理提示，不能靠 LLM 猜“没有搜到就是不支持”。

### P2-01：token 开销有局部边界，尚无任务级预算

- **PRD 位置：** §9、§12。
- **证据：** E2 的 20 条搜索结构化负载为 14,481 字符；get_document 无路径返回所有 31 篇目录，3,560 字符；A4 实验 summary 5,881 字符，F9 full 6,769 字符。MCP 实际回包同时含 structuredContent 和文本表示：E2 完整序列化 33,914 字符。不同客户端是否把两份都注入模型上下文未验证，不能把传输长度直接当 token 用量。每页文档还重复完整 headings；18,000 字符限制只覆盖正文窗口，不是总回包上限。
- **影响：** 多轮跨模块取证时摘要、路径、URL、限制说明和重复文档会吞噬预算；现有 limit 不能直接保证任务 token 成本。
- **可执行修改：** 提供紧凑摘要/字段选择，目录分页，章节定位及明确 total/truncation；统一 `max_chars` 或可测响应预算。验收分别记录实际客户端入模 token、逻辑内容字符、完整回包字节，不混为一谈。优先解决重复章节/整页、重复三种本地 URL，而非先换向量数据库。

### P2-02：迁移规则尚未覆盖生成链与自动范围校验

- **PRD 位置：** §9–11。
- **证据：** `site/build_site.py:15` 的 DOCS 与 `scripts/build_index.py` 仍硬编码 solver；site 构建调用 `extend_solvers()`。当前图公共 pipeline/process 节点未带范围，实验方法 README 因路径不在 solvers 下被标 shared。`site/dist/app.js:46–47` 有裸 VBD 导航。仅搬 Markdown 或修改 dist 会被下次构建覆盖。
- **影响：** 页面迁移看似完成，重建后退回旧分类；路径推断把“站点公共入口”与“物理内容适用范围”混同，旧 ID/关系/深链接可能断裂。
- **可执行修改：** P0 迁移清单增加 authored/generator/generated/index/route 五列；明确唯一内容源及 solver registry。P1 必须运行“源→catalog→graph→SQLite→route”的一致性校验，验证无孤立 next_call、无裸 solver 回退、ID 不变、显式重定向及深链接参数保留。不要把 generated 文件当长期编辑入口。

### P2-03：固定 commit 标签还需要更细的来源与构建一致性状态

- **PRD 位置：** §8/9/11 P5。
- **证据：** `knowledge.py:42–48` 只检查 catalog 的 version/commit；search DB、graph 和文件没有共同 build ID 校验。`get_source:538–567` 仅对 inspected-file manifests 里有记录的文件验证原始哈希。A7/F1 的 collide.py、B6 controllers.py、C6 coupling.rst 都返回 `matches_recorded_hash=null` 并说明原因，未冒充 hash 已匹配，但仍统一标 `pinned_source_excerpt`。
- **影响：** 公共知识扩展时，“返回了当前哈希”和“核对了固定快照哈希”容易被混读；部分重建可能使目录、关系、检索来自不同内容世代。此处是维护风险，没有观察到本次已发生数据错配。
- **可执行修改：** 保存整份源快照或所有被引用文件的锁定 manifest；把 provenance 标为 `verified_snapshot / local_snapshot_unverified_file` 等。catalog/graph/SQLite/records 统一 build ID，服务拒绝或明确提示混合构建。按 API 签名、默认解析和来源 hash 做增量变更检查，P5 不只写“持续维护”。

## 5. MCP 实际签名与可用边界

以下是本次发现的当前工具，不是 PRD 未来实现：

| 工具 | 当前关键签名 | 验证结果与边界 |
|---|---|---|
| search_knowledge | query；kind；limit=6（1–20）；version=1.7.0；solver=all/vbd/mujoco/kamino | 有词法检索及中英文扩展；无 domain/stage/shared 筛选，无分页；has_more 可真 |
| get_parameter | name；version；solver=vbd | 同名默认正确；兼容默认 VBD 未另行标记；公共输入只有现有特例，Control 全集不在记录内 |
| get_experiment | experiment_id；detail=summary/full；version；solver=vbd | 17 个 VBD 案例读取；MuJoCo/Kamino 无 A/B 明确报错；exp: CPU 探针不走此 reader |
| get_relations | node_id；limit=12（1–30）；offset；version | 有一跳邻居分页；最多 80 边并标 edges_truncated；无全记录正文读取 |
| get_document | path=""；section=""；start_line=1；max_lines=100（≤200）；version | 空路径列白名单全部文档；精确标题和原始行号可用；当前没有公共流程页 |
| get_source | path；start_line=1；max_lines=100（≤200）；scope=newton/experiment；version | 可读取快照内允许文本文件；实验仅两个程序；知道路径后可取证，没有源路径/符号发现接口 |

保留六工具足够。缺的主要是输入/返回契约与知识记录连接，不是工具数量。需要扩展六工具的可选参数或精确读法，同时保留旧调用；并对将来旧调用省略范围的情况给出明确兼容提示。

## 6. 跨模块任务场景与实际调用结果

### 场景 A：球穿过粗三角布面，定位碰撞设置并判断能否迁移到另一 solver

涉及公共几何/碰撞、VBD、实验、MuJoCo 能力判断。调用 A1–A7、F1。

1. A1 `search_knowledge("full_surface 穿模", solver="vbd", limit=5)` 将 `lab:full_surface` 排在第一，带实验 next_call；这一任务发现有效。
2. A2 参数读取确认真实 owner 是 CollisionPipeline，声明默认 False，且不是 SolverVBD 构造参数。
3. A4 读取保存的 A/B 配置、量测、环境与观测；F1 用 A2 返回的 `collide.py:1338` 阅读源码依据。局部证据链成立。
4. A3 从 pipeline 节点只获得一个实验邻居；没有公共碰撞概念/源节点。A5 切到 mujoco 搜索 `CollisionPipeline full surface` 无命中，A6 精确读同参数报 PARAMETER_NOT_FOUND。

**判定：部分完成。** 能解释 VBD 已记录案例；不能沿当前检索证据链完成跨 solver 适用性判断。不得把空命中当作 MuJoCo 明确不支持，也不得迁移 VBD 实验结论。A7 保留了现有文档示例的硬编码 1275 行探查；正式证据定位采用动态返回的 F1 行号。

### 场景 B：导入多机器人，使用 IK/控制器下发 MuJoCo 目标，再读取接触力

涉及资产导入、Worlds/selection、IK/controllers、Control、MuJoCo、Sensors/Observables。调用 B1–B6、F6、F10–F13、F15。

- F6 URDF、B1 ControllerDifferentialIK、B2 ArticulationView、B3 joint_target_q（mujoco）、B5 SensorContact 均无命中。
- B4 读取 joint_target_q、F10 读取 body_f 报 PARAMETER_NOT_FOUND；这表示当前参数记录未涵盖所需输入，不表示 Newton 不存在这些接口。
- F11 `use_mujoco_contacts` 参数可以读取；F12 “Solver Observables”命中部分 VBD 结论/实现与 MuJoCo disable_sensors，但 F13 精确 contact_f 无命中，无法形成传感器链。
- B6/F15 在审核者已知文件路径后成功读到 controllers 公共导出、SensorContact 必须请求 CONTACT_F 并复用 contacts 的官方要求。

**判定：未完成。** 知道路径后的源码阅读是有效逃生通道，但不是当前知识检索自主发现能力。缺的不只是文章数量，还有 setup 分配→Control 布局→step→sensor.update 的顺序和跨阶段关联。

### 场景 C：MuJoCo/Kamino 刚体与 VBD 布料双向耦合，检查 attachment 和子步归属

涉及多个 solver、ModelView、碰撞与状态同步。调用 C1–C6。

- C1 搜索 SolverCoupledADMM 无命中。
- C2 搜索 coupling 命中 VBD implementation 的章节与整页、Kamino DVI 的 bilateral_solve_interval 等，没有公共耦合入口。
- C3/C4 成功读取 integrate_with_external_rigid_solver，明确“这个选项本身不构成双向耦合”；这是有价值的边界提醒。
- C5 图只有相关 VBD 结论、SolverVBD 构造源码和 solver 节点，没有 Proxy/ADMM 框架。
- C6 已知 `docs/concepts/coupling.rst` 路径后，可读到完整公开框架入口及 ownership/entry 子步。

**判定：未完成。** 已有数据能避免一个错误推断，却不能从局部限制继续定位正确实现方案。应把 coupled 作为跨 solver 桥接主题，不能仅用“solver 分类允许交叉”替代。

### 场景 D：比较三个 solver 的迭代预算并要求实测依据

涉及 VBD/MuJoCo/Kamino 配置与实验层。调用 D1–D4。

- VBD iterations 返回声明/解析 10，关联 VBD iterations 实验。
- MuJoCo iterations 返回声明 None、模型/后端解析策略，documentation 给出后端默认 100。
- Kamino config.padmm.max_iterations 返回声明/解析 200，并提示看三个残差与 converged。
- 请求 MuJoCo iterations 实验明确返回 NO_MEASURED_EXPERIMENTS。

**判定：在限定问题内完成。** 可完成默认与证据存在性比较；不能据此排名 solver 性能或推荐跨 solver 等值迭代预算，也未在本次重新核验所有默认解析分支。

### 辅助边界测试

| 调用 | 实际结果 | 意义 |
|---|---|---|
| E1/E2 iterations，limit=2/20 | 均 has_more=true，无 next cursor | 搜索无法穷尽 |
| E3 不存在的标识符 | hits=[]，通用 limitations | 未区分 no-match 与未整理 |
| E4 省略 solver 读 iterations | 返回 VBD，未提示兼容默认 | 正确兼容，但范围解析不透明 |
| E5 version=latest | UNSUPPORTED_VERSION | 固定版本边界有效 |
| E7/E8 agent 文档，mujoco/all | mujoco 范围排除 shared 接入页 | 共享范围过滤需明示 |
| E9/F2 有/无未实现 stage 字段 | 返回完全相同 | 未知参数静默忽略；不是现有 stage 功能回归 |
| E10/E11 文档 1–5/6–10 行 | next_start_line=6/11 | 行号续读正确 |
| F7/F8 关系 limit=1 offset=0/1 | total_neighbors=7，next_offset=1/2 | 邻居分页正确 |
| F4 solver=xpbd | 明确枚举校验错误 | 当前只支持三 solver 的范围参数 |

### 上下文与 token 成本

没有对某个模型运行 tokenizer，以下是实际返回字符数，**不是 token 数**：

| 调用 | 结构化逻辑负载字符 | 完整 MCP JSON 字符 |
|---|---:|---:|
| A1：5 条搜索 | 4,462 | 10,541 |
| A4：full_surface summary | 5,881 | 13,900 |
| E2：20 条搜索 | 14,481 | 33,914 |
| E6：31 篇目录 | 3,560 | 9,019 |
| F9：full_surface full | 6,769 | 17,206 |

VBD 局部闭环 A1→A2→A4→F1 的逻辑负载合计 13,961 字符；公共关系和跨 solver 查证还会继续增加。当前 full 不返回整条轨迹是合理取舍，但未来场景初始几何规模增大时，仍需总响应预算，而非只靠行数限制。

## 7. 建议的信息架构与记录契约修订

保留现有两条主阅读路径，增加明确的公共知识地图：

- **流程路径**回答“现在在做哪一步”：导入、预处理、初始化、控制/碰撞/求解、输出。
- **模块/主题索引**回答“我要找哪个接口体系”：对应 12 API 入口、14 Concepts；Worlds、IK、coupled、可微等可由多个阶段引用。
- **solver 路径**回答“这个 backend 如何实现、支持哪些功能”：三个深入专区与五个索引级入口，能力比较表包含证据和版本。
- **开发/维护路径**区分上游开发测试、知识构建校验、MCP 合约测试和物理实验。

§9 建议明确以下字段，而不是只有自然语言栏目名：

| 字段组 | 建议最小契约 |
|---|---|
| 身份 | stable_id、record_type、schema_version；标题变化不换 ID |
| 归档 | owner_module、domain、stages[]、primary_topic；页面只是投影 |
| 适用性 | applicable_solvers[]、backend/device/feature 条件、supported/unsupported/unknown；unknown 不等于 unsupported |
| 覆盖 | indexed/explained/task_validated/experiment_validated/deferred，附缺口原因 |
| 证据 | 每条断言关联 source_ref/experiment_id；证据方法与运行状态分开；无实验也可有源码支持 |
| 读取 | canonical_document/section/line、read_next_call、source_next_call、relation_node_id |
| 版本 | Newton version/commit、source hash、content/index build ID |
| 范围解析 | requested_scope、resolved_scope、applied_filters、compatibility_warning |

证据状态应允许并存：一个公共定义经源码核对，同时有“仅 VBD 某案例实测”边；不能把整条公共定义升级为“所有 solver 实测”。内容覆盖状态、功能支持状态、证据等级与实验执行状态是不同维度。

## 8. 建议的阶段计划与可执行验收指标

以下是对原 P0–P5 的修订建议，不是已经实施的能力。数量门槛是建议的验收合同，不是本次测得的覆盖率。

| 阶段 | 调整后的交付 | 建议验收 |
|---|---|---|
| P0 范围与合同 | 覆盖清单、稳定 ID/归属/适用性 schema、六工具扩展设计、生成链迁移表 | 12 API 入口、14 Concepts、八具体 backend、coupled 均有明确目标记录与首期深度；无未决归属；三个跨模块场景写出答案要点与必须证据 |
| P1 数据与导航同步迁移 | 公共 registry、统一专区/模板、旧链接映射、构建一致性 | 原有 31 篇文档、17 A/B、169 参数记录及其稳定 ID 有迁移映射；分类含义变化可解释；深链接逐个验收；任意 solver 页面导航不隐藏回退 VBD；catalog/graph/index build ID 一致 |
| P2 公共骨架与 MCP 最小可用 | 五阶段、完整模块索引、生命周期配方、公共概念、检索范围/分页/精确续读 | 每个必需模块至少有摘要、固定版本出处、公共 API 路径、例子/测试入口、覆盖状态；上面 A/B/C 场景可从检索进入并给出有证据的答案或明确缺口；不用审核者预知内部路径 |
| P3 任务深度 | 控制、碰撞、求解器差异、coupled、批量复位/量测等任务包 | 增加至少 12 个冻结查询任务，含中文问题、英文符号、同名参数、公共+solver、无实验、缺失模块、版本拒绝与歧义；每个有 required record IDs 和 forbidden conclusions |
| P4 多 solver 实验 | 原建议 MuJoCo 两组后 Kamino 两组可保留 | 每组明确 config diff、场景、依赖/设备、时长、采样、计时/预热、metric/unit、raw hash、run ID；失败/环境受限可记录但不算“完成实测”；运行完成与物理有效性分开判定 |
| P5 维护 | API/源码差异监测、coverage ledger、增量索引与证据失效 | 每次内容更新校验 source hash、断链、scope、索引 build；每次 Newton 版本扩展单独兼容矩阵，不静默复用旧默认/实验结论 |

验收报告必须分别报告三类口径，不能用文档、参数或图节点数量代替：

| 口径 | 分母与通过条件 | 本次状态 |
|---|---|---|
| 主要模块入口覆盖 | 冻结的 12 API 入口、14 Concepts、八 backend 清单分别统计；每项有可发现入口、来源、深度与缺口状态才计入；coupled 单列 | 已建立本报告盘点基线；当前不能宣称完整覆盖 |
| 显式跨模块关系连通 | 冻结的 required-path 清单，例如 controller→Control→solver、SensorContact→CONTACT_F→step、coupled→ModelView→子 solver、full-surface→定义→实验；要求两端可精确读取、边有语义与来源 | A3/C5 证实关键路径缺失；不能用 776 条边代表连通通过 |
| Agent 端到端任务完成 | 冻结的任务集合，以正确范围、结论、完整证据、负面边界与调用预算联合判定；不依赖预知内部路径；协议成功不计任务成功 | 本次四个设计场景：A 部分完成，B/C 未完成，D 在限定问题内完成；样本不代表全库成功率 |

建议在 P2/P3 增加机器可测的发布门槛：

1. **发现质量：** 对覆盖清单中每个主要模块，精确模块名/API 名查询能在前 5 条找到入口；中文任务查询以冻结的相关记录集合评估 Recall@5/MRR，不用“搜到任意文档”算成功。
2. **范围正确性：** 同名参数、shared+solver、单 solver 和多 solver recipe 的结果归属无歧义；没有对应支持证据时返回 unknown。未知筛选字段不得静默生效。
3. **证据连通：** 每条命中至少有一个可执行精确读取入口；数值默认有声明/解析来源；所有返回 next_call 可成功；公共概念到来源、案例到定义的必需路径逐项验收。
4. **分页完整性：** 对所有超过页长的测试查询，cursor 翻到末尾与基准结果集合一致，不重复、不遗漏；关系边截断也有可恢复读法或明确不可穷尽状态。
5. **任务成本：** 固定的局部参数取证任务原则上 4 次读取内拿到默认、范围、源码、实测存在性；完整跨模块任务设 8 次读取的初始目标。达不到时记录失败原因，而非人为删证据。紧凑 search 5 条建议不超过 6,000 逻辑字符，超出时提供摘要/续读；实际 tokenizer 指标随目标 agent 客户端一并记录。
6. **负面边界：** `not_indexed`、`no_match`、`no_measured_evidence`、`unsupported_feature`、`unsupported_version` 各有用例，禁止从空命中推断能力不存在；proposed 诊断不得返回为 measured。
7. **复现与迁移：** 网站功能验证、知识结构验证、MCP 任务验证、物理量测四类报告独立列出，不相互替代。

第一版仍可命名为 P1+P2，但 P2 应包含上述最低 agent 契约。算法深化与新物理实验继续不阻塞结构/公共知识上线。

## 9. 精简的优先修改清单

1. 给 §2 增加 **12 API / 14 Concepts / 八 backend + coupled** 覆盖附表；声明三 solver 深入、其余入口级的首期边界。
2. 给 §9 拆开 **owner、适用 solver/backend、覆盖状态、证据状态**；`stage` 改为可多值，公共内容不能按路径或默认 VBD 推断。
3. 把 **MCP 最小范围契约、可分页检索、精确续读、未知参数/空缺反馈** 提前到 P2；P3 只加深度。
4. 把 **IK/controllers/selection、coupled、Worlds/reset、Sensors/Observables、可微** 写成有目标页面和证据的跨阶段主题。
5. 将本报告 A/B/C/D 场景加入 §12，使用真实 MCP 调用结果和证据 ID 验收；不要只验证工具能连接。
6. 在迁移表中列出 **源文件→生成器→catalog/graph/index→路由**，保证重建与旧 ID/链接兼容。
7. 保留现有证据边界与三 solver 参数读法；新实验仍独立排期，不用增加实验数量替代知识发现和证据连通。

## 10. 主要文件证据索引

以下链接指向本次实际审查的文件；上文行号用于快速定位。

- [PRD](<D:/RAG/Newton knowledge/planning/PRD.md>)
- [公开导出 newton/__init__.py](<D:/RAG/Newton knowledge/sources/newton-v1.7.0/newton/__init__.py>)
- [官方 API 导航](<D:/RAG/Newton knowledge/sources/newton-v1.7.0/docs/api/_toctree.rst>)、[官方 Concepts 导航](<D:/RAG/Newton knowledge/sources/newton-v1.7.0/docs/index.rst>)
- [具体 solver 导出](<D:/RAG/Newton knowledge/sources/newton-v1.7.0/newton/_src/solvers/__init__.py>)、[官方 solver 能力矩阵](<D:/RAG/Newton knowledge/sources/newton-v1.7.0/docs/solvers/index.rst>)
- [Coupled Solvers](<D:/RAG/Newton knowledge/sources/newton-v1.7.0/docs/concepts/coupling.rst>)、[SolverBase 生命周期](<D:/RAG/Newton knowledge/sources/newton-v1.7.0/newton/_src/solvers/solver.py>)
- [Solver Observables](<D:/RAG/Newton knowledge/sources/newton-v1.7.0/docs/concepts/solver_observables.rst>)、[Sensors](<D:/RAG/Newton knowledge/sources/newton-v1.7.0/docs/concepts/sensors.rst>)、[Worlds](<D:/RAG/Newton knowledge/sources/newton-v1.7.0/docs/concepts/worlds.rst>)
- [MCP 工具签名](<D:/RAG/Newton knowledge/mcp_service/server.py>)、[MCP 读取实现](<D:/RAG/Newton knowledge/mcp_service/knowledge.py>)
- [共享检索实现](<D:/RAG/Newton knowledge/scripts/knowledge_search.py>)、[基础记录构建](<D:/RAG/Newton knowledge/scripts/build_index.py>)
- [网站生成链](<D:/RAG/Newton knowledge/site/build_site.py>)、[网站导航实现](<D:/RAG/Newton knowledge/site/dist/app.js>)
