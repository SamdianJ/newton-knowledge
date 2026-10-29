"""Rebuild MuJoCo/Kamino dossiers from pinned AST + explicitly curated interpretation.

No imports of Newton, downloads, simulation, or edits to the evidence snapshot.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import quote

from solver_mechanism_content import COVERAGE, EXTRA_SOURCE_FILES, concept_sections, mechanism_records
from kamino_experiment_content import experiment_sections, link_mapping_evidence
from kamino_pd_content import pd_experiment_sections
from mujoco_experiment_content import mujoco_experiment_sections

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "sources/newton-v1.7.0"
SHA = "7e75abe28b8d69522bc0b34837aaed2c303dff5a"
MU = "newton/_src/solvers/mujoco/solver_mujoco.py"
KA = "newton/_src/solvers/kamino/solver_kamino.py"
KC = "newton/_src/solvers/kamino/config.py"
MODEL = "newton/_src/sim/model.py"
FILES = [
    MU,
    KA,
    KC,
    MODEL,
    "pyproject.toml",
    "docs/solvers/mujoco.rst",
    "docs/solvers/kamino.rst",
    "docs/concepts/simulation_tuning_mujoco.rst",
    "docs/concepts/simulation_tuning_solvers.rst",
    "newton/_src/solvers/kamino/README.md",
    "newton/_src/solvers/kamino/_src/solver_kamino_impl.py",
    "newton/_src/solvers/kamino/_src/core/conversions.py",
    "newton/_src/solvers/kamino/_src/solvers/padmm/__init__.py",
    "newton/_src/solvers/kamino/_src/solvers/padmm/solver.py",
    "newton/_src/solvers/kamino/_src/solvers/dvi/solver.py",
] + EXTRA_SOURCE_FILES
TEXTS = {p: (SOURCE / p).read_text(encoding="utf-8") for p in FILES}
TREES = {p: ast.parse(t) for p, t in TEXTS.items() if p.endswith(".py")}


def write(path, value):
    if str(path)=='README.md' and (ROOT/path).exists() and '仿真知识平台' in (ROOT/path).read_text(encoding='utf-8-sig').splitlines()[0]:
        return
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def ref(path, needle=None, line=None):
    if line is None:
        line = next(i for i, text in enumerate(TEXTS[path].splitlines(), 1) if needle in text)
    return {
        "repository": "newton-physics/newton",
        "commit": SHA,
        "path": path,
        "line": line,
        "url": f"https://github.com/newton-physics/newton/blob/{SHA}/{path}#L{line}",
    }


def cite(r):
    return f"[{r['path']}:{r['line']}]({r['url']})"


def saved_lab_cases(solver):
    """Read existing archived cases without rerunning or promoting evidence."""
    cases = []
    for path in (ROOT / "experiments/solver_parameter_lab/catalog.json", ROOT / "experiments/kamino_mechanism_lab/catalog.json", ROOT / "experiments/kamino_pd_lab/catalog.json", ROOT / "experiments/mujoco_joint_contact_lab/catalog.json"):
        if path.exists():
            catalog = json.loads(path.read_text(encoding="utf-8"))
            cases.extend(case for case in catalog.get("cases", []) if case.get("solver") == solver)
    return cases


def parameter_experiment_note(parameter, cases):
    matches = [case for case in cases if parameter["id"] in case.get("associations", [])]
    if matches:
        return (
            "已有归档实测关联（机制/配置组对照不等于该字段的单因素干预）：" + "、".join(f"`{case['id']}`" for case in matches)
            + "；见 " + "、".join(sorted({f"[实验与边界](../../{case.get('artifact_root', 'experiments/solver_parameter_lab/')}README.md)" for case in matches})) + "。"
            "结论仅限保存的场景、后端与参数组，不代表全范围验证。"
        )
    return "当前实验目录未关联该字段的直接 A/B；本条为源码解释，不宣称参数效果已实测。"


def classes(path):
    return [n for n in ast.walk(TREES[path]) if isinstance(n, ast.ClassDef)]


def base(solver, name, owner, annotation, default, definition, documentation, layer):
    declared = ast.unparse(default) if default is not None else None
    return {
        "id": f"newton:1.7.0:{solver}:{name}",
        "solver": solver,
        "name": name,
        "owner": owner,
        "type": ast.unparse(annotation) if annotation else "unspecified",
        "required": default is None,
        "declared_default_expression": declared,
        "resolved_default": declared,
        "definition": definition,
        "documentation": documentation,
        "summary_zh": documentation.split("\n")[0] if documentation else f"{owner} 的 {name} 输入。",
        "units": "以源码字段说明为准",
        "category": layer,
        "layer": layer,
        "status": "source_checked",
        "lifecycle": "构造/配置时读取；运行期变更需按对应 API 更新，已捕获图可能需要重建。",
        "experiments": [],
    }


def constructor(solver, path, clsname):
    cls = next(c for c in classes(path) if c.name == clsname)
    init = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__")
    docs = ast.get_docstring(init) or ""
    pieces = re.split(r"(?m)^    (\w+):\s*", docs.partition("Args:")[2])
    descriptions = {pieces[i]: pieces[i + 1].strip() for i in range(1, len(pieces) - 1, 2)}
    args = init.args.args
    positional = [None] * (len(args) - len(init.args.defaults)) + list(init.args.defaults)
    entries = []
    for arg, default in list(zip(args, positional, strict=True)) + list(
        zip(init.args.kwonlyargs, init.args.kw_defaults, strict=True)
    ):
        if arg.arg == "self":
            continue
        p = base(
            solver,
            arg.arg,
            f"newton.solvers.{clsname}.__init__",
            arg.annotation,
            default,
            ref(path, line=arg.lineno),
            descriptions.get(arg.arg, ""),
            "solver_constructor",
        )
        entries.append(p)
    return entries


def config_fields(path, classname, prefix):
    cls = next(c for c in classes(path) if c.name == classname)
    records = []
    for i, node in enumerate(cls.body):
        if not isinstance(node, ast.AnnAssign):
            continue
        following = cls.body[i + 1] if i + 1 < len(cls.body) else None
        doc = (
            following.value.value.strip()
            if isinstance(following, ast.Expr)
            and isinstance(following.value, ast.Constant)
            and isinstance(following.value.value, str)
            else ""
        )
        name = prefix + "." + ast.unparse(node.target)
        p = base(
            "kamino",
            name,
            "SolverKamino." + classname if classname in ("Config", "ResetConfig") else "kamino.config." + classname,
            node.annotation,
            node.value,
            ref(path, line=node.lineno),
            doc,
            "reset_configuration" if classname == "ResetConfig" else "solver_configuration",
        )
        p["summary_zh"] = f"{prefix} 配置：" + (doc.split("\n")[0] if doc else ast.unparse(node.target))
        records.append(p)
    return records


MU_SUMMARY = {
    "model": "要转换为 MuJoCo 模型的 Newton Model。",
    "separate_worlds": "是否拆分 Newton worlds；None 时实际分支为 not use_mujoco_cpu 且 world_count > 1。",
    "njmax": "每 world 的约束容量；自动估算或检查初始约束并告警扩容，不是迭代预算。",
    "njmax_nnz": "稀疏约束 Jacobian 的非零元素容量。",
    "nconmax": "每 world 接触点容量；不足与物理解算未收敛是不同问题。",
    "iterations": "约束优化最大迭代预算；None 继续走模型属性/后端默认解析。",
    "ls_iterations": "每轮优化的线搜索预算。",
    "ccd_iterations": "碰撞检测 CCD 迭代预算。",
    "sdf_iterations": "SDF 碰撞搜索迭代预算。",
    "sdf_initpoints": "SDF 搜索初始点数量。",
    "solver": "选择 CG/Newton 约束求解方法。",
    "integrator": "时间积分方法；Newton 注册默认 implicitfast，与原生 MuJoCo 默认不同。",
    "cone": "摩擦锥近似：pyramidal 或 elliptic。",
    "jacobian": "约束 Jacobian 的 dense/sparse/auto 表示。",
    "impratio": "切向与法向约束阻抗的比值，不能当作摩擦系数。",
    "tolerance": "约束优化提前终止容差。",
    "ls_tolerance": "线搜索提前终止容差。",
    "ccd_tolerance": "CCD 收敛容差。",
    "density": "流体介质密度，影响阻力与升力。",
    "viscosity": "介质黏度。",
    "wind": "介质风速向量。",
    "magnetic": "磁场向量。",
    "use_mujoco_cpu": "切换 MuJoCo-C native CPU 后端；此分支始终由原生 MuJoCo 生成接触，不消费传入的 Newton contacts。MuJoCo Warp 的 CPU 设备与本选项不是一回事。",
    "enable_multiccd": "多点碰撞接触生成；效果受几何和 margin 路径限制。",
    "enable_sleeping": "GPU sleeping 优化，受 solver、积分器和碰撞路径组合约束。",
    "nvmax": "sleeping 路径的活跃自由度容量。",
    "sleep_tolerance": "休眠速度阈值。",
    "disable_contacts": "禁用接触计算；用于诊断时会改变物理场景。",
    "disable_sensors": "禁用常规传感器计算；部分请求的观测量仍按源码路径更新。",
    "update_data_interval": "Newton state 向 MuJoCo data 同步的步间隔；0 关闭 step 内的 state 同步。control 和外力仍每步提交，reset 的显式状态同步另行处理。",
    "save_to_mjcf": "导出编译前模型以排查转换；这是 solver 参数，MCP 只读工具不会执行导出。",
    "use_mujoco_contacts": "仅 MuJoCo Warp 分支用此开关选择内建检测或导入 Newton contacts；use_mujoco_cpu=True 的 native CPU 分支即使设 False 也不消费传入 contacts。响应仍由 MuJoCo 约束体系求解。",
    "include_sites": "是否导出 SITE 参考点；SITE 不参与碰撞。",
    "skip_visual_only_geoms": "是否从导出模型排除仅可视几何。",
    "deterministic": "MuJoCo Warp 核确定性设置；None 继承 Warp 配置。",
}
KA_SUMMARY = {
    "config.dynamics_solver": "PADMM/DVI 后端选择；应在创建 Config 时指定，以一致解析依赖默认值。",
    "config.sparse_jacobian": "None 时 DVI=True、PADMM=False；属于表示/后端组合设置。",
    "config.sparse_dynamics": "启用稀疏动力学；要求 sparse_jacobian=True。",
    "config.dynamics.preconditioning": "对偶预条件；DVI 必须为 False，直接 dataclass 默认与 Config 组合解析不同。",
    "config.dynamics.linear_solver_type": "直接子配置默认 LLTB；默认 DVI 组合改为 LLTBRCM，稀疏 DVI 改为 CR。",
    "config.padmm.rho_0": "PADMM 初始增广罚参数；属于数值参数，不是接触材料刚度。",
    "config.padmm.eta": "近端正则化强度；影响子问题数值性质。",
    "config.padmm.max_iterations": "PADMM 最大迭代预算；同时核对三个残差和 converged。",
    "config.padmm.penalty_update_method": "罚参数更新策略；非 fixed 需要 sparse_dynamics=True。",
    "config.padmm.use_graph_conditionals": "CUDA 条件图迭代控制；不适用的平台应选择固定上限循环路径。",
    "config.padmm.warmstart_scale": "缓存约束反力的 warmstart 缩放，不等同于材料耗散。",
    "config.constraints.alpha": "双边关节 Baumgarte 稳定化比例，范围 [0,1]。",
    "config.constraints.beta": "单边关节限位 Baumgarte 稳定化比例，范围 [0,1]。",
    "config.constraints.gamma": "单边接触 Baumgarte 稳定化比例，范围 [0,1]。",
    "config.constraints.delta": "接触穿透容许 margin，非负，不能补偿碰撞漏检。",
    "config.dvi.omega": "投影 Gauss-Seidel 松弛比例，范围 (0,2]。",
    "config.dvi.max_alternating_iterations": "DVI 外层双边直接解与单边投影交替预算。",
    "config.dvi.inequality_sweeps_per_iteration": "每个 DVI 外层迭代中的单边投影扫描次数。",
    "config.use_collision_detector": "是否启用 Kamino 内部碰撞管线；默认 False 时由调用方提供 Newton contacts。",
    "config.integrator": "Euler/Moreau；Moreau 要求内部碰撞检测，不应单独切换。",
    "config.collect_solver_info": "收集额外诊断，有开销；status 在 False 时仍然存在。",
}


def make_models(solver):
    specs = [
        ("body_mass", "kg", "刚体质量；先从参考尺度与密度确定，避免用质量补偿错误接触。"),
        ("body_inertia", "kg·m²", "刚体惯量张量；影响转动与约束条件数。"),
        ("joint_armature", "依自由度而定", "关节附加惯量；需区分转动与平移自由度。"),
        ("joint_target_ke", "依自由度而定", "关节 PD 比例增益；不同 solver 的执行/隐式路径需分别核对。"),
        ("joint_target_kd", "依自由度而定", "关节 PD 导数增益。"),
        ("joint_effort_limit", "N 或 N·m", "执行器力/力矩上限；与驱动方式共同作用。"),
        ("joint_limit_lower", "m 或 rad", "关节下限及参考坐标约定。"),
        ("joint_limit_upper", "m 或 rad", "关节上限及参考坐标约定。"),
        ("shape_material_mu", "无量纲", "形状表面摩擦；需同时检查材料混合和接触维度。"),
    ]
    if solver == "mujoco":
        specs += [
            ("joint_damping", "N·s/m 或 N·m·s/rad", "关节被动黏性阻尼，导出为 MuJoCo dof_damping；区别于 PD 目标速度误差项 joint_target_kd。"),
            ("shape_material_mu_torsional", "m", "扭转摩擦系数，控制接触法线方向的摩擦力矩尺度；需 condim≥4 才启用。单位为长度，不与无量纲滑动摩擦系数混用。"),
            ("shape_material_mu_rolling", "m", "滚动摩擦系数，控制切向旋转的摩擦力矩尺度；需 condim=6 才启用。此次扭转实验不构成滚动摩擦验证。"),
            ("shape_margin", "m", "形状接触裕量；需核对 native 后端实际 geom_margin 与 CCD 标志，不能仅根据请求值推断激活距离。"),
            ("shape_gap", "m", "形状接触候选间隙；应区分候选生成与活动约束，语义以固定 MuJoCo 版本及实际 geom_gap 为准。"),
            (
                "shape_material_ke",
                "按转换模式解释",
                "接触刚度输入会转换为 MuJoCo solref；MuJoCo Warp 的 Newton-contacts force-space 路径有额外条件。native CPU 不消费外部 Newton contacts。",
            ),
            ("shape_material_kd", "按转换模式解释", "接触阻尼输入，不能把 VBD penalty 单位/效果直接搬到 MuJoCo。"),
        ]
    else:
        specs += [
            (
                "shape_material_restitution",
                "无量纲",
                "碰撞恢复系数；与 material manager 的混合模式共同决定成对材料响应。",
            )
        ]
    result = []
    for field, units, description in specs:
        if solver == "kamino":
            if field in ("joint_armature", "joint_target_ke", "joint_target_kd", "joint_effort_limit"):
                description += (
                    " Kamino 关节动力学/implicit PD 当前限于 revolute、prismatic、gimbal；"
                    "按 DoF 路由驱动，但 FK 仍按整 joint 分被动/驱动。保持约束分配时可通知数值变化；"
                    "跨零改变动态分配、增删有界 PD 或改变驱动分区必须重建。"
                )
            elif field in ("joint_limit_lower", "joint_limit_upper"):
                description += " 已有有限限位可通知数值更新；改变有限/无限状态导致约束结构变化，必须重建。"
            elif field in ("shape_material_mu", "shape_material_restitution"):
                description += (
                    " 内部碰撞器经 SHAPE_PROPERTIES 更新固定材质表；共享 material 的 shapes 若分歧为不同材质值，"
                    "必须重建以拆分分组。外部 Newton contacts 直接读 shape 材质，不使用内部材质表。"
                )
        needle = f"self.{field}:"
        if needle not in TEXTS[MODEL]:
            needle = field
        consumer_path = MU if solver == "mujoco" else "newton/_src/solvers/kamino/_src/core/conversions.py"
        consumer = (
            ref(consumer_path, "model." + field)
            if "model." + field in TEXTS[consumer_path]
            else ref(MU if solver == "mujoco" else KA, "class Solver")
        )
        result.append(
            {
                "id": f"model:{solver}:{field}",
                "solver": solver,
                "field": field,
                "units": units,
                "description_zh": description,
                "model_definition": ref(MODEL, needle),
                "consumer": consumer,
                "consumer_scope": "First static source occurrence, not complete data-flow analysis.",
                "default_policy": "由实际 ModelBuilder / 导入模型决定，未声明跨场景通用默认值。",
                "experiments": [],
            }
        )
    if solver == "mujoco":
        for name, description in [
            ("solref", "接触参考响应参数；正值格式与直接负值格式含义不同。"),
            ("geom_solimp", "约束阻抗曲线；与 solref 共同定义接触软化。"),
            ("condim", "接触维度，决定是否含切向/扭转/滚动摩擦。"),
            ("solref_mode", "ke/kd 转换模式；逐接触 force-space 修正属于 MuJoCo Warp 的 Newton-contacts 路径。native CPU 不消费外部 contacts，原生检测也不采用该逐接触修正。"),
        ]:
            definition = ref(MU, f'name="{name}"')
            result.append(
                {
                    "id": f"model:mujoco:mujoco.{name}",
                    "solver": solver,
                    "field": "mujoco." + name,
                    "units": "见字段定义",
                    "description_zh": description,
                    "model_definition": definition,
                    "consumer": definition,
                    "default_policy": "读取已注册 mujoco 自定义属性及实际模型值。",
                    "experiments": [],
                }
            )
    return result


CONTENT = {
    "mujoco": {
        "name": "MuJoCo",
        "theory": r"""## 广义坐标与约束响应

