"""Author P3's task-depth records against the separately frozen questions."""

import hashlib
import json
from urllib.parse import quote

from plan_p0 import ROOT, SRC, COMMIT
from source_api import inventory

TEXT = {
    "X01": (
        "坐标布局、索引和清理是三个独立动作。先在创建模型前设置 newton.use_coord_layout_targets；coord layout 下 joint_target_q 的长度是 joint_coord_count，joint_target_qd/joint_f 是 joint_dof_count。FREE/BALL/DISTANCE 含四元数，不能把 qd 的 DOF offset 当作 q 的坐标 offset。",
        """1. 从 Model 的 joint_target_q_start 与 joint_q/qd_start 核查每个关节的真实切片，再映射 controller 输出；只写被控制的关节。
2. Reset 时使用 `control.clear(model)`：它从 model.joint_target_q 恢复合法坐标目标；不给 model 的兼容路径会零填，四元数槽可能成为 (0,0,0,0)。
3. State.clear_forces 处理外力，执行器输出清零处理累加，Control.clear(model) 处理控制初态，不能把这三个调用混为同一个每步必做动作。
4. 比较当前与目标四元数的有效性、关节切片长度及速度单位，再排查增益或 solver 迭代。""",
        ["topic:robot-control", "concept:conventions", "module:selection"],
    ),
    "X02": (
        "Actuator 的输出是 effort 的 scatter-add，调用方必须先清零将被累加的输出。Delay 读取命令历史，Drive 算原始 effort，Clamping 按电机模型限制输出，然后累加并更新 drive/delay 状态。",
        """1. 检查实际执行器写入哪个控制输出数组，只清理该 effort 累加缓冲，保留需要持有的 targets。
2. 记录每个 actuator 的步进周期。Delay 的 N 个 timesteps 指执行器步，而不是渲染帧；控制更新频率与仿真子步的比例必须明确。
3. 如果 solver 同时启用同一关节的内置驱动，明确外部 effort 是替代、附加前馈还是另一项物理力，避免重复计算同一 PD 项。
4. 初版一执行器一 DOF，不含通用 transmission 与完整电机动力学；可微与 graphable 取决于 drive 的实现，不由 Actuator 名称自动保证。
5. Reset 同时考虑 Delay/Drive 的历史，按其接口处理；本配方不把所有执行器 reset 等价于 solver.reset。""",
        ["module:actuators", "concept:actuators", "stage:control"],
    ),
    "X03": (
        '先查看碰撞形状，再比较视觉网格。ModelBuilder.approximate_meshes 默认 method="convex_hull"；凸包会填平凹洞，不适合作为保留容器内腔的保证。',
        """1. 需要非凸分解时显式选择 coacd/vhacd，并固定依赖、shape_indices 与 remeshing 参数。官方代码在缺依赖或失败且 raise_on_failure=False 时可回退 convex_hull 等后续方法。
2. 若回退不可接受，使用 raise_on_failure=True 并检查返回的实际形状集合与 warning。keep_visual_shapes 控制保留视觉形状，不能证明碰撞近似保真。
3. 核查每个 shape 的 collision/visibility 标记、world 分配与 add_shape_collision_filter_pair；碰撞过滤配对会移除候选，不能靠提高 iterations 恢复。
4. 用截面、接触记录和探针位置检查内腔与壁厚，再核查质量/惯量。预处理产物和参数要保存；本库没有替用户执行本次网格分解。
5. 接着按目标 solver 的 mesh 支持和导入转换规则确认最终使用的几何。""",
        ["stage:preprocess", "module:geometry", "module:utils", "concept:collisions"],
    ),
    "X04": (
        "live contact count 要区分原始计数 raw_count 与已存储行数：刚体写入先递增计数，溢出时 raw_count 可超过 capacity，不能直接作为数组遍历上限。capacity 是已分配数组大小；CONTACT_F 分配按 rigid_contact_max + soft_contact_max，刚体槽在前，软接触槽在后。零接触不表示零容量。",
        """1. 在分配接触观测前确定所选碰撞路径的容量，创建 Contacts，再给 solver.observables(kinds={CONTACT_F}, contacts=contacts)。即使容量为零也要绑定 Contacts。
2. 分配后容量冻结在 Model 上；删除 Observables 不能解除冻结。修改已冻结容量必须从 builder 重新 finalize/new Model，再构造 solver、pipeline、Contacts 与 Observables。同容量更换 storage 也必须重新绑定相应观测；捕获了旧数组指针时还要重新捕获。
3. 刚体数组只读取 min(raw_count, capacity) 行，并单独报告 raw_count > capacity 的 overflow。分别检查 broad-phase/triangle-pair/reduction 中间缓冲、solver 内部每对象接触列表和求解约束容量；最终计数未超限不代表中间阶段没有丢候选。nconmax/njmax 与 iterations/tolerance 不是同一类预算。
4. VBD rigid_body_particle_contact_buffer_size 涵盖粒子和 full-surface edge/face 记录。overflow 表示可能丢接触；DAT 也无法截断未被报告的接触。
5. 增加迭代只改变已有约束的求解预算，不能补回被过滤、漏检或溢出丢掉的行。""",
        [
            "concept:solver-observables",
            "concept:collisions",
            "recipe:mujoco-native-contact",
            "solver:vbd",
        ],
    ),
    "X05": (
        "Model 数组更新与后端私有缓存更新分开。ModelFlags 的宽泛分组与较窄分组各有自己的 bit；只检查 JOINT_DOF_PROPERTIES 不会自动覆盖所有窄通知。",
        """1. 修改质量/质心/惯量时核对 BODY_INERTIAL_PROPERTIES；修改 armature 核对 JOINT_DOF_INERTIAL_PROPERTIES；增益、阻尼、摩擦和力限核对 JOINT_DOF_FORCE_PROPERTIES。
2. 通过选定 SolverMuJoCo 的 notify_model_changed(flags) 处理缓存与常数更新；直接改 Python 属性或 Model Warp 数组不是刷新后端的证明。
3. 固定源码说明 armature 和参考姿态相关更新可能重算 MuJoCo 常数，应在 reset/域随机化等时段规划，避免把完整重建放进每个子步。
4. 重新分配、拓扑/容量变化或捕获指针失效需要重建/重新捕获；仅数据更新是否可直接复用捕获图，需按具体后端更新函数与设备条件核查。
5. 改动后检查后端实际值、有限状态和相同输入下的响应。这里给出通知依据，不声称执行过该参数干预。""",
        ["topic:lifecycle-observation", "module:newton", "solver:mujoco"],
    ),
    "X06": (
        "公共初态恢复、Control 恢复、solver 历史重置是不同责任。ArticulationView 的 mask 和 SolverBase.reset 的 world_mask 不能直接复用。",
        """1. 核查 view.world_count 与 Model.world_count、articulation/world 映射。view 的 mask 支持 (world_count,) 或 (world_count,count_per_world)。
2. solver world_mask 为 (model.world_count+1,)；前面选择局部 world，最后一项选择 global world=-1。只复位 world 1 时先验证该 world 存在，显式保持其余项及 global 项为 False。
3. 按选中对象恢复 State/Control，并同步需要的双缓冲状态。再用具体 backend 的 solver.reset(state, world_mask=..., flags=...) 清理私有历史；不要把默认 no-op 当作恢复物理初态。
4. StateFlags 的 JOINT_Q/QD、BODY_Q/QD、PARTICLE_Q/QD 与 FORCE 分组表达公共输入变化，不是 ModelFlags。
5. MuJoCo、VBD、Kamino 的 reset override 与缓存不同，核查选定配置；不能因 mask 同形就推断所有后端历史行为等价。global 实体还可能位于数组前后两段。""",
        [
            "recipe:worlds-reset",
            "topic:worlds-batching",
            "concept:worlds",
            "module:selection",
        ],
    ),
    "X07": (
        "SensorIMU 请求 BODY_QDD，SensorContact 请求 CONTACT_F，可合并请求 kinds，但两种传感器的输入时刻与物理定义不同。",
        """1. 固定版本中 Kamino BODY_QDD 是 (body_qd_out-body_qd_in)/dt 的步平均，包括碰撞冲量除以 dt；MuJoCo Warp 使用对应后约束动力学阶段，不能把冲击下两者当同一瞬时采样。
2. SensorIMU.update(state, observables=...) 使用所需的当前位姿和加速度，核对 site 局部参考系、重力与刚体质心/量测点关系；不要只比较数组数字。
3. Kamino 导出的接触点在输入 body frame，wrench 关于输入 COM；SensorContact.update(state_in, contacts, observables=...) 消费相应接触。原位 step 也要保留输入位姿给需要变换的消费者。
4. native MuJoCo CPU 仅提供 QFRC_ACTUATOR，不支持这些 BODY_QDD/CONTACT_F 请求；MuJoCo Warp 的 cpu/cuda 设备与 native CPU 选项是不同维度。
5. 保存 dt、冲击发生的子步与输出采样时刻，才可分析读数差异。此处没有执行跨后端 IMU 实测。""",
        [
            "module:sensors",
            "concept:solver-observables",
            "topic:lifecycle-observation",
            "solver:kamino",
            "solver:mujoco",
        ],
    ),
    "X08": (
        "ModelView 划分所有权，coupler 与子 solver 不能同时重复负责同一接口行。ADMM 的对称接口约束路径不同于代理反馈。",
        """1. 对每个 body/particle/joint/shape 检查所属 Entry；仅当关节端点属于不同 entry 且 joint 本身不归任一子 solver 时，coupler 接管该跨 solver 关节。
2. 当前 ADMM 关节行支持 BALL/FIXED/REVOLUTE，PRISMATIC/DISTANCE/D6 行未支持。不要根据某个子 solver 自己支持关节就推断 coupler 也支持接口行。
3. particle-body attachment 由 ModelBuilder.add_attachment_particle_body 建立。跨 entry 由 coupler 处理；同 entry 留给该 solver，端点无 owner 或该 solver 不支持时应检查 warning。
4. legacy coupling:body_particle_attachment 自定义行仍被 ADMM 消费，但对 VBD 直接求解不可见；迁移时分清数据布局。
5. ContactPair 显式开启 ADMM 私有接触检测，确保子 solver 的接触路径没有再次解同一跨 entry 交互。接触摩擦从模型材料读取，不是 ContactPair 的任意字段。
6. attachment 是物理假设，不作为夹爪接触抓取的默认替代；本知识配方未执行实际耦合任务。""",
        ["concept:coupling", "topic:coupling", "recipe:coupled-rigid-deformable"],
    ),
    "X09": (
        "先选固定版本支持的微分路径。官方能力表仅将 SolverSemiImplicit / SolverFeatherstone 标为 basic 可微，XPBD/VBD 不支持；requires_grad=True 只是分配相关缓冲的前提。",
        """1. 通过 builder.finalize(requires_grad=True) 分配模型，按示例创建需要梯度的 State 与标量 loss。
2. 在 wp.Tape() 范围内记录 forward rollout 和 loss 计算，再调用 tape.backward(loss)。检查所求导的数组是否参与、是否分配 grad，以及是否被非可微流程断开。
3. 多步时保留反向所需的中间状态/数组；不能照搬普通仿真的双缓冲交换后覆盖所有历史。按 diffsim 示例的状态列表与优化循环处理。
4. 梯度非 None 不等于数值正确，还需有限差分等验证；当前条目是源码与示例依据，不宣称本库完成梯度数值检验。
5. 控制器、导入器或外部组件的梯度支持也要分别核查，不能从 Warp 可微直接推导整个应用可微。""",
        [
            "topic:differentiable-simulation",
            "solver:semi-implicit",
            "solver:featherstone",
            "solver:xpbd",
        ],
    ),
    "X10": (
        "ke/kd 的数值与 MuJoCo 实际约束参数要连同接触来源、solref_mode 和 backend 判断。相同字段名不是跨路径等效的保证。",
        """1. 先区分 backend：Newton 1.7.0 中 use_mujoco_cpu=True 的 native CPU 分支直接调用 mj_step，不消费传入的 Newton contacts；即使 use_mujoco_contacts=False 仍使用原生碰撞。MuJoCo Warp 分支才按 use_mujoco_contacts 选择原生检测或 False 时的 Newton 接触导入，后者需要调用方先计算 contacts。Warp 的 cpu/cuda 设备与 native CPU backend 不是同一个开关。
2. 正数 ke/kd 的旧数值映射为 timeconst=2/kd、dampratio=kd/(2*sqrt(ke))。这个 unit-mass 数值映射不是任意有效质量下的物理临界阻尼公式。
3. Newton contacts 的 force-space 修正使用两刚体 translational body_invweight0 的和与 solimp，这不是任意铰接/偏心接触的完整 (J M^-1 J^T)^-1。固定文档明确 native contacts/CPU 不采用该逐接触因子，不能把它们解释为同一物理刚度转换。
4. RAW、MJCF_DEFAULT、Newton force-space 模式与导入属性分别核查。SOLREF_MODE_* 是实现标记，不是公开选择 API，不从 _src 导入常量改变模式。正格式 solref 的 refsafe 使用 max(timeconst,2*dt) 作为活动约束下界，不改写存储值；负数 direct 格式绕过此规则。
5. 记录真正的 solver/model/backend 配置及转换值，再对压入、振动和轨迹做对照。不要从相同 ke 给出严格相同响应的承诺。""",
        ["solver:mujoco", "concept:simulation-tuning", "concept:collisions"],
    ),
    "X11": (
        'dynamics_solver 选择会触发一组依赖默认值。应该在 SolverKamino.Config(dynamics_solver="dvi") 构造时选择后端，并核查解析后的 dynamics、线性求解和稀疏布局，而非只事后改字符串。',
        """1. PADMM 是默认 proximal ADMM 路径，使用其对应的 dense Jacobian/dynamics 与线性系统配置；DVI 有自己的块/稀疏与求解器组合。实际值由 Config 的初始化/校验逻辑解析。
2. PADMM 使用预条件冲量 x/y，但报告 r_p=||P(x-y)||_inf，r_d=||P^-1(eta(x-x_prev)+rho(y-y_prev))||_inf；P 因子将其转到物理约束单位。DVI r_p 为物理冲量的锥投影距离，r_d 为对偶锥速度距离/双边速度违约。两者 r_p 为 N·s 或 N·m·s，r_d 为 m/s 或 rad/s，r_c 为冲量-速度内积的绝对最大值 [J]；同单位不表示同一定义。
3. 官方文档说明两者残差均为绝对最大值，未除以参考范数归一；不能按同名字段直接跨 backend 排优劣或套用同一容差。
4. 切换后端是配置组干预，应保存所有实际 diff、终止状态和物理误差，不写成只改变一个独立参数的 A/B。
5. 首版深入知识中 config.padmm.max_iterations=200 是 PADMM 的声明上限，不是 DVI 的等效预算。本配方没有执行后端性能比较。""",
        [
            "solver:kamino",
            "page:solvers/kamino/parameters.md",
            "page:solvers/kamino/theory.md",
        ],
    ),
    "X12": (
        "rigid_soft_enable_dat 是针对已报告接触的 Divide-and-Truncate 限制，不是任意非凸场景全局无穿透保证。它要求 solver-owned pipeline。",
        """1. 先构造 CollisionPipeline，再把 collision_pipeline= 传给 SolverVBD；step 必须 contacts=None。DAT 的分割平面来自检测时的参考构型。
2. AUTO 下相关 RIGID slot 解析 PRE_POST_INIT，检测在初始化前后；快速运动可核查 ITERATIONS 调度与 collision_frequency。DAT 家族激活时对应 slot 不能为 NONE。同时启用 rigid-soft DAT 与 self-contact DAT 时，两者共享 motion reference：RIGID 与 SOFT_SELF_CONTACT 必须解析为相同调度类型，若使用 ITERATIONS 还须频率相同；应同时设置两个 slot，不能仅提高其中一个的频率。
3. 每侧预算含 0.5 * dat_conservative_bound_relaxation * 最小查询半径，半径由 gap、soft feature radius 与 shape margin 组成；在构造时固定，后改这些字段不会自动刷新预算。该各向同性预算约束模型中每个动态 body/particle 的检测间运动，不只限制接触附近的对象。
4. Kinematic bodies 在 solver 外运动，不被截断。overflow 丢掉的接触不参与限制；非凸几何稠密覆盖也不由此自动保证。
5. 采样/二分可能漏掉样点间穿过再返回的轨迹；额外 interval prefix 路径仍标 experimental，不将其视为成熟无条件保证。
6. 用具体接触记录、运动预算、检测时刻和实际轨迹排查，再决定是否增大预算/检测频率或改善几何；提高迭代不能补回缺失接触。""",
        [
            "solver:vbd",
            "concept:collisions",
            "recipe:solver-owned-collision",
            "pipeline:enable_rigid_soft_full_surface_contact",
        ],
    ),
}


