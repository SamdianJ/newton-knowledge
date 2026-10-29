"""Curate the Newton 1.7.0 common knowledge layer from the locked release.

Narratives are source explanations, not run results. This writes authored input;
build_platform renders pages and indexes it without editing Newton or lab data.
"""

from __future__ import annotations

import json
from urllib.parse import quote

from plan_p0 import ROOT, SRC, COMMIT
from source_api import inventory
from common_content import COMMON_DETAILS

MODULES = {
    "newton": (
        "ModelBuilder / Model / State / Control / Contacts 的生命周期",
        "Builder 接收原语、URDF/MJCF/USD 与自定义属性；finalize 分配 Model。随后分配输入/输出 State、Control、Contacts 和可选 Observables，由所选 solver.step 推进。Model 主要保存拓扑、材料和参数，State 保存动态量；变更 Model 数组要核对 notify_model_changed 和缓存语义。",
        "状态交换后继续使用新输入；清理每步外力。contact_f 不在 State 中，应通过 solver.observables 请求。",
        "docs/guide/overview.rst",
        [
            "newton.ModelBuilder",
            "newton.Model",
            "newton.State",
            "newton.Control",
            "newton.Contacts",
            "newton.CollisionPipeline",
        ],
    ),
    "actuators": (
        "执行器 Delay → Drive → Clamping → scatter-add",
        "执行器读取状态与目标，计算 DOF effort，并累加到控制输出。ModelBuilder.add_actuator 注册后在 finalize 时实例化；也可独立组合 DrivePD/DrivePID、Delay 和电机限幅。",
        "调用方每步先清零 effort 输出；执行器的可微、graph capture 能力依赖具体 drive。首版一执行器一 DOF，无通用传动模型或完整电机动力学。",
        "docs/concepts/actuators.rst",
        ["newton.actuators.Actuator", "newton.actuators.DrivePD"],
    ),
    "controllers": (
        "机器人控制器：DifferentialIK、JointImpedance、OperationalSpace",
        "控制器从关节状态、末端目标与模型/外部运动学产生控制信号。ControllerDifferentialIK 每步 eval_fk / eval_jacobian，按 articulation/joint/site 选择机器人、列与工具点，再执行可选 Jacobian 解法。",
        "该 model-based DifferentialIK 当前只控制一坐标一 DOF 的关节；每个受控机器人恰好匹配一个 tool site，且 model.requires_grad=True 不受支持。controller 输出需按端口和模型索引写回 Control，不可假定它已经推进物理。",
        "newton/controllers.py",
        [
            "newton.controllers.ControllerDifferentialIK",
            "newton.controllers.ControllerDifferentialIK.step",
        ],
    ),
    "geometry": (
        "几何表示、碰撞检测数据与预处理",
        "newton.Mesh 等根模块几何类型用于建模；geometry 模块提供 BroadPhase、NarrowPhase、SDF 与形状碰撞工具。视觉网格不自动等同于碰撞表示；构建阶段检查尺度、拓扑、法线、形状类型、SDF 和接触支持，再交给 CollisionPipeline。",
        "模型级凸分解使用 ModelBuilder.approximate_meshes(method=\"coacd\"/\"vhacd\")；utils.remesh_mesh 是网格重建工具，不提供这两个分解方法。碰撞过滤决定候选配对，增加 solver iterations 无法修复漏检。",
        "docs/concepts/collisions.rst",
        ["newton.Mesh", "newton.geometry.NarrowPhase"],
    ),
    "ik": (
        "逆运动学目标与迭代求解",
        "IKSolver 将位置、旋转、关节限制等 IKObjective 组合到运动学优化问题，求解满足任务目标的关节配置。它与 newton.eval_ik 的表示转换、以及 controllers 的微分控制职责不同。",
        "运动学目标不保证动力学可行或接触安全；之后要映射 Control 布局、选择驱动并经 solver 检验。",
        "newton/ik.py",
        [
            "newton.ik.IKSolver",
            "newton.ik.IKObjectivePosition",
            "newton.ik.IKObjectiveRotation",
        ],
    ),
    "math": (
        "空间数学与坐标变换索引",
        "空间向量、惯量与变换运算服务于控制、关节和动力学。先确定向量的参考点和参考系，再选择公开 math 导出；签名与实现可从下方源码入口读取。",
        "本模块首版为 I 级索引，不给全部数学函数另写推导。不要把线性/角度分量顺序或 body-origin twist 与质心 twist 混用。",
        "docs/concepts/conventions.rst",
        [],
    ),
    "selection": (
        "ArticulationView 批量读取与掩码写入",
        "ArticulationView 根据标签或索引选择 articulation，建立 view 与 Model 的索引映射，在 Model、State、Control、Observables 上读写受支持 frequency 的属性。set_attribute 支持 world 或 world×articulation 掩码。",
        "选择 API 当前假设模型同质。选择掩码形状与 solver.reset 的 world_count+1 掩码不同；raw contact 行没有稳定唯一的 articulation 归属，不能直接通过 view 过滤。",
        "newton/_src/utils/selection.py",
        [
            "newton.selection.ArticulationView",
            "newton.selection.ArticulationView.set_attribute",
        ],
    ),
    "sensors": (
        "SensorContact / IMU / Camera 与量测依赖",
        "传感器从 State、Sites、Contacts 和 solver Observables 产生量测。SensorContact 声明 CONTACT_F 需求；可与其他传感器所需 kinds 合并，一次分配并跨步复用。",
        "先确认后端 supported_observables，再配置接触容量和同一 Contacts。接触几何通常按输入 state 消费；native MuJoCo CPU 不提供 CONTACT_F，MuJoCo Warp 路径才支持该观测。",
        "docs/concepts/sensors.rst",
        [
            "newton.sensors.SensorContact",
            "newton.sensors.SensorContact.update",
            "newton.sensors.SensorIMU",
        ],
    ),
    "solvers": (
        "SolverBase 接口、8 个后端与能力边界",
        "统一接口为 step(state_in,state_out,control,contacts,dt,observables=...)。坐标表示、材料响应、关节类型、碰撞来源、可微性和观测支持按 backend 与配置分别判断。",
        "继承 ObservableKind 名称不代表支持；以 solver.supported_observables 为准。solver.reset 默认实现不恢复所有物理初态；查看后端覆盖。coupled 是 experimental 子系统，不计作第九个普通后端。",
        "docs/solvers/index.rst",
        [
            "newton.solvers.SolverBase",
            "newton.solvers.SolverBase.step",
            "newton.solvers.SolverBase.reset",
        ],
    ),
    "usd": (
        "USD 资产、Schema 与物理属性解析",
        "通过 ModelBuilder.add_usd 和 newton.usd 公开 Schema 工具把 USD 层级及物理属性转入 builder。解析结果受 schema、单位、坐标轴、刚体/关节/可变形体表达与 importer 支持范围影响。",
        "import 成功只证明解析；还要检查导入后的质量、碰撞表示、驱动、自定义属性和 solver 支持。不要把 viewer 导出的 USD 视为逐项保真 roundtrip。",
        "docs/concepts/usd_parsing.rst",
        ["newton.ModelBuilder.add_usd"],
    ),
    "utils": (
        "资产与网格处理、开发辅助索引",
        "utils 收录资产获取、remesh_mesh 网格重建、着色、惯量和其他辅助函数。首版以公开 __all__ 索引与函数源码为主；模型级凸分解的公开入口是 ModelBuilder.approximate_meshes，应在 finalize 前调用。",
        "可达的 newton._src 路径属于实现，不是稳定公开导入。可选依赖与工具输出需要固定版本；本地知识服务不执行下载或分解。",
        "newton/utils.py",
        [],
    ),
    "viewer": (
        "ViewerGL / ViewerUSD / ViewerNull 与结果导出",
        "Viewer 接收 model、时间步和 state，支持交互显示、USD 记录或无窗口执行。渲染、接触显示和离线导出共用物理输出，但不改变 solver 的数值结果。",
        "观测接触力需传入已分配的 observables；帧率与仿真子步区分，结果应同时保存数值指标、配置和原始状态，不仅保存视频。",
        "docs/guide/visualization.rst",
        [
            "newton.viewer.ViewerGL",
            "newton.viewer.ViewerUSD",
            "newton.viewer.ViewerNull",
        ],
    ),
}