Newton 的 SolverMuJoCo 把 Model 转为 MuJoCo 模型，计算广义坐标系统中的动力学，再将状态同步回来。机器人树结构主要在关节坐标中表达，额外闭环通过受支持的 equality 约束表达。

$$M(q)\dot v+c(q,v)=\tau+J(q)^T f$$

MuJoCo 的接触响应是带软约束的优化模型。`solver` 决定数值优化方法，`iterations/tolerance` 决定求解预算，`solref/solimp` 决定约束响应模型，`dt/integrator` 决定时间离散。增加迭代无法修复碰撞漏检、错误模型转换或错误材料参数。

## 接触、材料与后端

`use_mujoco_contacts` 只在 MuJoCo Warp 分支选择接触生成来源，不把约束响应换成 VBD。`use_mujoco_cpu=True` 选择 MuJoCo-C native CPU；它与运行在 CPU 设备上的 MuJoCo Warp 不同。

| 后端 | use_mujoco_contacts | v1.7.0 实际接触路径 |
|---|---|---|
| native CPU（use_mujoco_cpu=True） | True 或 False | 始终由原生 MuJoCo 检测并响应；传入的 Newton contacts 不被消费 |
| MuJoCo Warp（use_mujoco_cpu=False） | True | MuJoCo Warp 内建检测与响应 |
| MuJoCo Warp（use_mujoco_cpu=False） | False | 调用方先检测并传入 Newton contacts，包装层转换后交后端响应 |