def main():
    tasks_path = ROOT / "planning/p3/tasks.json"
    tasks = json.loads(tasks_path.read_text(encoding="utf-8"))["tasks"]
    freeze = json.loads((tasks_path.parent / "scope-lock.json").read_text())
    if hashlib.sha256(tasks_path.read_bytes()).hexdigest() != freeze["tasks_sha256"]:
        raise ValueError("P3 frozen task pack changed")
    registry = json.loads(
        (ROOT / "knowledge/registry.json").read_text(encoding="utf-8")
    )
    api = {s["public_name"]: s for s in inventory(registry)}
    lock = json.loads((ROOT / "manifests/source-lock.json").read_text(encoding="utf-8"))
    records = []
    relations = []
    needles = {
        "docs/migration.rst": "Joint-target layout",
        "docs/concepts/actuators.rst": "Actuators provide composable",
        "docs/concepts/solver_observables.rst": "Allocation freezes",
        "docs/concepts/coupling.rst": "Cross-solver model joints are owned",
        "docs/solvers/index.rst": "Differentiability",
        "docs/solvers/mujoco.rst": "Contact ``solref`` conversion",
        "docs/solvers/kamino.rst": "residual definitions are backend-specific",
    }
    task_needles = {
        "X04": {
            "newton/_src/solvers/vbd/solver_vbd.py": "rigid_body_particle_contact_buffer_size: Max"
        },
        "X05": {
            "newton/_src/sim/enums.py": "class ModelFlags",
            "newton/_src/solvers/mujoco/solver_mujoco.py": "def notify_model_changed",
        },
        "X06": {
            "newton/_src/core/reset.py": "def normalize_reset_world_mask",
            "newton/_src/solvers/solver.py": "def reset",
            "newton/_src/solvers/mujoco/solver_mujoco.py": "def reset",
        },
        "X07": {
            "docs/concepts/solver_observables.rst": "computes acceleration as the discrete"
        },
        "X09": {
            "newton/examples/diffsim/example_diffsim_ball.py": "self.states = [self.model.state()"
        },
        "X10": {
            "newton/_src/solvers/mujoco/kernels.py": "def convert_solref",
            "docs/solvers/mujoco.rst": "Shape-material contact stiffness and damping",
        },
        "X11": {
            "newton/_src/solvers/kamino/config.py": "class ConstrainedDynamicsConfig",
            "newton/_src/solvers/kamino/solver_kamino.py": "def __post_init__",
        },
        "X12": {
            "newton/_src/solvers/vbd/solver_vbd.py": "rigid_soft_enable_dat: Whether"
        },
    }
    for task in tasks:
        mechanism, steps, related = TEXT[task["id"]]
        refs = []
        for name in task["symbols"]:
            if name not in api:
                raise ValueError("Missing public symbol " + name)
            s = api[name]
            refs.append({"path": s["path"], "line": s["line"]})
        for path in task["source_requirements"]:
            lines = (SRC / path).read_text(encoding="utf-8").splitlines()
            needle = task_needles.get(task["id"], {}).get(path, needles.get(path))
            if not needle and any(r["path"] == path for r in refs):
                continue
            line = next(
                (i + 1 for i, v in enumerate(lines) if needle and v.strip() == needle),
                None,
            )
            if line is None:
                line = next(
                    (i + 1 for i, v in enumerate(lines) if needle and needle in v), 1
                )
            if needle and not any(needle in v for v in lines):
                raise ValueError(
                    "Curated source anchor not found: " + path + " / " + needle
                )
            refs.append({"path": path, "line": line, "role": "behavior_excerpt"})
        # Supplement frozen task sources with the exact branches behind corrected facts.
        extra_refs = {
            "X04": [("newton/_src/sim/collide.py", 142), ("newton/_src/sim/collide.py", 223), ("newton/_src/sim/model.py", 1965), ("newton/_src/geometry/narrow_phase.py", 2225)],
            "X10": [("newton/_src/solvers/mujoco/solver_mujoco.py", 4568)],
            "X12": [("newton/_src/solvers/vbd/solver_vbd.py", 4808)],
        }
        refs.extend({"path": path, "line": line, "role": "behavior_excerpt"} for path, line in extra_refs.get(task["id"], []))
        refs = list({(r["path"], r["line"]): r for r in refs}.values())
        for r in refs:
            r.update(
                commit=COMMIT,
                sha256=lock["files"][r["path"]],
                url=f"https://github.com/newton-physics/newton/blob/{COMMIT}/{r['path']}#L{r['line']}",
            )
        solver = (
            task["applicable_solvers"][0]
            if len(task["applicable_solvers"]) == 1
            else None
        )
        body = (
            "# "
            + task["title"]
            + "\n\n## 机制与输入输出\n\n"
            + mechanism
            + "\n\n## 配置与诊断步骤\n\n"
            + steps
        )
        body += "\n\n## 适用范围与证据\n\nNewton 1.7.0 固定文档、公开 API 与源码说明；runtime_status=not_run。这里的任务验证只验证知识检索与配置推理证据，不是物理任务执行或参数 A/B。设备、后端和捕获限制按所选路径核对。\n"
        body += "\n## 精确 API\n\n" + "\n".join(
            f"- [{s}](#/record/{quote('symbol:' + s, safe='')})"
            for s in task["symbols"]
        )
        body += "\n\n## 相关知识\n\n" + "\n".join(
            f"- [{r}](#/record/{quote(r, safe='')})" for r in related
        )
        body += (
            "\n\n## 固定出处\n\n"
            + "\n".join(f"- [{r['path']}:{r['line']}]({r['url']})" for r in refs)
            + "\n"
        )
        rid = task["record_id"]
        record = {
            "id": rid,
            "family": "recipe",
            "title": task["title"],
            "summary": mechanism[:170],
            "body": body,
            "domain": "workflow",
            "stages": task["stages"],
            "solver": solver,
            "owner_module": "newton.solvers" if solver else "newton",
            "applicable_solvers": task["applicable_solvers"],
            "support_status": "supported",
            "runtime_status": "not_run",
            "source_refs": refs,
            "target_depth": "T",
            "canonical_path": "knowledge/pages/extended/" + rid.split(":")[1] + ".md",
            "task_id": task["id"],
        }
        records.append(record)
        for target in related + ["symbol:" + s for s in task["symbols"]]:
            relations.append(
                {
                    "source": rid,
                    "target": target,
                    "relation": "related_workflow"
                    if not target.startswith("symbol:")
                    else "uses_public_api",
                    "source_refs": refs[:2],
                    "evidence_type": "source_checked",
                    "scope": "P3 task recipe association; no inferred causal or runtime claim",
                }
            )
    (ROOT / "knowledge/extensions.json").write_text(
        json.dumps(
            {
                "version": "1.7.0",
                "commit": COMMIT,
                "task_pack_sha256": freeze["tasks_sha256"],
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
                "extended_tasks": len(tasks),
                "recipes": len(records),
                "relations": len(relations),
            }
        )
    )


if __name__ == "__main__":
    main()
