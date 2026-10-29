"""Render the readable handbook from curated records and source-verified prose."""
import json
from curated import ROOT, SHA, symbol

def write(path, text):
    if path=='README.md' and (ROOT/path).exists() and '仿真知识平台' in (ROOT/path).read_text(encoding='utf-8-sig').splitlines()[0]:
        return
    p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text.strip()+'\n',encoding='utf-8')
def read(path): return json.loads((ROOT/path).read_text(encoding='utf-8'))
def C(name):
    s=symbol(name);return f"[`{name}`]({s['source']['url']})"
def P(id):
    r=next(p for p in read('manifests/papers.json') if p['id']==id)
    return f"[{r['title']}]({r['url']})"

write('README.md',f'''# Newton 1.7.0 · VBD 知识库样板

这是以官方正式版本为事实基线的可追溯知识库，服务于 solver 学习、源码定位、参数解释和 real-to-sim agent 决策。每个 solver 后续可复用同一结构。

**版本固定：`v1.7.0`，commit `{SHA}`。** `sources/newton-v1.7.0` 保存官方仓库快照；在线 `latest`、项目封装默认值、旧版调参记录均不自动成为本版本事实。

## 从哪里开始

本地网站：[http://127.0.0.1:18448/](http://127.0.0.1:18448/)。双击根目录的 `启动知识库.cmd` 启动；部署和更新说明见 [网站说明](site/README.md)。

| 目的 | 入口 |
|---|---|
| 理解 VBD、AVBD、compliant ALM、DAT 的分工 | [原理](solvers/vbd/theory.md) |
| 看功能范围、构建与 step 的数据流 | [源码导读](solvers/vbd/implementation.md) |
| 阅读三篇核心论文与实现差异 | [论文笔记](solvers/vbd/papers.md) |
| 查询完整构造参数和默认解析 | [参数手册](solvers/vbd/parameters.md) |
| 查询材料/几何/控制层参数 | [模型输入](solvers/vbd/model-inputs.md) |
| 从公式追到代码和验证 | [对应关系](solvers/vbd/paper-code-map.md) |
| 识别版本陷阱和证据空缺 | [版本与边界](solvers/vbd/version-notes.md) |
| 根据现象生成诊断实验 | [诊断手册](solvers/vbd/diagnostics.md) |
| 看 17 组真实参数 A/B 回放、曲线与官方说明对照 | [VBD 参数实验表](experiments/vbd_parameter_lab/index.html) · [交互三维版](experiments/vbd_parameter_lab/index-3d.html) |
| 将知识库接入重建 agent | [Agent 接入](agent/WORKFLOW.md) |
| 验证交付内容 | [验证记录](evaluations/REPORT.md) |

## 已包含的内容

- 3 篇原始论文 PDF、逐页文本、关键页预览和 SHA-256；保留作者/出版方权利。
- 完整构造签名：48 个输入项，含必填 `model`，即 47 个可选项。区分声明默认值、条件解析、弃用/忽略状态。
- 20 组重点 Model 输入；88 个直接字段引用的静态索引（非完整数据流分析）。
- 472 个源码符号的 AST 索引，8 组论文/机制/代码映射，22 条可追溯结论，8 组待验证诊断方案。
- JSON 关系图、SQLite FTS5 检索、图邻居扩展和可重复的校验脚本。当前不依赖外部模型服务，不包含向量 embedding 或自动生成的社区摘要。
- 4 组实际运行的 CPU 探针。它们验证有限行为，不证明任意真实任务的精度、GPU 性能或复杂接触鲁棒性。

## 直接使用

以下命令在 PowerShell 中执行。目录已附独立 `.venv`，不更改 RoboSimStudio 环境。

```powershell
Set-Location 'D:\\RAG\\Newton knowledge'
.\\.venv\\Scripts\\python.exe -X utf8 scripts\\retrieve.py --query '自接触 margin gap 默认值'
.\\.venv\\Scripts\\python.exe -X utf8 scripts\\retrieve.py --query 'rigid_compliant_alm' --json
.\\.venv\\Scripts\\python.exe -X utf8 scripts\\validate.py
.\\.venv\\Scripts\\python.exe -X utf8 experiments\\run_cpu_probes.py
```

运行环境的可重建依赖见 [runtime-lock.txt](manifests/runtime-lock.txt)。检索和静态构建只用 Python 标准库；下载/解析 PDF 另需 `pypdf`。

从已有证据重建：

```powershell
.\\.venv\\Scripts\\python.exe -X utf8 scripts\\rebuild.py
```

它依次重建 AST 清单、结构化记录、手册、关系图和检索索引，不下载源码、不重新运行物理实验。人工内容的编辑入口为 `scripts/curated.py`、`scripts/model_and_cases.py`、`scripts/author_docs.py`；修改这些后再 rebuild，避免只改生成文件而被覆盖。

## 目录约定

```text
sources/        官方源码快照与原始论文，作为证据
manifests/      版本、哈希、依赖锁定、证据读取范围
solvers/vbd/    人类手册 + 参数、结论、能力、诊断、映射 JSON
graph/          有类型、有出处的关系图
indexes/        可重建的 AST / Model 引用 / SQLite 索引
agent/          检索与行动约定，不包含自动执行 agent
experience/     调参实验记录模板；没有虚构历史成功案例
experiments/    可运行 CPU 探针与结果
evaluations/   检索问题集、结构/检索检查结果
scripts/        构建、检索与验证工具
```

证据等级：`source_checked` 是静态源码核查，`paper_background` 是方法背景，`measured` 只在对应实验条件内成立，`proposed` 是待试验建议。诊断条目不是既有调参经验。来源冲突保留，不由语言模型自动“折中”。
''')