这是固定 `SolverMuJoCo.step` 的分支行为：CPU 直接调用 mj_step，只有 Warp 分支调用 `_convert_contacts_to_mjwarp`。`shape_material_ke/kd` 经转换得到 MuJoCo 参数，其作用不应沿用 VBD 的直接 penalty 解释；逐接触 force-space 修正还需核对接触来源和转换模式。

## 对重建 agent 的意义

优先核对机器人关节、质量/惯量、几何导出、接触生成、参考坐标与控制同步；随后探索接触软化和时间步，最后调整优化预算。以几何穿透、滑移、关节误差和运行开销分别评价。
""",
        "implementation": """## 构造到 step 的数据流

1. 注册 `mujoco.*` 自定义属性；构造参数覆盖模型属性，未覆盖部分继续走注册默认/后端默认。
2. 把 Newton bodies/joints/shapes/equalities 转成 MuJoCo spec，编译模型，创建 CPU 或 Warp 数据与索引映射。
3. 每次 step 先提交 control 和外力；仅 Newton state → 后端 data 的同步受 update_data_interval 门控。interval=0 也会接受新的控制输入。
4. native CPU 始终用原生碰撞，不消费传入的 Newton contacts；MuJoCo Warp 才按 use_mujoco_contacts 选择内建检测或外部 contacts 转换，然后执行后端步进。
5. 写回 Newton 输出状态及已请求的观测量；模型属性变更需走 `notify_model_changed` 支持的路径。