CONCEPTS = {
    "worlds": (
        "一个 Model 中的 world 分组与选择",
        "用 begin_world/end_world、add_world 或 replicate 建立独立 world，实体数组记录各自 world index；-1 为 global。*_world_start 有 world_count+2 项，global 实体可能分布在前后两段，不能只取一个连续 slice。",
        "Builder 可以构建异质 world，不代表全部 solver 或 ArticulationView 都支持异质批量。",
    ),
    "articulations": (
        "广义坐标和最大坐标的双重表示",
        "joint_q/joint_qd 表示广义坐标；body_q/body_qd 表示刚体位姿和质心 twist。eval_fk 从关节坐标更新刚体表示，eval_ik 做反向表示转换；MuJoCo/Featherstone 主要使用广义坐标。",
        "碰撞前保证最大坐标更新；FREE/BALL 的坐标数与 DOF 数不同，不能统一按 qd offset 索引目标。",
    ),
    "deformables": (
        "curve / surface / volume 的离散化与材料归属",
        "Rod-backed curve 记录 bodies/joints；三角 surface 记录 particles/triangles/bending edges；四面体 volume 记录 particles/tets。add_cloth_mesh/grid 与 add_soft_mesh/grid 等分别写入对象范围。",
        "网格分辨率、材料数组、质量和着色都影响响应。每个 solver 消费的材料字段不同，参数记录与网格建模应分别检查。",
    ),
    "mass-inertia": (
        "质量、质心与惯量决定动力学尺度",
        "构建时由形状密度或显式质量/惯量建立 body 质量属性；区分 body frame、中心惯量和 world frame，检查单位、正定性及 kinematic/static 身份。",
        "错误密度、薄片惯量或质量比会表现为接触抖动；不能仅靠接触刚度弥补。最终以 Model 的实际数组与后端转换为准。",
    ),
    "sites": (
        "Site 是附着参考坐标，不是碰撞形状",
        "Site 为末端控制、IMU 和其他传感器提供相对刚体的参考姿态；通过 label 匹配到机器人上的工具点或量测点。",
        "Site 位置与碰撞几何、COM 位置各有语义。控制器选 tool_sites 时每个受控机器人需匹配恰好一个。",
    ),
    "sensors": (
        "量测在物理步后的显式消费",
        "传感器在构建/初始化阶段声明所需资源；量测阶段调用 update。状态型、接触型、渲染型传感器的输入与刷新时机不同。",
        "SensorContact 消费 CONTACT_F 与绑定的 Contacts，不能只把几何接触数量当作接触力；原生 CPU 与 Warp 的支持不同。",
    ),
    "conventions": (
        "SI 单位、XYZW 四元数与参考系",
        "位置、质量、时间等采用官方约定；关节与刚体空间向量要同时注明线性/角度顺序、参考系和参考点。实际数组布局以 Control/State 字段文档为准。",
        "FREE/DISTANCE 的 joint_qd 与 joint_f 均以 child COM 为参考点，区别是表达参考系：joint_qd 在 joint parent frame，joint_f 在 world frame。body_qd=(v_COM, omega) 与 body_f=(force, torque_COM) 均为 world-frame、线性分量在前。不要把参考系旋转误作参考点平移。Control.clear(model) 可避免 coord layout 中四元数目标被零填坏。",
    ),
    "usd-parsing": (
        "USD 属性如何进入 Newton 模型",
        "add_usd 解析 supported schemas，把几何、刚体、关节、sites、材料和可变形体数据写入 builder。解析阶段先做单位、up-axis 和拓扑检查。",
        "不支持的 Schema 或属性不应被视为已复现物理。可视模型与 collision/solver 的支持需要后续独立验收。",
    ),
    "custom-attributes": (
        "frequency、assignment、namespace 与注册",
        "add_custom_attribute 在构建前声明 dtype、frequency、assignment、default、namespace 等，决定数组分配到 Model、State、Control 或 Contacts。solver 注册的字段需在构建/finalize 前准备好。",
        "None 占位声明不是物理默认。namespace 与 frequency 不是任意键值标签：world 合并、引用重映射和接触容量均影响分配。",
    ),
    "solver-observables": (
        "可选观测独立于 State 和 Contacts",
        "solver.observables(kinds,contacts=...) 分配请求的数组；CONTACT_F 需要先解析容量并绑定同一 Contacts。未请求字段为 None，请求但容量零的字段为空数组。分配后容量在该 Model 生命周期内冻结；删除 Observables 不解除冻结，修改容量必须新建 Model 和相应运行资源。",
        "container 属于创建它的 solver/model；step 与消费者必须使用相同 contact storage。原生碰撞需 solver 先建立导出容量；MuJoCo CPU 仅支持 QFRC_ACTUATOR。",
    ),
    "collisions": (
        "几何候选、接触存储与求解消费",
        "CollisionPipeline 用 world/collision filter、broad phase 和 narrow phase 产生 Contacts，再由 solver 计算响应。full surface 开关 enable_rigid_soft_full_surface_contact 属于公共管线，默认 False；现有 VBD A/B 检查粗三角面内接触。",
        "漏检、容量不足、初始穿透和 penalty 压入不同。VBD 开启 full surface 的案例仍有约 0.245 mm 终态压入。固定版本中 edge/face soft contacts 由 VBD 的受支持路径消费；XPBD、SemiImplicit、Style3D 的 particle-only 路径明确拒绝，VBD proxy-particle coupling 也不支持。不要把该边界泛化为所有仅消费 rigid_contacts 的后端都会抛错，也不要混同刚体 hydroelastic contact。",
    ),
    "simulation-tuning": (
        "先诊断、再调物理参数和数值预算",
        "先构造最小复现，再检查几何/初态、control、质量与驱动、容量，最后调整接触模型和 solver 预算。一次 step 的 iterations 与每帧 substeps 对应不同误差来源。",
        "更硬未必更稳定；把 penetration、轨迹、能量、接触力与成本一起量测。默认值以固定源码为准，实验取值不自动成为通用建议区间。",
    ),
    "coupling": (
        "共享 Model、ModelView 与所有权",
        "每个 Entry 的 solver(view) 工厂获得 ModelView，只对分配的 bodies/particles/shapes/joints 输出负责；耦合器复制输入力、按 entry substeps 推进、合并 owned rows 并通知私有缓存。",
        "Proxy 是滞后/交错代理反馈；ADMM 是接口约束迭代。接通 integrate_with_external_rigid_solver 单个开关不等同于已实现双向反馈。",
    ),
    "actuators": (
        "执行器模型与 solver 驱动的接口",
        "Drive 计算 effort，Delay 模拟命令延迟，Clamping 表达电机输出限制，最后 scatter-add 到控制数组。control target、驱动刚度/阻尼和力限共同决定跟踪响应。",
        "控制器求目标、执行器算 effort、solver 施加动力学三层要分清。保留直接后端 drive 时，避免和外部 effort 双重驱动。",
    ),
}