write('solvers/vbd/theory.md',rf'''# VBD 原理：从能量到每一步计算

适用版本：Newton 1.7.0。Newton 是引擎名称；VBD 局部更新使用 Newton 型线性化，并不是每步装配并求解整个场景的全局 Newton 系统。

## 1. 隐式 Euler 的变分形式

以无额外速度相关项的粒子系统说明。位置 x、速度 v、质量矩阵 M、时间步 h、外加加速度 a：

$$y=x^n+h v^n+h^2a,\qquad G(x)=\frac{{1}}{{2h^2}}(x-y)^T M(x-y)+E(x).$$

惯性项希望粒子靠近自由预测位置 y，材料与接触项 E 希望满足弹性/接触关系。求解这个平衡后，由位置差得到速度。对应 {P('paper:vbd2024')} PDF p.3 Eqs.(2)–(4)、p.4 Eq.(6)，及 {C('SolverVBD._initialize_particles')}、{C('SolverVBD._finalize_particles')}。

这不是“忽略时间积分、直接把物体投影回去”。质量和步长进入局部系统，改变 h 会同时改变时间离散误差、惯性权重与数值耗散。材料阻尼、隐式积分耗散和有限迭代误差应分开识别。

## 2. 将大系统拆成顶点块

固定其他顶点，仅更新 i 的三个坐标：

$$f_i=-\nabla_iG,\quad H_i=\frac{{m_i}}{{h^2}}I+\sum_j\nabla_i^2E_j,\quad H_i\Delta x_i=f_i.$$

每次只处理与 i 相邻的力元。按拓扑着色安排同色块并行，不同颜色依次消费更新状态；动态接触另有积累/近似处理，不能把所有接触一概称为无耦合并行。对应论文 p.4 Eqs.(7)–(9)、Sec.3.9，以及 {C('SolverVBD._solve_particle_iteration')}、{C('solve_elasticity')}。

标量核用 3×3 逆，行列式绝对值不大于 `1e-8` 时跳过该更新。CUDA 还存在 tiled 特化路径。一次局部 Newton 更新不保证已求出局部最优，论文讨论的可选 line search 也不等于 Newton 当前所有路径都执行 line search。不能把“论文在极端测试中稳定”改写成任意初值/任意 dt 的正确性保证。

## 3. 刚体块、legacy AVBD 与 compliant ALM

刚体使用平移和转动的 6 自由度局部块；力、力矩、惯性、约束雅可比进入局部系统，{C('solve_rigid_body')} 调用 {C('ldlt6_solve')}。

legacy AVBD 引入拉格朗日乘子，双边硬约束的示意能量为 `0.5*k*C²+lambda*C`，随后更新 lambda 与 penalty。实际实现还含误差稳定化 `C-alpha*C0`、单边投影、罚参数上限与 warm start。论文依据是 {P('paper:avbd2025')} PDF pp.3–6；对应 {C('_update_joint_structural_dual')}。软行和硬行的 dual 规则不同。

Newton 1.7.0 推荐的 compliant ALM 是需要单独理解的实现扩展：

$$s=\frac{{K}}{{K+\rho}},\quad k_{{eff}}=\frac{{K\rho}}{{K+\rho}},\quad F_{{row}}=k_{{eff}}C+s\lambda.$$
$$\lambda^+=s\,[\lambda+\rho(C-\alpha C_0)].$$

K 是有限材料刚度，rho 是数值求解参数。K 不能简单被“无限增大 iterations/rho”替代；在平衡条件下 lambda 表达材料反力。内部 rho 按行类型与惯性支撑计算，例如双边行策略包含 `max(H,9K)`，并非用户 beta 的同义词。数值实现使用避免乘法溢出的等价形式。来源：{C('_compliant_alm_coefficients')}、{C('_alm_relaxed_ascent')}、{C('_material_force_terms')}、{C('_bilateral_auto_rho')}。

接触法向乘子投影为非负；切向 trial 乘子投影到由 `mu*lambda_n` 决定的 Coulomb 圆盘。切向不套用法向材料 s 缩放。见 {C('_compliant_contact_dual_step')}。以上公式并非直接摘自 AVBD 2025 的同编号公式。

**1.7.0 必须显式选择模式：**省略 `rigid_compliant_alm` 仍为 legacy；`True` 才进入 compliant。alpha 默认分别为 0.95 与 0，gamma 默认 0.999。beta=0 是当前默认，不是论文所有示例的配置。

## 4. 材料与摩擦的实现差异

膜能量、二面角弯曲、tet 体积能量各自贡献局部 force/Hessian。VBD 是求解组织方式，不是唯一的材料模型。改变网格、静止面积/体积、厚度约定或材料律，都会改变同一数值参数对应的物理含义。

VBD 2024 Sec.3.3 的简化 Rayleigh 阻尼不能直接当作 1.7.0 膜/tet 阻尼实现：当前膜核以 `C=FᵀF` 的变化率构造客观阻尼，使纯刚体旋转不引入此应变阻尼；tet 核也采用该类结构。弯曲阻尼则依据二面角变化率。见 {C('evaluate_neo_hookean_membrane_force_hessian')}、{C('evaluate_volumetric_neo_hookean_force_and_hessian')}、{C('evaluate_dihedral_angle_based_bending_force_hessian')}。

粒子摩擦使用滑移距离的平滑函数，`eps_u=friction_epsilon*h`。mu 决定摩擦强度，epsilon 决定小滑移的平滑区域；二者不可互换。见 {C('compute_friction')}。

## 5. DAT 是几何位移限制层

优化器先提出位移，DAT 用接触候选定义安全区域，再截断位移，使几何更新留在区域内。Planar-DAT 根据双侧趋近位移分配分隔平面，避免对远离/切向运动做同等的各向同性限制；它不替代材料反力或摩擦模型。见 {P('paper:dat2026')} PDF p.4 Eqs.(11)–(16)，以及 {C('apply_planar_truncation_parallel_by_collision')}。

软自接触使用 vertex–triangle 与 edge–edge 候选，刚柔还需考虑刚体转动轨迹，相关实现为 {C('rigid_trajectory_truncation_t')}。本版本刚柔 DAT 需 owned pipeline、禁止 external rigid，并要求有效查询半径；见 {C('SolverVBD._init_rigid_penetration_free')}。

论文的几何性质有前提：初始合法构形、充分候选覆盖、有效距离/轨迹界和正确截断。有限 buffer、错误过滤、初始穿插都不能由一个布尔开关消除。本样板没有证明任意 tet 翻转都受保护，也没有运行密集接触验证。

```mermaid
flowchart LR
 A[状态、控制、模型] --> B[预测与检测]
 B --> C[局部力和 Hessian]
 C --> D[按颜色求解刚体或粒子块]
 D --> E[适用时 DAT 截断]
 E --> F[约束与历史更新]
 F --> C
 F --> G[速度与接触力输出]
```

图为机制关系示意，精确的刚体/粒子调用顺序以 [源码导读](implementation.md) 和 `step` 为准。
''')