## 需要特别检查的转换边界

DISTANCE/ROD 不能视为已受支持的原生约束。MuJoCo 碰撞 mesh 使用凸几何；非凸任务应检查编译后实际模型。Newton 的标量关节坐标相对 authored pose，MuJoCo qpos 还可能含 `ref`；导入、范围与 position control 的偏移要一致。`update_data_interval=0` 会改变输入同步语义，不能仅当作性能开关。

## 默认值冲突

`separate_worlds` 的 docstring 简写为 `not use_mujoco_cpu`，实际构造分支还要求 `model.world_count > 1`，本库以执行分支为准。`integrator=None` 也不能解释为原生 MuJoCo Euler；Newton 注册默认值是 implicitfast。
""",
        "papers": """## 两篇方法背景

- **Todorov, Erez, Tassa (2012)**：解释面向控制的广义坐标引擎结构，包含模型编译、动力学与约束响应。对本任务的用途是定位模型层与求解层；其历史实现不是当前 Warp 后端的支持列表。
- **Todorov (2014)**：解释软化约束、凸接触响应与可解析逆动力学。对本任务的用途是理解接触软化与优化收敛的区别；本轮未复现论文性能结果。

## 阅读与复现边界

输入是多刚体模型、状态、驱动与接触；输出是约束反力与推进后的状态。论文实验用于论证其方法，Newton 1.7.0 的包装、材料转换和 CPU/GPU 路径需另查源码。图示建议：阅读论文的约束求解/管线图，并绘制 Model → MuJoCo spec → backend → State 的本地解释图。
""",
        "versions": """## 固定版本与依赖

事实基线是 Newton 1.7.0；其 `pyproject.toml` 对 `mujoco` 和 `mujoco-warp` 使用 `~=3.15.0`。这不是本机已经安装这两个包的声明。MCP 读取知识无需安装物理后端。

## 支持边界

native CPU 与 MuJoCo Warp 可用的 solver/integrator/contacts/sleeping 组合并不完全相同。sleeping 要求 GPU、Newton 优化方法、MuJoCo contacts 与非 RK4 积分。native CPU 不消费外部 Newton contacts，use_mujoco_contacts=False 不能改变这一点。逐接触 force-space 增益修正属于 MuJoCo Warp 的 Newton-contacts 路径；native CPU 或内建检测路径不使用该逐接触因子。

## 实验状态

静态入库阶段未运行 MuJoCo A/B；后续 P4 已增加两组 native CPU 参数实验，见 [多 solver 参数实验](../../experiments/solver_parameter_lab/README.md)。VBD 的 17 组实验不构成 MuJoCo 验证。未知后端能力及新版本行为保持未知。
""",
        "claims": [
            (
                "defaults",
                "构造值优先于模型 mujoco 自定义属性，再到注册/后端默认；None 不等于固定数值默认。",
                ["iterations", "integrator", "solver"],
                MU,
                "Solver options",
            ),
            (
                "worlds",
                "separate_worlds=None 时，实际分支为 not use_mujoco_cpu and model.world_count > 1。",
                ["separate_worlds", "use_mujoco_cpu"],
                MU,
                "separate_worlds = not",
            ),
            (
                "integration",
                "Newton 注册的默认积分器是 implicitfast，不应套用原生 MuJoCo 默认 Euler。",
                ["integrator"],
                MU,
                "default=3,  # Newton default",
            ),
            (
                "contact_source",
                "外部 Newton contacts 只由 MuJoCo Warp 的 use_mujoco_contacts=False 分支转换并消费；native CPU 不消费传入 contacts，仍使用原生检测。约束响应均由 MuJoCo 负责。",
                ["use_mujoco_contacts", "use_mujoco_cpu"],
                MU,
                "if not self.mjw_model.opt.run_collision_detection:",
            ),
            (
                "capacity",
                "nconmax/njmax 控制容量而非数值收敛预算，初始化不足可能告警扩容。",
                ["nconmax", "njmax", "iterations"],
                MU,
                "Maximum number of constraints per world",
            ),
            (
                "sleeping",
                "sleeping 的有效组合受后端、优化方法、积分器与接触来源限制。",
                ["enable_sleeping", "use_mujoco_cpu", "solver", "integrator"],
                MU,
                "enable_sleeping=True requires solver='newton'",
            ),
        ],
        "diagnostics": [
            (
                "穿透或接触响应偏软",
                [
                    "确认编译后的几何、接触记录和碰撞来源。",
                    "冻结质量/尺度与 dt，比较 solref/solimp 或相应 ke/kd 转换模式。",
                    "再扫 iterations/tolerance，分别量测穿透和收敛。",
                ],
                "更高迭代不能修复几何漏检。",
                ["iterations", "use_mujoco_contacts"],
            ),
            (
                "抓持缓慢滑落",
                [
                    "确认 condim、mu、cone 与 impratio。",
                    "冻结驱动目标，记录切向位移和法向力。",
                    "逐组比较摩擦模型和接触软化。",
                ],
                "impratio 不是摩擦系数。",
                ["impratio", "cone"],
            ),
            (
                "控制目标改变但状态没有跟随",
                [
                    "检查控制端口、关节切片与驱动映射；control 和外力每步提交，不受 update_data_interval 降采样。",
                    "核对 joint ref、关节坐标与 actuator target。",
                    "另行检查 state 的 update_data_interval 同步；先用逐步 state 同步和固定控制输入建立基线。",
                ],
                "先排查同步和参考坐标，再调整增益。",
                ["update_data_interval"],
            ),
            (
                "多接触场景容量或编译问题",
                [
                    "检查 nconmax/njmax/njmax_nnz 告警与初始接触数。",
                    "确认 world 拆分与 CPU/GPU 路径。",
                    "容量与优化预算分别扫描。",
                ],
                "容量设置不能当作材料参数。",
                ["nconmax", "njmax", "separate_worlds"],
            ),
        ],
    },
    "kamino": {
        "name": "Kamino",
        "theory": r"""## 最大坐标与闭环机械系统