LIFECYCLE = """先确认 `solver.supported_observables`。接触索引量要求容量已解析、`contacts=contacts` 与后续 step/consumer 使用同一实例；分配之后容量在 Model 生命周期内冻结。修改冻结容量必须重新 finalize 得到新 Model，再创建 solver、pipeline、Contacts 和 Observables；仅删除/重建 Observables 不会解冻。同容量替换 storage 需重新绑定相应 Observables。组合传感器的 `solver_observable_kinds` 后一次分配，graph capture 前完成分配。

外部碰撞：pipeline → solver/contacts → observables → 每步 collide → step → sensor.update。
原生 MuJoCo：solver → 使用 get_max_contact_count 配置 pipeline → contacts → observables → step 导出几何和力；不调用 pipeline.collide。
Solver 自持碰撞：绑定 solver.contacts；step(..., contacts=None) 使用内部存储。

`CONTACT_F` 在 MuJoCo Warp、XPBD、VBD、Kamino 可用；native MuJoCo CPU (`use_mujoco_cpu=True`) 仅支持 `QFRC_ACTUATOR`，因此不能走本接触力配方。MuJoCo Warp 可在 CPU 或 GPU 运行，依赖与硬件条件另行核对。
SensorContact 用 `update(state_in, contacts, observables=observables)` 消费接触；Kamino 的接触点在输入 body frame，原位步进也需保留输入位姿。IMU 等状态型传感器按其 API 消费 `state_out`，不要统一套用输出 state。"""

CONTROL = """导入机器人后保留 articulation、joint、site 的 label/index 映射。IKSolver 求运动学目标；ControllerDifferentialIK 用模型内 FK/Jacobian 每步求控制信号，`step(inputs=..., outputs=..., dt=...)`，每个受控 articulation 匹配一个工具 site，只控制一坐标一 DOF 的关节。它能处理异构受控机器人集合，但 ArticulationView 当前的批量布局假设同质，两者能力不能混用。

`newton.use_coord_layout_targets` 在创建任何模型前一次设置。启用 coord layout 时 `Control.joint_target_q` 对齐 `joint_coord_count`，`joint_target_qd` 和 `joint_f` 对齐 `joint_dof_count`；使用 `joint_target_q_start` 等映射，不按 qd offset 盲写四元数目标。`Control.clear(model)` 恢复合法初始坐标目标。

Controller 输出通过真实端口与选中关节映射写 Control，配置该 solver 支持的驱动，再走求解循环。对 MuJoCo 核查模型转换后的 drive、力限与 backend 选项；IK 本身不确保碰撞可行、力矩可行或接触稳定。"""

RESET = """通过 ModelBuilder.add_world / replicate 构建同质批量，检查 Model.*_world 与 *_world_start。ArticulationView 按 articulation label/index 创建视图，先读取选中对象的真实布局，再用 set_attribute(name,target,values,mask=...) 局部写入。

ArticulationView 的 mask 是 `(view.world_count,)` 或 `(view.world_count, count_per_world)`；solver.reset 的 world_mask 是 `(model.world_count+1,)`，最后一项选择 global world -1。两种掩码不可直接复用；global 实体还可能位于数组前后两段。

先按 mask 恢复公共 State 与 Control 的物理初态，再按后端要求 `solver.reset(state, world_mask=mask, flags=...)` 同步私有历史和缓存。SolverBase 默认 reset 仅校验掩码，是 no-op；不能宣称任何 solver.reset 都自动恢复全部初态。MuJoCo / VBD / Kamino 的具体缓存、global 行为和 backend 条件需读取对应 override；状态双缓冲也需一致处理。模型属性改动另走 notify_model_changed。"""