write('solvers/vbd/implementation.md',f'''# 源码导读与生命周期

官方版本：`{SHA}`。源码路径均在 `sources/newton-v1.7.0`。公开入口为 `newton.solvers.SolverVBD`；`_src` 只用于证据定位，业务代码使用公开入口。

## 模块地图

| 文件 | 职责 | 重点入口 |
|---|---|---|
| `solver_vbd.py` | 配置解析、内存、三阶段 step、历史、调度、导出 | {C('SolverVBD.__init__')}；{C('SolverVBD.step')} |
| `particle_vbd_kernels.py` | 膜/tet/弯曲/弹簧力与 Hessian、摩擦、局部解、DAT | {C('solve_elasticity')}；{C('compute_friction')} |
| `rigid_vbd_kernels.py` | 刚体局部系统、关节、ALM、接触材料/dual、刚体 DAT | {C('solve_rigid_body')}；{C('update_duals_joint')} |
| `vbd_coupling_kernels.py` | proxy 耦合相关接触力采集 | 见 [符号索引](../../indexes/source_symbols.json)，不等同 constructor 的单向耦合 |
| `geometry/tri_mesh_collision.py` | 网格自接触候选与拓扑过滤 | 见静态索引与调用方 |
| `sim/model.py`、`sim/builder.py` | 数据定义与模型装配 | [模型输入](model-inputs.md) |

## 构建顺序

1. 确定单位、坐标、材料、几何与控制；添加到 `ModelBuilder`。
2. `builder.color()`，覆盖粒子及 VBD 所积分的刚体；随后 `finalize`。
3. 建立 `CollisionPipeline`，明确是否由 solver 持有，配置全局容量与 matching。
4. 外部检测模式：pipeline → contacts → solver；owned 模式：把 pipeline 交给 solver 分配 contacts。
5. 分配 state/control；先完成一次普通运行或所需预分配，再考虑 CUDA graph capture。

不是所有数组都能在 graph capture 中临时增长。全局 contact storage 与每个刚体/顶点的邻接表容量也不是同一参数。相关保证与异常见 {C('SolverVBD')}。

## step 的真实顺序

依据 {C('SolverVBD.step')}：

```text
解析 contacts 所有权与 observables
解析本步 rigid / soft-self-contact 检测调度并验证 DAT 条件
需要时执行初始化前检测
初始化刚体 → 初始化粒子
需要时执行初始化后检测
重复 iterations 次：
    需要时更新检测结果
    刚体迭代：颜色组 primal、相关 dual/penalty 等
    粒子迭代：颜色组接触/弹簧/材料力与 Hessian、位移及截断
可选：在最终迭代构形导出接触力
保存刚体接触历史 → 最终更新刚体 → 最终更新粒子速度
```

源码会使用 `state_in` 内的数组承载部分中间迭代，不应把其命名理解成函数式只读输入。需要保存上一帧观测时另行复制。外部刚体模式对 `state_in/out` 的旧/新刚体位姿语义有专门约定，见 {C('SolverVBD._solve_particle_iteration')}。

### 碰撞所有权不能混用

- 外部：调用者 `pipeline.collide(state, contacts)`，再传 contacts 给 `solver.step`。
- owned：构造 `SolverVBD(..., collision_pipeline=pipeline)`，`step(..., contacts=None, dt=...)`，用 solver 的 contacts 读取结果。
- owned 模式 AUTO 的普通 rigid slot 为 PRE_INIT；soft self-contact 或 rigid-soft DAT 启用后相关 slot 为 PRE_POST_INIT。
- `rigid_soft_enable_dat=True` 要求 owned pipeline，而且不支持 external-rigid solver。参见 {C('SolverVBD._default_collision_frequency_type')}、{C('SolverVBD._init_rigid_penetration_free')}。
- 同时启用 `rigid_soft_enable_dat` 与 `particle_enable_self_contact` 时，两种 DAT 共用 motion reference：RIGID 与 SOFT_SELF_CONTACT 必须解析为同一种调度类型；若为 ITERATIONS，还必须使用相同 frequency。各自非 NONE 并不足够。显式修改检测频率时同步配置两个 slot；不匹配会在 step 中被拒绝。参见 {C('SolverVBD._validate_dat_collision_schedules')}。

## 能力边界

支持 cloth 三角形/弯曲、tet、粒子弹簧、刚体、关节及相关混合。关节：BALL、FIXED、FREE、REVOLUTE、PRISMATIC、D6、ROD。DISTANCE 和若干模型字段不支持：armature、joint_friction、effort/velocity limits、target_mode、equality constraints；joint-owned mimic 与已弃用 sparse mimic 必须区分。完整机器记录在 [capabilities.json](capabilities.json)，证据为 {C('SolverVBD')}。

CONTACT_F 导出最终构形下的刚体接触和刚柔接触记录，不导出软自接触力。测量传感器的坐标系、作用点、符号和采样频率还需适配；不能直接将 contact wrench 与真实腕部六轴数据逐项相减。

## 修改与 reset

- 非 ROD 的结构材料、布局、静止角为构造缓存；重建 solver。
- ROD 的 `joint_target_ke/kd` 材料更新使用 `notify_model_changed(ModelFlags.JOINT_DOF_PROPERTIES)` 或较窄的 `ModelFlags.JOINT_DOF_FORCE_PROPERTIES`；这不会刷新静止弯扭角缓存。
- ROD 静止弯扭角由 `joint_X_p`、`joint_X_c` 和 `model.body_q` 派生。修改 joint rest frames 后通知 `ModelFlags.JOINT_PROPERTIES`，修改 body 的模型静止姿态后通知 `ModelFlags.BODY_PROPERTIES`；对应分支才调用 rest cache 刷新。仅改运行时 State 位姿不等于改变模型静止构形。参见 {C('SolverVBD.notify_model_changed')}、{C('SolverVBD._refresh_rod_rest_bend_twist_cache')}。
- `joint_enabled` 有 live 读取，但派生接触 conditioning 还需 `JOINT_PROPERTIES` 通知。
- CUDA tiled 材料类别特化在构造发生；改三角形/边刚度后重建。
- episode reset 需同时考虑 solver 历史、pipeline matching 历史、FK 和新接触。`JOINT_Q/QD` 不直接替代最大坐标 `body_q/qd`。

证据：{C('SolverVBD')}、{C('SolverVBD.reset')}、{C('SolverVBD._init_particle_system')}。不要把“某个数组可写”当作“所有缓存立即有效”。

## 本地可运行入口

[CPU 探针](../../experiments/run_cpu_probes.py) 使用公开 API 构造两个粒子和一根弹簧，运行真正的 SolverVBD 并与解析隐式步比较；另有配置语义检查。真实布料/软体案例优先参照固定快照的 `examples/vbd`、`examples/cloth`、`examples/softbody` 与 `examples/multiphysics/example_vbd_dat_rigid_soft.py`。这些上游例子已保留，但本样板没有声称全部运行通过。

密集接触与 DAT 后续回归入口列在 [upstream-tests.json](upstream-tests.json)，每条具有固定 commit 的函数定位和 `not_run_in_this_delivery` 标记，区分“上游存在测试”和“本机已运行”。
''')