Kamino 使用刚体最大坐标表达机械系统，关节、闭环、限位和接触通过约束耦合。先构造受约束动力学问题并求约束冲量，再积分刚体状态；面向刚体机械装配，不能当作 VBD 软体求解器。

以约束 Jacobian J 和质量矩阵 M 表示，对偶系统包含 Delassus 算子：

$$W=JM^{-1}J^T$$

该表达是阅读管线的概念索引，不替代源码中稳定化、预条件、摩擦修正和离散项。

## PADMM 与 DVI

默认 PADMM 通过近端 ADMM 将全局耦合子问题与约束锥投影分开迭代，结合 warmstart、正则化、可选加速与罚参数策略。`rho_0/eta` 是数值参数，不是物理材料刚度。

DVI 是显式选择的另一后端：交替处理双边约束直接解与单边约束投影；其 outer iterations 与 inequality sweeps 是不同预算。DVI 不支持 dual preconditioning。后端切换应在 `Config(dynamics_solver="dvi")` 构造时进行，以解析依赖默认值。

## 残差与物理响应

PADMM 与 DVI 都提供 converged、iterations、r_p/r_d/r_c，但残差定义不同。不要直接比较两个后端同名数值而不核对单位和定义。Baumgarte alpha/beta/gamma 与 delta 控制位置误差修正/穿透容许，不能补偿碰撞漏检。
""",
        "implementation": """## 构造与默认解析

公开入口为 `SolverKamino(model, config=None)`。未提供 config 时从 Model 的 Kamino 自定义属性构造。Config 的 `__post_init__` 建立启用的子配置并校验组合。

- 默认 PADMM：sparse_jacobian=False、sparse_dynamics=False；dynamics 子配置采用其默认 LLTB 和 preconditioning=True。
- DVI、非稀疏动力学：sparse_jacobian 默认 True；Config 自动建立 preconditioning=False、linear_solver_type=LLTBRCM 的 dynamics 子配置。
- DVI、稀疏动力学：同样禁用 preconditioning，动力学线性求解改为 CR，并提供 maxiter=9 的依赖默认 kwargs。

直接实例化 `ConstrainedDynamicsConfig()` 的默认值与嵌入特定后端 Config 后的值不同。不能在 Config 创建完成后只改 dynamics_solver 就假设所有默认值同步变化。

## step 管线

Newton 数据转换 → 初始状态/FK（按配置）→ 接触与限位 → Jacobian / dynamics / dual problem → PADMM 或 DVI → 时间积分 → Newton 输出。默认 `use_collision_detector=False`；调用方需要按接口提供 contacts。Moreau 需要内部碰撞检测路径。

## 诊断接口

`solver.status` 持续维护每 world 的终止记录，不要求 collect_solver_info=True；额外统计和 solution metrics 会增加开销。读取设备数据到 host 会同步。
""",
        "papers": """## 两篇直接引用的方法文献

- **Tsounis, Grandia, Bächer (2025)**：针对闭环机械系统、硬接触和限位，整理最大坐标对偶动力学与多类数值求解方法，并提供基准。重点阅读 V 节构建对偶问题、VI-F ADMM、VII–VIII 基准与实验；论文中的性能结论不能自动套到当前机器。
- **Carpentier, Le Lidec, Montaut (2024)**：结合近端方法与 ADMM 处理刚性/顺应接触，研究残差与罚参数调整。重点阅读 III-B 至 III-F；Kamino 源码在此基础上加入自身预条件、加速、warmstart 和后端约束。

## 从论文到本地重建

输入为刚体状态、质量/惯量、关节与接触约束；输出为约束冲量及推进状态。应同时量测闭环误差、穿透、摩擦行为和残差，再做速度/精度比较。本轮没有复现论文基准。建议读论文的求解算法和性能分布图，另绘制双边/单边约束进入对偶问题的解释图。
""",
        "versions": """## 正式版本中的实验性组件

Newton 1.7.0 的 Kamino 文档仍标为 BETA 1 / experimental，不能用当前日期推断它已经变为稳定版本。其 API、行为和支持范围按固定快照解释。

## 配置组合限制

`sparse_dynamics=True` 要求 sparse_jacobian=True；DVI 要求 dynamics.preconditioning=False；PADMM 的自适应罚参数更新要求 sparse_dynamics=True；Moreau 要求内部碰撞检测。这些是组合约束，不是独立调参旋钮。

## 状态与执行边界

Kamino 面向 constrained rigid systems。FK 对每关节 passive/actuated 的划分与动力学逐 DoF 驱动并非同一能力边界。body_qdd 是离散步平均加速度，冲击时可表现为冲量/dt，不是连续中点加速度。

## 实验状态