COUPLING = """从 `newton.solvers.experimental.coupled` 导入 ModelView、SolverCoupled、SolverCoupledProxy、SolverCoupledADMM。共享一个 Model，用 Entry 的 bodies/particles/shapes/joints 划分所有权，并在 solver(view) 工厂中绑定 MuJoCo 或 VBD 的构造参数。每个 entry 可有自己的 substeps；只有 owned outputs 合并回共享 state_out。

Proxy 将 source 的真实端点映射为 destination 中的代理端点，按 lagged/staggered 调度，结合质量缩放、relaxation 与反馈 harvest。通用 proxy loop 当前最多两个 entries。代理局部碰撞可由工厂创建并缓存 contacts；反馈不是简单复制位置。

ADMM 在接口上恢复局部状态、推进 subsolvers、解约束行、更新 dual，并注入相反方向的力。跨 solver model joints 支持 BALL/FIXED/REVOLUTE；PRISMATIC/DISTANCE/D6 接口行尚未支持。跨 solver attachment 使用 ModelBuilder.add_attachment_particle_body；接触须显式配置 ContactPair，coupler 有私有检测与固定容量缓存，按源文档处理避免重复求解同一约束。

`integrate_with_external_rigid_solver` 只描述 VBD 与外部刚体步进的一个开关；双向耦合还要求 ownership、接触、反馈、私有历史通知和子步调度。此知识配方有官方源码/示例依据，尚未作为本库物理任务执行；外部共享 Contacts、entry 内部检测和 ADMM 私有接触不能无条件共用。"""

DIFF = """固定版本官方能力表中，仅 SolverSemiImplicit 和 SolverFeatherstone 标为 basic 可微；SolverVBD、SolverXPBD、MuJoCo、Kamino、ImplicitMPM、Style3D 均未标为可微支持。`requires_grad=True` 分配梯度缓冲不能改变这个能力边界，尤其不能从 Warp 语言可微推断任一 solver 可微。

官方最小流程：builder.finalize(requires_grad=True)，分配带梯度 State 和 loss，在 `with wp.Tape():` 内执行 forward rollout 和标量 loss，然后 `tape.backward(loss)`。多步优化需要保存 Tape 所需的状态历史，不能随意双缓冲覆盖中间量；具体示例看 newton/examples/diffsim。

本条是源码与官方示例解释，没有在本知识库中完成梯度数值检验。外部 simulator 的可微能力、控制器可微能力和 Newton backend 的梯度支持分别判断。"""

RECIPES = {
    "external-collision": (
        "外部碰撞与接触力的调用顺序",
        LIFECYCLE
        + """\n\n```python
pipeline = newton.CollisionPipeline(model)
solver = newton.solvers.SolverXPBD(model)
contacts = pipeline.contacts()
observables = solver.observables(kinds={solver.ObservableKind.CONTACT_F}, contacts=contacts)
# 每个子步，state_in / state_out 已由 model.state() 分配
state_in.clear_forces()
pipeline.collide(state_in, contacts)
solver.step(state_in, state_out, control, contacts, dt, observables=observables)
# 有 SensorContact 时先用输入位姿消费接触，再交换 state
contact_sensor.update(state_in, contacts, observables=observables)
state_in, state_out = state_out, state_in
```
前提：contact_sensor 已针对同一 Model 构建；该片段是顺序配方，不是独立可运行资产脚本。示例 backend 是 XPBD，不暗示所有 solver 消费该接触格式。""",
    ),
    "solver-owned-collision": (
        "VBD 使用 solver 持有的碰撞资源",
        LIFECYCLE
        + "\n\n具体配方选择 VBD：先 `pipeline = newton.CollisionPipeline(model)`，再 `solver = newton.solvers.SolverVBD(model, collision_pipeline=pipeline)`，让 solver 持有 pipeline 和其 Contacts。绑定 `observables = solver.observables(kinds=needed, contacts=solver.contacts)`，每步 step 传 contacts=None；不要同时运行一条无关外部管线或绑定新 Contacts。该构造来自 SolverVBD 的 collision_pipeline 参数；不能把此配置推广为所有 backend 的构造默认。",
    ),
    "mujoco-native-contact": (
        "MuJoCo Warp 原生碰撞导出与 SensorContact",
        LIFECYCLE
        + """\n\n```python
# use_mujoco_cpu=False 选 MuJoCo Warp；use_mujoco_contacts=True 选原生碰撞
solver = newton.solvers.SolverMuJoCo(model, use_mujoco_cpu=False, use_mujoco_contacts=True)
pipeline = newton.CollisionPipeline(model, rigid_contact_max=solver.get_max_contact_count(), soft_contact_max=0)
contacts = pipeline.contacts()
sensor = newton.sensors.SensorContact(model, sensing_shapes="foot_*", request_contact_attributes=False)
observables = solver.observables(kinds=sensor.solver_observable_kinds, contacts=contacts)
# 预分配输入/输出 state 和 control；原生后端填充 Contacts，无 pipeline.collide
solver.step(state_in, state_out, control, contacts, dt, observables=observables)
sensor.update(state_in, contacts, observables=observables)
```
前提：模型确有 foot_* sensing shapes、设备一致且容量充足。本库尚未执行该组合传感器物理任务；配方的顺序来自固定官方文档。""",
    ),
    "coupled-rigid-deformable": ("MuJoCo 刚体与 VBD 布料：所有权和双向耦合", COUPLING),
    "ik-mujoco-contact": (
        "多机器人 IK / controller → MuJoCo → 接触力量测",
        CONTROL
        + "\n\n## World、选择与复位\n\n"
        + RESET
        + "\n\n## 接触量测顺序与支持条件\n\n"
        + LIFECYCLE
        + "\n\n这是导入、选取、控制、碰撞与量测的组合配方，有来源但尚无本库端到端实测。需要运行时先选定资产、joint/site/shape labels 与 MuJoCo Warp 依赖，再验证控制信号和接触量测。",
    ),
    "worlds-reset": ("部分 world 的机器人控制与掩码复位", RESET),
}