write('solvers/vbd/papers.md',f'''# 论文阅读卡与实现边界

论文全文、逐页提取文本位于 `sources/papers`，哈希与原始 URL 见 [papers.json](../../manifests/papers.json)。页码为 PDF 页码，从 1 开始；文本提取可能丢失公式布局。已经视觉核对 VBD p.3、AVBD p.6、DAT p.4。

## VBD 2024：为什么能逐顶点解隐式系统

Anka He Chen、Ziheng Liu、Yin Yang、Cem Yuksel；TOG 43(4), Article 116；DOI `10.1145/3658179`。{P('paper:vbd2024')}；[本地 PDF](../../sources/papers/vbd2024.pdf)。

**问题与核心思路：**全局隐式系统的大规模求解开销高；把未知量分成顶点坐标块，以相邻力元构建 3×3 局部系统。颜色调度保留块 Gauss–Seidel 的信息传播并提供并行性。

**阅读路径：**p.3 Eqs.(2)–(5) 定义全局和局部目标；p.4 Eqs.(7)–(9) 定义局部 Newton 系统；Sec.3.3–3.9 讨论阻尼、接触、摩擦、初始化与并行。实验考察弹性形变、困难初始构形和计算预算。本文报告的稳定现象不能替代目标场景的误差测量。

**与 Newton 对应：**{C('solve_elasticity')} 和 {C('SolverVBD._solve_particle_iteration')} 是主入口。膜/tet 当前客观阻尼不直接等于论文 Sec.3.3 的简化 Rayleigh；tile 特化、DAT 和 rigid compliant ALM 是额外实现。复现先用单弹簧解析步，再用固定网格静态载荷与动态衰减分别识别材料/阻尼。

**图示建议：**证据页用 p.3 的全局/局部目标；解释图用“一个顶点与相邻三角形/tet”的局部系统，勿把整页论文当架构图。

## AVBD 2025：硬约束与刚度差异

Chris Giles、Elie Diaz、Cem Yuksel；TOG 44(4), Article 90；DOI `10.1145/3731195`。{P('paper:avbd2025')}；[本地 PDF](../../sources/papers/avbd2025.pdf)。

**问题与核心思路：**单纯提高 penalty 处理硬约束会使收敛困难；引入 dual，交替做局部 primal 更新与约束乘子/罚参数更新。接触需要处理不等式与摩擦边界。

**阅读路径：**p.3 Eq.(8) 约束能量、Eq.(11) dual、Eq.(12) stiffness；p.6 Eq.(19) warm start 与 Algorithm 1 总流程。实验覆盖刚体接触、堆叠与关节等困难约束场景。

**与 Newton 对应：**{C('solve_rigid_body')}、{C('update_duals_joint')}、{C('_ramp_penalty_k')} 对应 legacy 机制。论文示例 alpha=0.95、gamma=0.99，不等于 Newton 全部默认（源码 gamma=0.999、beta=0，compliant 默认 alpha=0）。有限材料 K 与 rho 分离的 compliant ALM 依据当前源码单独建卡，不能偷换成原论文公式。

**图示建议：**证据页 p.6 Algorithm 1；解释图画 primal→dual 的反馈，并把物理 K 和数值 rho 分开。

## DAT 2026：把几何合法性从优化步骤分离

Anka He Chen、Jerry Hsu、Youssef Ayman、Miles Macklin；arXiv `2604.15513v1`，已下载版本为 2026-04-16 的 v1；正式发表 DOI `10.1145/3799902.3811143`。归档的 arXiv 标题使用 Systems，Newton 引用的发表标题使用 System，未声称两版正文逐字相同。{P('paper:dat2026')}；[本地 PDF](../../sources/papers/dat2026.pdf)。

**问题与核心思路：**不同物理系统在耦合中可能穿插；为接触双方构造互斥区域，限制每次更新。Planar-DAT 按趋近运动分配分隔平面，减少对切向运动的过度限制。

**阅读路径：**Sec.3、p.4 Eqs.(11)–(12) 平面分配、Eqs.(13)–(15) 顶点条件、Eq.(16) 截断；Fig.3 展示相向、远离和切向运动。实验包含多类物理对象耦合，具体保证依赖候选覆盖与合法初态等前提。

**与 Newton 对应：**{C('apply_planar_truncation_parallel_by_collision')}、{C('rigid_trajectory_truncation_t')}。启用 `rigid_soft_enable_dat` 有 pipeline/半径/外部 solver 限制。本文更广的方法（如 Divide and Project）不因被论文讨论就自动视为此 release 已完整实现。

**图示建议：**证据图为 p.4 Fig.3；解释图叠加候选范围、原始位移和截断后位移，分别展示漏候选与截断。

## 相关文献的收录原则

固定版本 `docs/solvers/vbd.rst` 还引用 OGC（Offset Geometric Contact, DOI `10.1145/3731205`），同时明确 OGC coverage 待 Newton 可用后补充。本样板把它保留为背景线索，不建“1.7.0 已完整支持 OGC”的图关系。后续材料模型论文也应先由具体 kernel 引用或实现差异触发收录，不凭术语相似就建立等价关系。
''')