静态入库阶段的参数说明来自源码与论文，诊断记录仍为 proposed。P4 已完成两组 PADMM / CPU 参数 A/B，并关闭 graph conditionals，见 [实验协议与复现](../../experiments/solver_parameter_lab/README.md)。不据此声称其他 CPU/GPU 组合已验证。
""",
        "claims": [
            (
                "backend_defaults",
                "Config 构造时按 PADMM/DVI 和 sparsity 解析 Jacobian、预条件与线性求解器默认值。",
                [
                    "config.dynamics_solver",
                    "config.sparse_jacobian",
                    "config.dynamics.preconditioning",
                    "config.dynamics.linear_solver_type",
                ],
                KA,
                "def __post_init__",
            ),
            (
                "padmm_controls",
                "PADMM 的 rho_0/eta、三种残差容差与最大迭代共同控制数值求解。",
                [
                    "config.padmm.rho_0",
                    "config.padmm.eta",
                    "config.padmm.max_iterations",
                    "config.padmm.primal_tolerance",
                    "config.padmm.dual_tolerance",
                    "config.padmm.compl_tolerance",
                ],
                KC,
                "class PADMMSolverConfig",
            ),
            (
                "dvi_controls",
                "DVI 外层交替迭代与单边投影 sweeps 是两层预算，不等同于 PADMM iterations。",
                [
                    "config.dvi.max_alternating_iterations",
                    "config.dvi.inequality_sweeps_per_iteration",
                    "config.dvi.omega",
                ],
                KC,
                "class DVISolverConfig",
            ),
            (
                "stabilization",
                "alpha/beta/gamma 分别控制双边关节、单边限位、单边接触稳定化。",
                [
                    "config.constraints.alpha",
                    "config.constraints.beta",
                    "config.constraints.gamma",
                    "config.constraints.delta",
                ],
                KC,
                "class ConstraintStabilizationConfig",
            ),
            (
                "diagnostics",
                "status 总是维护；collect_solver_info 控制额外统计而非 status 是否存在。",
                ["config.collect_solver_info", "config.compute_solution_metrics"],
                "docs/solvers/kamino.rst",
                "Terminal status is always maintained",
            ),
            (
                "restrictions",
                "DVI 预条件、PADMM 自适应罚参数与稀疏设置受显式校验约束。",
                ["config.dynamics.preconditioning", "config.padmm.penalty_update_method", "config.sparse_dynamics"],
                KA,
                "Adaptive PADMM penalty updates require",
            ),
        ],
        "diagnostics": [
            (
                "闭环漂移或关节约束不一致",
                [
                    "先校验几何、关节拓扑和初始姿态。",
                    "检查 FK 是否启用及其收敛。",
                    "冻结 dt，扫描约束稳定化与 solver 预算，记录闭环误差及三类残差。",
                ],
                "不能仅用更强稳定化掩盖错误关节模型。",
                ["config.constraints.alpha", "config.fk.tolerance"],
            ),
            (
                "PADMM 未收敛或反复达到上限",
                [
                    "读取 status 的 converged/iterations/r_p/r_d/r_c。",
                    "冻结尺度和模型，比较 max_iterations 与各容差。",
                    "再探索 eta/rho_0、warmstart 和合法的罚参数策略。",
                ],
                "残差阈值不是所有任务通用的物理精度保证。",
                ["config.padmm.max_iterations", "config.padmm.rho_0"],
            ),
            (
                "DVI 多接触误差增大",
                [
                    "核对 preconditioning=False 和后端默认组合。",
                    "分别扫描外层迭代与 inequality sweeps。",
                    "在相同接触/步长/模型下与 PADMM 比较。",
                ],
                "后端同名残差定义不同，不可直接以单个数字排名。",
                ["config.dvi.max_alternating_iterations", "config.dvi.inequality_sweeps_per_iteration"],
            ),
            (
                "接触漏检或穿透",
                [
                    "确认使用内部 collision detector 还是外部 contacts。",
                    "检查容量、gap 与几何。",
                    "最后扫描 gamma/delta 与 dt。",
                ],
                "delta 和稳定化不能生成缺失接触。",
                ["config.use_collision_detector", "config.constraints.gamma"],
            ),
            (
                "改后端或积分器后配置报错",
                [
                    "从新的 Config(dynamics_solver=...) 重建。",
                    "核对 sparse_dynamics / sparse_jacobian / preconditioning。",
                    "Moreau 同时启用内部碰撞；按异常定位组合约束。",
                ],
                "不要在完成默认解析后只改一个字段。",
                ["config.dynamics_solver", "config.integrator"],
            ),
        ],
    },
}


def build(solver, papers):
    data = dict(CONTENT[solver])
    concepts = concept_sections(ref, cite)[solver]
    data["implementation"] += "\n" + concepts
    data["versions"] += "\n" + COVERAGE[solver]
    saved_cases = saved_lab_cases(solver)
    experiment_brief, experiment_document = experiment_sections(saved_cases) if solver == "kamino" else ("", "")
    pd_brief, pd_document = pd_experiment_sections(saved_cases) if solver == "kamino" else ("", "")
    mujoco_brief, mujoco_document = mujoco_experiment_sections(saved_cases) if solver == "mujoco" else ("", "")
    if experiment_brief:
        data["implementation"] += experiment_brief
        data["versions"] += experiment_brief
    if pd_brief:
        data["implementation"] += pd_brief
        data["versions"] += pd_brief
        experiment_document += pd_brief
    if mujoco_brief:
        data["implementation"] += mujoco_brief
        data["versions"] += mujoco_brief
        experiment_document = mujoco_document
    params = constructor(
        solver, MU if solver == "mujoco" else KA, "SolverMuJoCo" if solver == "mujoco" else "SolverKamino"
    )
    if solver == "kamino":
        params += config_fields(KA, "Config", "config") + config_fields(KA, "ResetConfig", "reset")
        for cls, prefix in [
            ("CollisionDetectorConfig", "collision_detector"),
            ("ConstraintStabilizationConfig", "constraints"),
            ("ConstrainedDynamicsConfig", "dynamics"),
            ("PADMMSolverConfig", "padmm"),
            ("DVISolverConfig", "dvi"),
            ("ForwardKinematicsSolverConfig", "fk"),
            ("MaterialManagerConfig", "materials"),
        ]:
            params += config_fields(KC, cls, "config." + prefix)
    for p in params:
        if solver == "mujoco":
            p["summary_zh"] = MU_SUMMARY.get(p["name"], p["summary_zh"])
            if p["name"] in ("update_data_interval", "use_mujoco_contacts", "use_mujoco_cpu"):
                p["source_refs"] = [ref(MU, "def step(")]
                p["implementation_note"] = "原始 docstring 保留作出处；执行语义以 summary_zh 和 step 分支核对为准。"
            if p["declared_default_expression"] == "None":
                p["resolved_default"] = "条件解析；见 default_policy 与固定源码"
                p["default_policy"] = (
                    "优先显式构造值，其次模型 mujoco 属性，最后注册/后端默认；非 option 设置按构造分支解析。"
                )
        else:
            p["summary_zh"] = KA_SUMMARY.get(p["name"], p["summary_zh"])
            p["default_policy"] = (
                "声明默认来自所属 dataclass；完整 Config.__post_init__ / from_model 可覆盖或补全子配置。"
            )
            if p["declared_default_expression"] == "None":
                p["resolved_default"] = "条件解析；由 Config.__post_init__ / from_model 补全，见默认策略。"
            if p["name"] == "config.sparse_jacobian":
                p["resolved_default"] = "PADMM=False；DVI=True（未显式指定时）"
            if p["name"].startswith("config.dynamics."):
                p["default_policy"] += (
                    " PADMM 默认 LLTB/预条件 True；DVI dense-dynamics 默认 LLTBRCM/False；DVI sparse-dynamics 默认 CR/False。"
                )
            if p["name"] == "config.dynamics.preconditioning":
                p["resolved_default"] = "PADMM=True；DVI=False（自动创建 dynamics 子配置时）"
                p["conditional_defaults"] = {"standalone_subconfig": True, "padmm": True, "dvi": False}
            elif p["name"] == "config.dynamics.linear_solver_type":
                p["resolved_default"] = "独立子配置/PADMM=LLTB；DVI dense-dynamics=LLTBRCM；DVI sparse-dynamics=CR"
                p["conditional_defaults"] = {
                    "standalone_subconfig": "LLTB",
                    "padmm": "LLTB",
                    "dvi_dense_dynamics": "LLTBRCM",
                    "dvi_sparse_dynamics": "CR",
                }
    byname = {p["name"]: p for p in params}
    models = make_models(solver)
    claims = []
    mappings = []
    diagnostics = []
    for key, statement, names, path, needle in data["claims"]:
        claim = {
            "id": f"claim:{solver}:{key}",
            "solver": solver,
            "statement_zh": statement,
            "scope": "Newton 1.7.0 static source only",
            "evidence_type": "source_checked",
            "parameter_ids": [byname[n]["id"] for n in names],
            "source_refs": [ref(path, needle)],
        }
        claims.append(claim)
        mappings.append(
            {
                "id": f"map:{solver}:{key}",
                "solver": solver,
                "title_zh": statement.split("；")[0],
                "paper_id": papers[0]["id"],
                "paper_ids": [p["id"] for p in papers],
                "paper_locator": "源码事实；所连论文只提供方法背景，不是此包装层行为的逐项出处",
                "correspondence": statement,
                "boundary": "保留兼容 ID 的 implementation_fact。默认、分支和包装层行为由固定源码支持；不计作独立论文算法映射或已复现性能。",
                "parameter_ids": claim["parameter_ids"],
                "source_refs": claim["source_refs"],
                "symbols": [],
                "mapping_kind": "implementation_fact",
                "evidence_type": "source_checked",
            }
        )
    mappings.extend(mechanism_records(solver, byname, ref))
    if solver == "kamino":
        link_mapping_evidence(mappings, saved_cases)
    mechanism_text = "\n## 具体机制与论文对应\n\n"
    for m in mappings:
        if m.get("mapping_kind") != "mechanism_correspondence":
            continue
        mechanism_text += (
            f"### {m['title_zh']}\n\n{m['paper_locator']}\n\n{m['correspondence']}\n\n"
            + "源码符号：" + "、".join(f"[{s['name']}]({s['url']})" for s in m["symbols"])
            + f"。\n\n适用边界：{m['boundary']}\n\n"
        )
    data["theory"] += mechanism_text
    data["papers"] += mechanism_text + COVERAGE[solver]
    for i, (symptom, plan, caution, names) in enumerate(data["diagnostics"], 1):
        diagnostics.append(
            {
                "id": f"diagnostic:{solver}:{i}",
                "solver": solver,
                "symptom": symptom,
                "plan": plan,
                "caution": caution,
                "parameter_ids": [byname[n]["id"] for n in names],
                "evidence_type": "proposed",
                "status": "not_run",
            }
        )
    dossier = {
        "id": solver,
        "name": data["name"],
        "version": "1.7.0",
        "commit": SHA,
        "parameters": params,
        "model_inputs": models,
        "claims": claims,
        "mappings": mappings,
        "diagnostics": diagnostics,
        "papers": papers,
        "experiments": [],
        "counts": {
            "constructor_optional": sum(p["layer"] == "solver_constructor" and not p["required"] for p in params),
            "config_fields": sum(p["layer"] == "solver_configuration" for p in params),
            "reset_fields": sum(p["layer"] == "reset_configuration" for p in params),
            "parameters": len(params),
            "model_inputs": len(models),
            "papers": len(papers),
            "experiments": 0,
        },
        "evidence_status": "Source and paper curation; archived lab cases are joined by the unified build. This generator performs no simulations.",
        "capabilities": {
            "coordinate_system": "generalized joint coordinates" if solver == "mujoco" else "maximal body coordinates",
            "deformable_solver": False,
            "experimental": solver == "kamino",
            "source_refs": [ref("docs/solvers/" + solver + ".rst", line=5)],
        },
    }
    folder = "solvers/" + solver
    replay_note = "\n\n## 实体轮廓回放\n\n当前 MuJoCo / Kamino 参数实验已统一为三维实体轮廓展示，可同步旋转、缩放、切换正侧俯视和放大 A/B。原始几何按冻结尺寸绘制；无 shape 的转子以标注的示意转盘显示保存转角，不改变动力学或碰撞模型。归档数据、曲线与验收结果保持原样。历史实验 README 中的坐标轴展示描述对应原版视图；当前展示机制见 [新版回放说明](../../experiments/solid_replay/README.md)。\n"
    if experiment_document:
        write(folder + "/experiments.md", experiment_document + replay_note)
    if pd_document:
        write(folder + "/pd-experiments.md", pd_document + replay_note)
    for name, obj in [
        ("parameters", {"solver": solver, "version": "1.7.0", "records": params}),
        ("model-inputs", models),
        ("claims", claims),
        ("paper-code-map", mappings),
        ("diagnostics", diagnostics),
        ("capabilities", dossier["capabilities"]),
        ("catalog", dossier),
    ]:
        write(folder + "/" + name + ".json", obj)
    footer = (
        "\n\n## 固定来源\n\n"
        + "\n".join(
            "- " + cite(r)
            for r in [
                ref(MU if solver == "mujoco" else KA, "class Solver"),
                ref("docs/solvers/" + solver + ".rst", line=5),
                ref(MU if solver == "mujoco" else KA, "def step("),
            ]
        )
        + "\n"
    )
    for stem, key, title in [
        ("theory", "theory", "原理与机制"),
        ("implementation", "implementation", "源码导读"),
        ("papers", "papers", "论文与实现"),
        ("version-notes", "versions", "版本与边界"),
    ]:
        text = f"# {data['name']} · {title}\n\nNewton 1.7.0，commit `{SHA}`。\n\n" + data[key]
        if stem == "papers":
            text += "\n## 本地原文\n\n" + "\n".join(
                f"- [{p['title']}](../../{p['local_path']})，{p['pages']} 页；[作者/出版方入口]({p['url']})。"
                for p in papers
            )
        write(folder + "/" + stem + ".md", text + footer)
    text = f"# {data['name']} · 完整参数与配置\n\n构造参数、嵌套配置和 reset 字段分层列出。声明默认不一定是给定 Model/后端的最终值。\n\n"
    for group in dict.fromkeys(p["category"] for p in params):
        text += "\n## " + group + "\n\n"
        for p in (v for v in params if v["category"] == group):
            text += f"### `{p['name']}`\n\n{p['summary_zh']}\n\n- 类型：`{p['type']}`；声明默认：`{p['declared_default_expression'] if not p['required'] else '必填'}`。\n- 最终默认策略：{p.get('default_policy', '直接声明值；仍需核对适用后端。')}\n- 原始说明（上游 docstring，执行边界以上述实现解读为准）：{p['documentation']}\n- 源码：{cite(p['definition'])}\n- 实验证据：{parameter_experiment_note(p, saved_cases)}\n\n"
    write(folder + "/parameters.md", text + footer)
    text = f"# {data['name']} · 重点模型输入\n\n这些输入与 solver 构造参数分开记录；不是全量字段数据流分析。\n\n"
    for p in models:
        text += f"## `{p['field']}`\n\n{p['description_zh']} 单位：{p['units']}。{p['default_policy']}\n\n{cite(p['model_definition'])}\n\n"
    write(folder + "/model-inputs.md", text + concepts + footer)
    text = f"# {data['name']} · 机制—论文—参数—源码对应\n\n每组对应关系包含边界；包装层默认事实由源码提供。\n\n"
    for m in mappings:
        text += (
            f"## {m['title_zh']}\n\n类型：{m.get('mapping_kind', 'curated_mapping')}。\n\n{m['correspondence']}\n\n参数："
            + "、".join("`" + n.split(f"{solver}:", 1)[-1] + "`" for n in m["parameter_ids"])
            + f"。论文定位：{m['paper_locator']}。{m['boundary']}\n\n"
            + "源码符号：" + "、".join(f"[{s['name']}]({s['url']})" for s in m["symbols"]) + "\n\n"
            + "\n".join(cite(r) for r in m["source_refs"])
            + "\n\n"
        )
        for evidence in m.get("local_experiments", []):
            text += f"局部实测：[{evidence['record_id']}](#/record/{quote(evidence['record_id'], safe='')})。{evidence['scope']}。边界：{evidence['limitation']}。\n\n"
    write(folder + "/paper-code-map.md", text + footer)
    text = f"# {data['name']} · 诊断与实验计划\n\n**全部为 proposed / not_run，不是既有成功调参经验。**\n\n"
    for d in diagnostics:
        text += (
            "## "
            + d["symptom"]
            + "\n\n"
            + "\n".join(f"{i}. {p}" for i, p in enumerate(d["plan"], 1))
            + "\n\n边界："
            + d["caution"]
            + "\n\n"
        )
    write(folder + "/diagnostics.md", text + footer)
    return dossier


def main():
    papers = json.loads((ROOT / "manifests/extra-papers.json").read_text(encoding="utf-8"))
    entries = {solver: build(solver, [p for p in papers if p["solver"] == solver]) for solver in CONTENT}
    nodes, edges = [], []
    for solver, cat in entries.items():
        root_id = f"solver:{solver}:1.7.0"
        nodes.append({"id": root_id, "type": "solver", "label": cat["name"], "solver": solver})
        for kind, records in [
            ("parameter", cat["parameters"]),
            ("model_input", cat["model_inputs"]),
            ("claim", cat["claims"]),
            ("mechanism_mapping", cat["mappings"]),
            ("diagnostic", cat["diagnostics"]),
            ("paper", cat["papers"]),
        ]:
            for p in records:
                nodes.append(
                    {
                        "id": p["id"],
                        "type": kind,
                        "solver": solver,
                        "label": p.get(
                            "name",
                            p.get(
                                "field",
                                p.get("statement_zh", p.get("title_zh", p.get("symptom", p.get("title", p["id"])))),
                            ),
                        ),
                    }
                )
                edges.append(
                    {
                        "source": root_id,
                        "target": p["id"],
                        "relation": "contains",
                        "evidence": "static_source_or_curated",
                    }
                )
                for target in p.get("parameter_ids", []):
                    edges.append(
                        {
                            "source": p["id"],
                            "target": target,
                            "relation": "proposes_test_for" if kind == "diagnostic" else "explains",
                            "evidence": p.get("evidence_type", "curated_mapping"),
                        }
                    )
                if kind == "mechanism_mapping":
                    for paper_id in p["paper_ids"]:
                        edges.append(
                            {
                                "source": p["id"],
                                "target": paper_id,
                                "relation": "method_background",
                                "evidence": "curated_mapping",
                            }
                        )
                for source in [p.get("definition"), p.get("model_definition"), p.get("consumer")] + p.get(
                    "source_refs", []
                ):
                    if not source:
                        continue
                    sid = f"source:{solver}:{source['path']}:{source['line']}"
                    if not any(n["id"] == sid for n in nodes):
                        nodes.append(
                            {
                                "id": sid,
                                "solver": solver,
                                "type": "code_symbol",
                                "label": source["path"].split("/")[-1] + ":" + str(source["line"]),
                                "source_ref": source,
                            }
                        )
                    edges.append(
                        {
                            "source": p["id"],
                            "target": sid,
                            "relation": "defined_at" if kind == "parameter" else "supported_by",
                            "evidence": "source_checked",
                        }
                    )
    write("graph/extra-solvers.json", {"nodes": nodes, "edges": edges})
    write(
        "manifests/extra-solvers-1.7.0.json",
        {
            "version": "1.7.0",
            "commit": SHA,
            "generator": "scripts/extend_solvers.py",
            "inspected_files": [
                {"path": p, "sha256": hashlib.sha256((SOURCE / p).read_bytes()).hexdigest()} for p in FILES
            ],
            "solvers": {key: c["counts"] for key, c in entries.items()},
            "evidence": "Static extraction plus curated reading; no new simulation runs.",
        },
    )
    marker = "\n<!-- MULTI_SOLVER_EXTENSION -->"
    original = (ROOT / "README.md").read_text(encoding="utf-8").split(marker)[0]
    original = original.replace("# Newton 1.7.0 · VBD 知识库样板", "# Newton 1.7.0 · Solver 知识库")
    write(
        "README.md",
        original
        + marker
        + "\n\n## MuJoCo / Kamino 与 MCP 扩展\n\n当前包含 VBD、MuJoCo、Kamino，使用相同的原理、源码、论文、参数、模型输入、机制对应和诊断文档结构。\n\n- [MuJoCo 原理](solvers/mujoco/theory.md) · [完整参数](solvers/mujoco/parameters.md) · [实现边界](solvers/mujoco/version-notes.md)。\n- [Kamino 原理](solvers/kamino/theory.md) · [分层配置](solvers/kamino/parameters.md) · [实现边界](solvers/kamino/version-notes.md)。\n- [只读 stdio MCP 与 agent 接入](mcp_service/README.md)。\n\n已有归档实验的范围与复现见 [多 solver 参数实验](experiments/solver_parameter_lab/README.md)；诊断计划仍为 proposed。4 篇相关论文保存在 sources/papers，校验值在 manifests/extra-papers.json。配置可从 scripts/extend_solvers.py 重建；生成器不下载原文或运行仿真，也不将未测字段升级为实验验证。\n",
    )
    print(json.dumps({key: c["counts"] for key, c in entries.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