STAGE_TEXT = {
    "asset_import": (
        "把真实资产变成可审查的 builder 输入",
        "输入：原语/URDF/MJCF/USD、尺度、坐标和初态。输出：ModelBuilder 的刚体、关节、形状、sites、材料与驱动。先核对单位、轴向、labels、碰撞/视觉几何和导入 warning；保留资产哈希与 importer 配置。",
        "module:usd concept:usd-parsing concept:conventions concept:articulations",
    ),
    "preprocess": (
        "配置构建期预处理，并检查 finalize 的派生结果",
        "输入：导入后的 builder。finalize 前配置几何、拓扑和 collision filter，显式完成 mesh approximation 与 solver 所需着色；对 VBD 等路径按示例调用 builder.color()。finalize 内还可能生成 deferred SDF、分配设备资源并验证/修正质量惯量，因此不能把 finalize 当作纯数据搬运。完成后检查 Model 实际数组与 warning，保存近似/SDF 参数和产物；增加迭代不能弥补漏掉的几何或错误过滤。",
        "module:geometry module:utils concept:mass-inertia concept:deformables concept:collisions",
    ),
    "initialization": (
        "Model、运行状态与资源的分配顺序",
        "输入：已配置 builder 与选定 backend。先在 builder 阶段注册 custom attributes 与 solver 扩展字段，再 finalize 得到 Model。SensorIMU 等接受 Model 的传感器在此后创建；legacy State 字段请求须在 model.state() 前完成，solver Observables 在 solver 构造和接触容量解析后分配。输出为 Model、双缓冲 State、Control、Contacts、solver 与可选 Observables；graph capture 前预分配。原生碰撞与外部碰撞顺序不同，按配方选择。",
        "module:newton concept:custom-attributes concept:solver-observables recipe:external-collision recipe:mujoco-native-contact",
    ),
    "control": (
        "先形成可解释的输入，再推进物理",
        CONTROL
        + "\n\n每个子步清理 State 外力，按实际调度写 targets/effort；Actuator scatter-add 输出需要调用方清零。记录 controller/drive/solver 三层的参数来源。",
        "module:controllers module:ik module:actuators topic:robot-control",
    ),
    "collision": (
        "从当前位姿生成有效 Contacts",
        "输入：当前 State 的 body/particle 位姿、Model 几何/过滤与 pipeline 配置。输出：有固定容量与原始计数的接触存储；溢出时 raw count 可超过容量，读取刚体存储行应限制为 min(raw_count, capacity)，并另报溢出，不能把被丢接触算成有效记录。外部模式调用 collide；MuJoCo 原生模式由 solver 导出。碰撞覆盖、接触材料、solver 响应分开诊断。full surface contact 是 CollisionPipeline 开关；其 edge/face soft records 由 VBD 指定路径消费，particle-only 消费器明确拒绝，并非支持状态未知。",
        "concept:collisions pipeline:enable_rigid_soft_full_surface_contact recipe:external-collision recipe:mujoco-native-contact",
    ),
    "solver_step": (
        "control → collision detection → solver.step()",
        "输入：Model、state_in、Control、匹配的 Contacts 和子步 dt。输出：state_out 与请求的 Observables。使用具体 solver 的坐标、碰撞和驱动支持；每帧 substeps 决定 dt，iterations 仅是一次 step 的内部预算。更新传感器后交换 State；复位或 Model 修改时同步后端私有缓存。",
        "stage:control stage:collision module:solvers topic:coupling topic:differentiable-simulation process:substeps",
    ),
    "output": (
        "观测、回放与可复现结果导出",
        "输入：物理状态、Contacts、Observables 与仿真时间。输出：Sensor 量测、Viewer 显示、USD/图像/轨迹和指标。保存单位、采样频率、run ID、配置差异、依赖、设备与 raw hash；渲染帧率不能替代仿真步长。接触传感器按输入位姿消费，普通状态显示通常取推进后的 state。",
        "module:sensors module:viewer topic:lifecycle-observation",
    ),
}