params=read('solvers/vbd/parameters.json')['records']
lines=['# SolverVBD 构造参数全集','',
 '基线为 1.7.0 固定签名：48 个输入含必填 model，47 个可选项。原始类型、英文参数说明、所有文本引用位置在 [parameters.json](parameters.json)；“文本出现”并不等于实际运行时依赖。',
 '', '## 阅读规则','',
 '- 声明 `None` 不代表无效或值为零；下表单列实际解析。',
 '- 官方默认值是接口事实，推荐范围/经验证成功区间是另一种证据；本库没有伪造统一调参区间。',
 '- 默认把 constructor 参数看作构造期配置；调度有公开 setter，Model 变更需遵守 notify/cache 规则。',
 '- 数值预算、物理材料、几何检测和历史参数分开记录；dt 与 substeps 不是此 constructor 的两个缺失参数。',
 '', '## 完整清单','']
for p in params:
    default=p['declared_default_expression'] if not p['required'] else '必填'
    lines += [f"### `{p['name']}`",'',f"类别：{p['category']}；声明默认：`{default}`；单位：{p['units']}。",'',p['summary_zh'],'',f"解析：`{p['resolved_default']}`。状态：`{p['status']}`。",'',f"证据：[签名 L{p['definition']['line']}]({p['definition']['url']})；[完整记录](parameters.json)。",'']
lines += ['## 新式自接触配置示意','',
 '```python','particle_enable_self_contact=True,','particle_self_contact_margin=0.005,','particle_self_contact_gap=0.005,','```','',
 '这里的 5 mm + 5 mm 仅是兼容语义探针配置，已验证 query radius=10 mm；不是布料抓取的通用推荐值。若仅填 margin=0.005 而不填 gap，启用自接触且有粒子时会因保留旧语义而报错。',
 '', '## 代码强制约束与建议的区别','',
 '| 类别 | 本版本已核查规则 |','|---|---|',
 '| 强制约束 | DAT relaxation 严格在 (0,1)；全局 beta>=0；旧 radius 不可和新 gap 并用 |',
 '| 强制依赖 | rigid-soft DAT 需 owned pipeline、不可 external rigid、存在查询时需正查询半径 |',
 '| 模式依赖 | legacy hard/soft 控制在 compliant rigid 路径不产生同样模式作用；body-particle 仍需单独分析 |',
 '| 已忽略 | 三个 stick/deadzone 参数被忽略，即使优化器给它们采样也不会达到预期效果 |',
 '| 待实测建议 | iterations、dt、网格精度、buffer、摩擦和刚度的搜索区间由任务标定决定 |',
 '', '不要把本表当作完整参数有效性验证器；精确异常还受场景结构、运行模式和设备影响。']
write('solvers/vbd/parameters.md','\n'.join(lines))

models=read('solvers/vbd/model-inputs.json')
lines=['# 模型输入：constructor 之外的物理知识','',
 '本表是重点字段解释，不声称覆盖 Model 全部输入。完整直接引用字段清单见 [model_field_uses.json](../../indexes/model_field_uses.json)，其范围是 VBD 模块里的 model.field 语法，不解析别名或跨函数数据流。','',
 '| 字段 | 单位/约定 | 作用与证据 |','|---|---|---|']