def main():
    registry = json.loads(
        (ROOT / "knowledge/registry.json").read_text(encoding="utf-8")
    )
    lock = json.loads((ROOT / "manifests/source-lock.json").read_text(encoding="utf-8"))
    api = inventory(registry)
    symbols = {s["public_name"]: s for s in api}
    records = {}
    relations = []

    def ref(path, needle=None):
        text = (SRC / path).read_text(encoding="utf-8").splitlines()
        line = next(
            (i + 1 for i, v in enumerate(text) if needle and v.strip() == needle), None
        )
        if line is None:
            line = next(
                (i + 1 for i, v in enumerate(text) if needle and needle in v), 1
            )
        return {
            "path": path,
            "line": line,
            "commit": COMMIT,
            "sha256": lock["files"][path],
            "url": f"https://github.com/newton-physics/newton/blob/{COMMIT}/{path}#L{line}",
        }

    def add(rid, summary, body, paths=(), symbol_names=(), related=()):
        entry = next(e for e in registry["entries"] if e["id"] == rid)
        detail = COMMON_DETAILS.get(rid)
        if detail:
            body += "\n\n" + detail["body"].strip()
        if entry["family"] == "api":
            paths = [
                *paths,
                "docs/api/newton"
                + ("" if rid == "module:newton" else "_" + rid.split(":")[-1])
                + ".rst",
            ]
        if entry["family"] == "recipe":
            body += """\n\n## 调度的五个时段

| 时段 | 本配方的责任 |
|---|---|
| Setup | 根据上述 backend 条件完成 Model、State、Control、Contacts 和 Observables；先解析容量，绑定同一 storage；graph capture 前完成分配与所需 warmup。 |
| 每仿真子步 | 清理外力、施加持有或新控制输入；外部模式每子步 collide，自持/原生模式由 step 按其碰撞调度更新；step 产生新状态和本子步观测。 |
| 每控制帧 | 仅在控制周期更新 IK/controller/轨迹目标；周期内按应用约定持有目标，不把控制帧率误当仿真 dt。 |
| 每输出帧 | 按采样周期消费最新有效观测；接触传感器使用对应的输入位姿，其他传感器按 API 读取所需 State；记录准确仿真时间并渲染/导出。 |
| Reset / Model 更新 | 按掩码恢复公共状态/控制并调用受支持的 solver.reset；Model 更新用 notify_model_changed 的后端支持 flags。改变已被 Observables 冻结的容量必须新建 Model 及相应 solver/Contacts/Observables；其他拓扑、分配或指针变化按后端重建资源并重新捕获，不假定已有 graph 自动反映任意 Python 参数变动。 |

配方中的控制与输出调度由调用方明确；本库没有把所有时段强制合并到每个 step。"""
        if rid == "topic:development-testing":
            body += "\n\n## Examples 的校验钩子\n\n每个 Newton example 必须实现 `test_final()`；可选 `test_post_step()` 在每仿真步后检查，`test_final()` 在示例结束时检查。失败要区分环境/设备/依赖、数值非有限、物理断言和性能问题；跳过或环境受限不能记为测试通过。类型/签名、单位、docstring 和 Warp 数组布局按 CODING_GUIDELINES.rst；本文只列命令和规定，没有伪造上游执行结果。\n"
        refs = [ref(entry["source_refs"][0]["path"])] + [
            ref(p) if isinstance(p, str) else ref(*p) for p in paths
        ]
        if detail:
            for path, line, end_line in detail["refs"]:
                source_lines = (SRC / path).read_text(encoding="utf-8").splitlines()
                if not 1 <= line <= end_line <= len(source_lines):
                    raise ValueError(f"Invalid common-content source range: {path}:{line}-{end_line}")
                refs.append({
                    "path": path,
                    "line": line,
                    "end_line": end_line,
                    "commit": COMMIT,
                    "sha256": lock["files"][path],
                    "url": f"https://github.com/newton-physics/newton/blob/{COMMIT}/{path}#L{line}-L{end_line}",
                })
        for name in symbol_names:
            if name not in symbols:
                raise ValueError("Unresolved curated symbol " + name)
            s = symbols[name]
            refs.append(
                ref(
                    s["path"],
                    (SRC / s["path"])
                    .read_text(encoding="utf-8")
                    .splitlines()[s["line"] - 1]
                    .strip(),
                )
            )
            # ref() selects a literal match; use the AST's exact declaration line.
            refs[-1].update(
                line=s["line"],
                url=f"https://github.com/newton-physics/newton/blob/{COMMIT}/{s['path']}#L{s['line']}",
            )
        refs = list({(r["path"], r["line"]): r for r in refs}.values())
        body = (
            "# "
            + entry["title"]
            + "\n\n"
            + summary
            + "。\n\n"
            + body.strip()
            + "\n\n## 证据与适用边界\n\n本页为 Newton 1.7.0 固定源码和官方文档解释。调用配方不表示本库已执行物理任务；实测证据单独保存在 solver 实验记录中。公开可达、后端支持、已解释与实测四项分别判断。\n"
        )
        if symbol_names:
            body += (
                "\n## 精确 API 入口\n\n"
                + "\n".join(
                    f"- [{n}](#/record/{quote('symbol:' + n, safe='')})"
                    for n in symbol_names
                )
                + "\n"
            )
        if related:
            body += (
                "\n## 相关知识\n\n"
                + "\n".join(f"- [{n}](#/record/{quote(n, safe='')})" for n in related)
                + "\n"
            )
        doc = next(
            (
                r["path"]
                for r in refs
                if r["path"].startswith("docs/") and r["path"].endswith(".rst")
            ),
            None,
        )
        if doc:
            # Surface the official page, clearly separating floating web navigation from pinned evidence.
            web = (
                "https://newton-physics.github.io/newton/latest/" + doc[5:-4] + ".html"
            )
            body += (
                "\n官方阅读入口（latest 可能已变更，本文结论以固定 commit 为准）：[Newton 官方文档]("
                + web
                + ")。\n"
            )
        body += (
            "\n## 固定版本原始出处\n\n"
            + "\n".join(f"- [{r['path']}:{r['line']}]({r['url']})" for r in refs)
            + "\n"
        )
        applicable = (
            [entry["solver"]]
            if entry["family"] == "solver"
            else registry["solver_keys"]
        )
        if rid in ("recipe:mujoco-native-contact", "recipe:ik-mujoco-contact"):
            applicable = ["mujoco"]
        elif rid == "recipe:external-collision":
            applicable = ["xpbd"]
        elif rid == "recipe:solver-owned-collision":
            applicable = ["vbd"]
        elif rid in (
            "recipe:coupled-rigid-deformable",
            "topic:coupling",
            "concept:coupling",
        ):
            applicable = ["mujoco", "vbd"]
        elif rid == "topic:differentiable-simulation":
            applicable = ["semi-implicit", "featherstone"]
        elif rid in ("module:controllers", "module:ik", "topic:robot-control"):
            applicable = [
                "mujoco",
                "featherstone",
                "kamino",
                "vbd",
                "xpbd",
                "semi-implicit",
            ]
        records[rid] = {
            "summary": summary,
            "body": body,
            "source_refs": refs,
            "support_status": "supported",
            "applicable_solvers": applicable,
            "runtime_status": "not_run",
            "evidence_type": "source_checked",
        }
        for target in related:
            relations.append(
                {
                    "source": rid,
                    "target": target,
                    "relation": "related_workflow",
                    "source_refs": refs[:2],
                    "evidence_type": "source_checked",
                    "scope": "navigation association; not causal inference",
                }
            )
        for name in symbol_names:
            relations.append(
                {
                    "source": rid,
                    "target": "symbol:" + name,
                    "relation": "uses_public_api",
                    "source_refs": refs,
                    "evidence_type": "source_checked",
                }
            )

    for key, (summary, mechanism, pitfalls, doc, syms) in MODULES.items():
        entry = next(e for e in registry["entries"] if e["id"] == "module:" + key)
        exports = entry["public_exports"]
        exportlinks = "\n".join(
            f"- [{n}](#/record/{quote('symbol:' + entry['owner_module'] + '.' + n, safe='')})"
            for n in exports
            if entry["owner_module"] + "." + n in symbols
        )
        body = (
            "## 职责、输入与输出\n\n"
            + mechanism
            + "\n\n## 失败模式与限制\n\n"
            + pitfalls
            + "\n\n## 模块公开导出索引\n\n"
            + exportlinks
        )
        related = {
            "controllers": [
                "module:ik",
                "topic:robot-control",
                "recipe:ik-mujoco-contact",
            ],
            "ik": ["topic:robot-control", "recipe:ik-mujoco-contact"],
            "sensors": [
                "concept:solver-observables",
                "recipe:mujoco-native-contact",
                "recipe:ik-mujoco-contact",
            ],
            "selection": [
                "concept:worlds",
                "topic:worlds-batching",
                "recipe:worlds-reset",
            ],
            "solvers": [
                "topic:differentiable-simulation",
                "concept:coupling",
                "solver:vbd",
                "solver:xpbd",
            ],
            "geometry": ["concept:collisions", "stage:preprocess"],
        }.get(key, [])
        add("module:" + key, summary, body, [doc], syms, related)
    for key, (summary, mechanism, pitfall) in CONCEPTS.items():
        related = {
            "collisions": [
                "pipeline:enable_rigid_soft_full_surface_contact",
                "lab:full_surface",
                "stage:collision",
            ],
            "solver-observables": [
                "module:sensors",
                "recipe:mujoco-native-contact",
                "recipe:ik-mujoco-contact",
            ],
            "worlds": [
                "module:selection",
                "topic:worlds-batching",
                "recipe:worlds-reset",
            ],
            "coupling": [
                "topic:coupling",
                "recipe:coupled-rigid-deformable",
                "solver:vbd",
                "solver:mujoco",
            ],
        }.get(key, [])
        extra = (
            LIFECYCLE
            if key == "solver-observables"
            else COUPLING
            if key == "coupling"
            else RESET
            if key == "worlds"
            else ""
        )
        syms = {
            "solver-observables": [
                "newton.solvers.SolverBase.observables",
                "newton.sensors.SensorContact.update",
            ],
            "worlds": [
                "newton.ModelBuilder.replicate",
                "newton.selection.ArticulationView.set_attribute",
            ],
            "collisions": [
                "newton.CollisionPipeline",
                "newton.CollisionPipeline.collide",
            ],
            "sites": ["newton.ModelBuilder.add_site"],
        }.get(key, [])
        add(
            "concept:" + key,
            summary,
            "## 机制与数据流\n\n"
            + mechanism
            + "\n\n## 诊断与边界\n\n"
            + pitfall
            + "\n\n"
            + extra,
            [],
            syms,
            related,
        )
    topics = {
        "robot-control": (
            "IK/controller、Control 布局与驱动分工",
            CONTROL,
            ["docs/migration.rst", "docs/concepts/actuators.rst"],
            ["newton.controllers.ControllerDifferentialIK", "newton.Control"],
            [
                "module:controllers",
                "module:ik",
                "module:selection",
                "recipe:ik-mujoco-contact",
                "solver:mujoco",
            ],
        ),
        "worlds-batching": (
            "World 索引、选择掩码与 solver 复位",
            RESET,
            ["newton/_src/core/reset.py"],
            [
                "newton.selection.ArticulationView",
                "newton.solvers.SolverBase.reset",
                "newton.solvers.SolverMuJoCo.reset",
            ],
            ["concept:worlds", "module:selection", "recipe:worlds-reset"],
        ),
        "coupling": (
            "MuJoCo 刚体 / VBD 布料：Proxy 与 ADMM",
            COUPLING,
            ["newton/examples/multiphysics/example_mujoco_vbd_coupled_solver.py"],
            [],
            [
                "concept:coupling",
                "recipe:coupled-rigid-deformable",
                "solver:vbd",
                "solver:mujoco",
            ],
        ),
        "differentiable-simulation": (
            "requires_grad、Warp Tape 与后端能力表",
            DIFF,
            [
                ("docs/solvers/index.rst", "Differentiability"),
                "newton/examples/diffsim/example_diffsim_ball.py",
            ],
            ["newton.ModelBuilder.finalize", "newton.solvers.SolverSemiImplicit"],
            [
                "module:solvers",
                "solver:vbd",
                "solver:xpbd",
                "solver:semi-implicit",
                "solver:featherstone",
            ],
        ),
        "lifecycle-observation": (
            "State、Contacts、Observables 的初始化与复用",
            LIFECYCLE + "\n\n" + RESET,
            ["docs/concepts/sensors.rst"],
            ["newton.sensors.SensorContact.update", "newton.State.clear_forces"],
            [
                "concept:solver-observables",
                "recipe:external-collision",
                "recipe:solver-owned-collision",
                "recipe:mujoco-native-contact",
            ],
        ),
        "environment": (
            "依赖、设备与兼容条件",
            "Python、Warp、Newton 和可选后端依赖共同决定运行条件；以该 release 的 pyproject.toml、uv.lock 和兼容文档为准。MuJoCo native CPU 与 MuJoCo Warp 区别于计算设备 cpu/cuda；Warp 版本与驱动兼容单独核查。无 GPU 不意味着所有 solver 都不能运行。\n\n安装工作流可用 uv sync --extra dev 或独立 venv；本库固定源码快照不应为试验安装而被修改。记录 Python、OS、Newton/Warp/backend 版本与设备。网页/MCP 是只读索引服务，读取不执行 solver。",
            [
                "pyproject.toml",
                "docs/guide/installation.rst",
                "docs/guide/development.rst",
            ],
            [],
            ["topic:development-testing", "topic:migration-integrations"],
        ),
        "development-testing": (
            "Newton coding style、公共 API 与测试入口",
            "__all__ 是公开导出的权威；通过 newton.* 公开路径导入，_src 是内部实现。命名采用 Solver*/Viewer*/IKObjective* 等共同前缀；保持可选 backend 懒加载，experimental 和弃用边界明确，避免不相关清理或破坏兼容。\n\nNewton 上游测试入口：`uv run --extra dev -m newton.tests` 或 `python -m newton.tests`。默认最多 8 进程，资源不足用 `--jobs 4` 或 `--serial-fallback`。示例可 `python -m newton.tests.test_examples -k test_basic.example_basic_shapes`。代码检查用 `uvx pre-commit run -a`；覆盖率可 `--coverage --coverage-html htmlcov`。\n\n这些是固定官方开发命令，本文没有执行上游完整测试。知识库自身的数据/网站/MCP/物理实验验收单独记录，不用 RoboSimStudio 的测试 tier 替代 Newton 测试。",
            [
                "CODING_GUIDELINES.rst",
                "docs/guide/source_code_guidelines.rst",
                "newton/tests/__main__.py",
            ],
            [],
            ["topic:environment", "topic:migration-integrations"],
        ),
        "migration-integrations": (
            "迁移时核对字段、布局和外部集成",
            "逐条检查 migration 文档中的 removed/deprecated 属性、坐标布局、Control targets、sensor/observable API 和 importer 变化。use_coord_layout_targets 应在建模前设置；joint_target_q 可能按坐标而 joint_target_qd 按 DOF。Actuator 的 controller 旧别名迁移到 drive 命名。\n\nMuJoCo 转换、USD schema 与 viewer 输出分别有集成边界。固定旧版本记录与新版本记录独立保存，不能把 latest 文档或其他版本实验默认继承到 Newton 1.7.0。",
            [
                "docs/guide/compatibility.rst",
                "docs/concepts/actuators.rst",
                "docs/concepts/usd_parsing.rst",
            ],
            ["newton.Control"],
            ["topic:environment", "module:usd", "solver:mujoco"],
        ),
    }
    for key, (summary, body, paths, syms, related) in topics.items():
        add("topic:" + key, summary, body, paths, syms, related)
    for key, (summary, body, related) in STAGE_TEXT.items():
        docs = {
            "asset_import": "docs/concepts/usd_parsing.rst",
            "initialization": "docs/concepts/solver_observables.rst",
            "preprocess": "docs/concepts/mass_inertia.rst",
            "control": "docs/migration.rst",
            "output": "docs/concepts/sensors.rst",
        }
        add(
            "stage:" + key,
            summary,
            body,
            [docs[key]] if key in docs else [],
            [],
            related.split(),
        )
    for key, (summary, body) in RECIPES.items():
        paths = ["docs/concepts/solver_observables.rst"]
        related = []
        syms = []
        if key == "ik-mujoco-contact":
            paths += [
                "docs/migration.rst",
                "newton/examples/controllers/example_controller_differential_ik.py",
            ]
            related = [
                "module:controllers",
                "module:ik",
                "module:selection",
                "concept:solver-observables",
                "solver:mujoco",
                "recipe:mujoco-native-contact",
            ]
            syms = ["newton.controllers.ControllerDifferentialIK.step"]
        elif key == "coupled-rigid-deformable":
            paths += [
                "newton/examples/multiphysics/example_mujoco_vbd_coupled_solver.py"
            ]
            related = [
                "concept:coupling",
                "topic:coupling",
                "solver:mujoco",
                "solver:vbd",
            ]
        elif key == "worlds-reset":
            paths += [
                "newton/_src/core/reset.py",
                "newton/examples/selection/example_selection_cartpole.py",
            ]
            related = ["concept:worlds", "module:selection", "topic:worlds-batching"]
            syms = [
                "newton.solvers.SolverBase.reset",
                "newton.solvers.SolverMuJoCo.reset",
            ]
        else:
            related = ["concept:solver-observables", "module:sensors"]
            syms = [
                "newton.solvers.SolverBase.observables",
                "newton.sensors.SensorContact.update",
            ]
        add("recipe:" + key, summary, body, paths, syms, related)
    caps = {
        "vbd": "隐式 VBD，统一 cloth、soft bodies、particles 和 rigid bodies；关节支持有限，当前 experimental。可选构造 iterations 默认 10。已有 17 组保存的 CPU A/B，47 个可选构造参数中直接变化 9 个；其他是 Model/管线/流程组。官方能力表不支持可微。",
        "mujoco": "广义坐标刚体/关节，转换 Newton Model 到 MuJoCo；默认使用内置碰撞。区分 native MuJoCo CPU 与 MuJoCo Warp。iterations 声明 None，按显式值/模型自定义属性/后端默认解析；不与 VBD 相同迭代数直接比较。CONTACT_F 仅 Warp 路径；当前本库无其保存 A/B。",
        "kamino": "最大坐标刚体与闭环约束、硬摩擦接触，BETA 1 / experimental。分层 Config/PADMM/DVI，config.padmm.max_iterations 声明默认 200；不与其他后端预算等价。无布料/软体/粒子求解支持；当前本库无其保存 A/B。",
        "featherstone": "广义坐标 articulation，半隐式积分；支持刚体、粒子与软体，cloth 不支持自碰撞。官方可微性为 basic，需按 diffsim 示例验证。首版只有源码索引，无本库完整参数与物理实验解释。",
        "semi-implicit": "最大坐标半隐式积分，支持刚体、关节、粒子与软体，cloth 无自碰撞。官方可微性为 basic，文档 Tape 示例使用此 backend。首版只有源码索引，未整理参数与实测。",
        "xpbd": "XPBD 约束求解与最大坐标关节，支持刚体/粒子，cloth 无自碰撞，soft bodies 标 experimental。固定版本官方表不支持可微；CONTACT_F 可用但需明确分配。首版为源码索引，未整理的参数返回 not_indexed。",
        "implicit-mpm": "隐式粒子 MPM 材料后端，官方表粒子支持，不提供刚体关节、cloth、soft-body 离散模型或可微能力。具体材料/网格/接触路径需读公开类。首版源码索引，无完整参数与 A/B。",
        "style3d": "隐式粒子/cloth 后端，官方表支持 particles/cloth，不支持刚体关节与四面体 soft bodies，未标可微。首版源码索引，无完整参数与保存 A/B。",
    }
    measured_catalog = ROOT / "experiments/solver_parameter_lab/catalog.json"
    if measured_catalog.exists():
        measured = json.loads(measured_catalog.read_text(encoding="utf-8"))
        if measured.get("status") == "passed":
            for solver in ("mujoco", "kamino"):
                count = sum(c["solver"] == solver for c in measured["cases"])
                caps[solver] = caps[solver].replace(
                    "当前本库无其保存 A/B。",
                    f"本库有 {count} 组保存的 CPU A/B，每个参数值独立进程复现两次；结论仅限保存场景、后端与参数组。",
                )
    for solver, body in caps.items():
        entry = next(e for e in registry["entries"] if e["id"] == "solver:" + solver)
        syms = ["newton.solvers." + entry["public_class"]]
        related = ["module:solvers"] + (
            ["topic:differentiable-simulation"]
            if solver in ("vbd", "xpbd", "semi-implicit", "featherstone")
            else []
        )
        add(
            entry["id"],
            entry["title"] + "：正式公开类、能力边界与覆盖状态",
            body,
            ["docs/solvers/index.rst"]
            + (
                ["docs/solvers/" + solver + ".rst"]
                if solver in ("vbd", "mujoco", "kamino")
                else []
            ),
            syms,
            related,
        )
    if set(records) != {e["id"] for e in registry["entries"]}:
        raise ValueError("Coverage entry mismatch")
    target = ROOT / "knowledge/authored.json"
    target.write_text(
        json.dumps(
            {
                "version": "1.7.0",
                "commit": COMMIT,
                "records": records,
                "relations": relations,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "authored_entries": len(records),
                "curated_navigation_edges": len(relations),
                "public_symbols": len(api),
            }
        )
    )


if __name__ == "__main__":
    main()