for m in models:
    lines.append(f"| `{m['field']}` | {m['units']} | {m['description_zh']} [Model 定义]({m['model_definition']['url']}) · [消费者]({m['consumer']['url']}) |")
lines += ['', '## 连续材料到离散输入','',
 '三维各向同性材料常用 E、nu 转换为 Lamé 系数：mu=E/[2(1+nu)]、lambda=E*nu/[(1+nu)(1-2nu)]。这只适用于相应三维本构约定，不能把这对数值直接复制为薄膜或 rod 的离散系数。厚度、截面积、静止网格、归一化和平面应力/应变约定必须明确。','',
 '特别保留两个单位核查点：Model 对 tri_materials 标 Pa/Pa·s，但膜 kernel 按静止面积缩放；edge stiffness 文档标 N·m/rad，弯曲 kernel 还乘静止边长。这里保存官方标签，不自行宣告等价的物理标定单位。用确定几何的拉伸/弯曲静态实验核对有效系数，再把适配公式入库。','',
 '## 数据层级','',
 '- `Model`：几何、质量、材料与静止数据。',
 '- `State`：位置、速度等时变数据。',
 '- `Control`：关节/执行器命令；VBD 支持的字段须从能力清单筛选。',
 '- `CollisionPipeline / Contacts`：候选、接触几何、容量、matching；不全部由 SolverVBD 参数决定。',
 '- 调用层：dt、子步数、控制更新率、碰撞频率、目标评价。',
 '', '旧工程中与这些层级混合保存的调参记录，需要先拆分，再判定哪些能迁移到 1.7.0。']
write('solvers/vbd/model-inputs.md','\n'.join(lines))

maps=read('solvers/vbd/paper-code-map.json')
lines=['# 论文—机制—源码—参数—实验映射','',
 '图边表示有范围的对应关系；`source_extension` 不表示论文原样实现。实验只支持其记录的窄条件。','']
for m in maps:
    lines += [f"## {m['title_zh']}（{m['id']}）",'',
        f"论文定位：{m['paper_id'] or '当前源码扩展'}；{m['paper_locator']}。",'',
        '源码：'+'；'.join(C(s['name']) for s in m['symbols'])+'。','',
        '参数：'+(', '.join('`'+p.rsplit(':',1)[1]+'`' for p in m['parameter_ids']) or '主要由 Model 材料字段配置')+'。','',
        f"对应性质：{m['correspondence']}。",'']
    local = m.get('local_experiments', [])
    if m['experiment_id']:
        lines += [f"既有窄探针：[{m['experiment_id']}](#/record/{m['experiment_id'].replace(':', '%3A')})；只支持该探针记录的输入与结论。",'']
    if local:
        lines += ['局部实测证据（不代表整张映射已验证）：','']
        for evidence in local:
            rid=evidence['record_id']
            lines += [f"- [{rid}](#/record/{rid.replace(':', '%3A')})：{evidence['scope']} 边界：{evidence['limitation']}"]
        lines += ['', '仍未覆盖：'+'；'.join(m.get('unvalidated_scope', [])), '']
    elif not m['experiment_id']:
        lines += ['尚无已关联的本地运行证据，保留为静态映射；这不表示整个知识库没有相关实验。','']
lines += [
    '## 证据层级与剩余实验', '',
    '`exp:*` 是早期构造语义/CPU 窄探针，`lab:*` 是保存 A/B 轨迹的参数实验。两者保留各自的场景与边界；关联局部实验不将整个映射标为 experiment_validated。', '',
    '当前参数实验为17组CPU A/B，直接干预9/47个可选构造项，没有全参数扫描或独立重复统计。tet、rod、历史状态、耦合与GPU等下一批实验见[版本差异与缺口](version-notes.md)。',
]
write('solvers/vbd/paper-code-map.md','\n'.join(lines))

write('solvers/vbd/version-notes.md',f'''# 版本差异、冲突和缺口

## 固定版本的意义

以正式 tag `v1.7.0` 的完整 commit `{SHA}` 为基线。正式发布并不改变 SolverVBD 在源码中标记为 experimental 的事实。线上 `latest` 和 GitHub `main` 都不是本知识库默认事实源。

| 容易误读的内容 | 1.7.0 的结论 |
|---|---|
| 省略 rigid_compliant_alm | 实际 False legacy；推荐显式 True 是另一件事 |
| alpha 的 None | 依据模式解析：legacy .95、compliant 0 |
| AVBD 论文 gamma | 论文示例 .99；源码默认 .999 |
| beta | 默认 0；不能照搬论文递增流程认定默认每步都 ramp |
| self-contact margin | 单独给 margin 仍为旧 query radius；新式必须显式给 gap |
| 原 particle conservative relaxation | 弃用别名仍覆盖新的共享 DAT 参数 |
| rigid_contact_stick_* | 弃用且忽略，不应纳入搜索空间 |
| 普通 rigid 与 rigid-soft DAT | AUTO 检测节奏不同，DAT 必须 owned pipeline |
| VBD 2024 阻尼公式 | 当前膜/tet 客观阻尼不是论文简化 Rayleigh 的逐式复刻 |
| OGC | pinned guide 说待可用后补充，不能宣称已完整支持 |
| docs 的调参章节 | 很多是 in-development outline，不是经验证参数表 |

见 [结论记录](claims.json)、{C('SolverVBD.__init__')}、{C('SolverVBD._default_collision_frequency_type')} 与仓库固定版本 `docs/concepts/simulation_tuning_vbd.rst`。

## 已保留的不确定性

1. 薄膜/弯曲参数的官方单位标签与离散能量缩放，需要材料标定适配；见 [模型输入](model-inputs.md)。
2. 复杂自接触、刚柔 DAT、转动轨迹、密集堆叠与 GPU tile 没有在本样板全面复现。
3. 本次 `.venv` 安装 Warp 1.18.0 的 CUDA 13 构建，本机驱动报告 12.8；CPU 探针正常通过。没有修改驱动，也没有把 GPU 不可用写成算法缺陷。
4. 源码里的测试是“有测试覆盖的证据入口”，不等于这些上游测试本次全部通过。
5. 旧版调参经验尚未导入；经验表仅有模板。历史 1.4 等版本记录应保留原版本和场景，重跑后才推广为 1.7.0 经验。

## 下一批物理实验（proposed / not_run）

以下是尚未执行的验证计划，不因本轮修正文档或缓存通知探针而变成已验证：

| 主要缺口 | 建议的最小场景与量测 | 不能借用的现有证据 |
|---|---|---|
| tet 与客观阻尼 | 固定体网格载荷与自由衰减，比较体积/形变/能量；叠加刚体旋转检查响应一致性 | 单三角膜和折页不验证体积材料或阻尼客观性 |
| rod 与刚体接触 | 简单弯扭 rod、修改静止构形后的恢复力；单刚体摩擦/接触，记录位姿和约束误差 | 缓存刷新探针只检查缓存值；固定关节和粒子摩擦不替代rod/刚体动力学 |
| history / matching / reset | 相同初态的全新solver与运行后reset对照，加入局部world复位，检查状态和接触历史 | 单次A/B不验证复位后的历史一致性 |
| 容量与耦合 | 稠密候选压力和刚柔接口场景，分别记录VT/EE容量溢出、各方轨迹/力及接口所有权 | 简单质点撞板不证明密集覆盖或双向耦合 |
| GPU / tile / graph | 在可用设备上固定场景/预算比较scalar与tile、eager与capture的轨迹误差和开销 | 当前CPU实验不构成GPU、跨设备逐位确定性或性能排名证据 |

每组先冻结干预、误差指标、初态和验收阈值，再保存原始数据并独立复算；不以“每个参数都有一行”替代主要机制覆盖。

## 更新到下一个版本

保留本目录版本基线；新版本建立独立 source manifest。先比较构造签名和默认解析，再比较相关函数、材料约定、缓存生命周期、碰撞调度。重跑本样板探针与检索问题集，补充目标场景回归；只有通过证据审查的关系才获得新 version scope，不能全库替换版本字符串。
''')

plans=read('solvers/vbd/diagnostics.json')
lines=['# 面向任务的诊断方案','',
 '下面是源码驱动的待验证计划，不是已经积累的成功经验。执行时把 scene、reference、commit、dt、控制轨迹和完整参数写入 [实验模板](../../experience/experiment-template.json)。','']
for d in plans:
    lines += [f"## {d['symptom']}",'',f"编号：`{d['id']}`；关联结论："+', '.join(d['claim_ids'])+'。','']
    lines += [f'{i+1}. {p}' for i,p in enumerate(d['plan'])]
    lines += ['', '记录指标：'+', '.join(d['metrics'])+'。','',d['caution']+'。','']
lines += ['## 经验晋级条件','',
 '一次看起来成功的视频只能算候选经验。至少保存基线、单项干预、固定评价指标、失败条件和完整产物；跨对象或跨网格复测后再扩大适用范围。所有结论都应能回溯到 run_id，而不是只留下“某值比较好”。']
write('solvers/vbd/diagnostics.md','\n'.join(lines))
