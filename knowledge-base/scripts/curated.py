"""Human-reviewed metadata layered on reproducible AST extraction. Edit this to extend the template."""
from pathlib import Path
import json
from extract_sources import ROOT, SRC, SHA, ref, dump
SYMBOLS=json.loads((ROOT/'indexes/source_symbols.json').read_text(encoding='utf-8'))['symbols']

def symbol(name):
    matches=[s for s in SYMBOLS if s['name']==name]
    if len(matches)!=1: raise ValueError((name,len(matches)))
    return matches[0]

def anchor(path, needle):
    lines=(SRC/path).read_text(encoding='utf-8').splitlines()
    hits=[i for i,l in enumerate(lines,1) if needle in l]
    if not hits: raise ValueError((path,needle))
    return ref(path,hits[0])

# name | category | units | Chinese interpretation. Unknown/conditional units are explicitly left contextual.
PARAMS='''model|模型|对象|ModelBuilder.finalize 产生的模型，需完成粒子和由 VBD 积分的刚体着色；不是调参旋钮。
iterations|数值预算|次/step|每个 step 的 VBD 外迭代次数；每次先刚体再粒子，各自按颜色更新。更多迭代不能修复漏检或错误物理模型。
friction_epsilon|摩擦正则|长度/时间（SI: m/s）|低相对速度的摩擦平滑阈值；内核以 epsilon*dt 转为滑移距离阈值，不是摩擦系数 mu。
dat_conservative_bound_relaxation|DAT|无量纲|DAT 保守截断系数；源码强制 0<值<1；共享于粒子与启用的刚柔 DAT。
integrate_with_external_rigid_solver|耦合模式|布尔|True 时由外部 solver 积分刚体，state_in/out 必须分别提供上一/当前刚体状态；这个选项本身不构成双向耦合。
particle_enable_self_contact|自接触|布尔|启用软体顶点-三角形和边-边自接触；检测调度不得为 NONE。
particle_self_contact_radius|弃用兼容|长度|旧交互半径。设置它时 margin 仍表示旧检测半径；不可同时指定 gap。新配置应迁移至 margin+gap。
particle_self_contact_margin|自接触|长度|显式指定 gap 才采用新语义：相互作用距离。单独给 margin 且不传 radius/gap 时仍采用旧检测半径语义。
particle_self_contact_gap|自接触|长度|新语义的额外检测距离，query_radius=margin+gap；新配置即使 gap=0 也应显式填写。
particle_conservative_bound_relaxation|弃用兼容|无量纲|弃用别名；非 None 时覆盖 dat_conservative_bound_relaxation 并警告。
particle_vertex_contact_buffer_size|容量|候选对/顶点|每顶点的顶点-三角形候选容量；超出容量的对会在检测时被静默丢弃。
particle_edge_contact_buffer_size|容量|候选对/边|每边的边-边候选容量；超出容量的对会在检测时被静默丢弃。
particle_collision_detection_interval|弃用兼容|迭代间隔|旧调度：负数 PRE_INIT，0 PRE_POST_INIT，正 n ITERATIONS；新配置用 collision_frequency_type/frequency。
particle_edge_parallel_epsilon|几何数值|内核近乎平行判据阈值|边-边接触中识别近乎平行边的阈值；不要当作接触厚度。
particle_enable_tile_solve|执行策略|布尔|CUDA 上使用 tiled 粒子弹性核，CPU 自动停用；构造时按材料特化，改变三角形/边刚度后重建 solver。
particle_topological_contact_filter_threshold|自接触过滤|拓扑环数|丢弃拓扑距离过近的候选；增大可能滤掉真实折叠接触，文档提示超过 3 环代价明显。
particle_rest_shape_contact_exclusion_radius|自接触过滤|长度|根据 model.particle_q 的静止构形间距额外排除近邻候选；不是当前帧接触半径。
particle_external_vertex_contact_filtering_map|自接触过滤|primitive ID 映射|额外排除的 vertex→triangle ID 集合/列表；仅自接触启用时使用。
particle_external_edge_contact_filtering_map|自接触过滤|primitive ID 映射|额外排除的 edge→edge ID 集合/列表；避免拿场景对象 ID 代替 primitive ID。
rigid_compliant_alm|刚体模式|布尔或 None|True 为推荐的 compliant ALM；1.7.0 省略时实际为 False legacy，并在积分刚体时警告。须显式固定。
rigid_avbd_alpha|约束稳定化|无量纲|既存约束误差稳定化，作用于 C-alpha*C0；None 在 compliant 为 0、legacy 为 0.95。不是刚度。
rigid_avbd_joint_alpha|约束稳定化|无量纲|关节行 alpha 覆盖；None 继承已解析的全局 alpha。
rigid_avbd_contact_alpha|约束稳定化|无量纲|接触行 alpha 覆盖；None 继承已解析的全局 alpha。
rigid_avbd_beta|legacy 罚参数|依约束残差量纲|legacy penalty ramp 的全局速率，0 表示不增长；不能把它当物理刚度。body-particle penalty 路径也使用该设置。
rigid_avbd_linear_beta|legacy 罚参数|线性行的刚度/残差|None 继承 beta；线性约束和 body-particle 接触增长速率。
rigid_avbd_angular_beta|legacy 罚参数|角度行的刚度/残差|None 继承 beta；角约束增长速率；线性和角度参数不可直接等量替换。
rigid_avbd_gamma|历史状态|无量纲|历史罚参数/乘子衰减。legacy 乘子保留 alpha*gamma，compliant 保留 gamma；论文示例 gamma 不等于源码默认。
rigid_contact_hard|legacy 模式|布尔|控制 legacy 刚体接触硬约束乘子行为；compliant ALM 中无该硬/软切换效应。
rigid_contact_history|历史状态|布尔|跨帧恢复刚体接触状态；要求接触匹配可用，owned pipeline 的 matching=disabled 会被拒绝。
rigid_contact_stick_motion_eps|已忽略|旧接口|已弃用且忽略；传数值不产生 deadzone 效果。几何持久化应在 CollisionPipeline 配置 sticky matching。
rigid_contact_stick_freeze_translation_eps|已忽略|旧接口|已弃用且忽略，不应纳入调参搜索空间。
rigid_contact_stick_freeze_angular_eps|已忽略|旧接口|已弃用且忽略，不应纳入调参搜索空间。
rigid_contact_k_start|legacy 罚参数|接触刚度量纲|legacy 接触罚参数起点；beta=0 时不起渐增作用，compliant 的刚体行由内部 rho 策略决定。
rigid_body_contact_buffer_size|容量|接触/刚体|每刚体接触邻接表容量；不同于 CollisionPipeline 的全局 rigid_contact_max。
rigid_body_particle_contact_buffer_size|容量|接触/刚体|每刚体刚柔接触邻接表容量；不同于全局 soft_contact_max，需考虑接触密度。
rigid_soft_contact_use_log_barrier|刚柔接触|布尔|False 为默认二次 penalty；True 使用与软体自接触同类的 C2 log barrier。不是 DAT 开关。
rigid_joint_linear_ke|物理/结构行|N/m|非 ROD 关节结构线性刚度；compliant 中是有限材料刚度，legacy 中还承担相应罚参数边界语义。
rigid_joint_angular_ke|物理/结构行|N·m/rad|非 ROD 关节结构角刚度；不可与线性 ke 混为同一量纲。
rigid_joint_linear_k_start|legacy 罚参数|N/m|legacy 结构线性行罚参数起点；是否生效与 beta/模式有关。
rigid_joint_angular_k_start|legacy 罚参数|N·m/rad|legacy 结构角行罚参数起点；不是 ROD 的材料参数。
rigid_joint_linear_kd|物理/结构行|N·s/m|非 ROD 结构线性阻尼，绝对物理阻尼系数，负值按源码夹为 0。
rigid_joint_angular_kd|物理/结构行|N·m·s/rad|非 ROD 结构角阻尼，绝对物理阻尼系数，负值按源码夹为 0。
rigid_soft_enable_dat|DAT|布尔|为刚柔接触启用刚体与粒子运动截断；要求 solver-owned pipeline，禁止 external rigid，实际查询存在时最小查询半径须为正。不能推广为全场景无穿透保证。
rigid_soft_dat_use_interval_arithmetic|DAT|布尔|刚柔 DAT 刚体轨迹截断的区间算术求界选项；仅对应路径启用时有意义。
deterministic|执行策略|Warp 枚举或 None|None 继承 wp.config.deterministic；非 NOT_GUARANTEED 模式采用无原子 per-particle gather 等路径，不代表跨所有设备逐位相同。
collision_pipeline|碰撞所有权|对象或 None|传入后 solver 持有 pipeline/contacts 并按调度执行检测；step 必须传 contacts=None。未传时由调用者外部检测。
collision_frequency|碰撞调度|迭代间隔映射|按 CollisionSlot 配置 ITERATIONS 模式的 k；与 frequency_type 合用，可经 set_collision_frequency 更新。刚柔 DAT 与自接触同时启用时，RIGID/SOFT_SELF_CONTACT 的 ITERATIONS 频率必须相同。
collision_frequency_type|碰撞调度|枚举映射|AUTO 默认：启用软自接触为 PRE_POST_INIT；owned rigid 默认 PRE_INIT，开启 rigid_soft DAT 时为 PRE_POST_INIT。双 DAT 同时启用时两个 slot 的解析类型须一致，ITERATIONS 还须同频率。'''

RESOLVED={
 'model':'required; no default',
 'rigid_compliant_alm':'None -> False in 1.7.0; explicit True selects compliant ALM',
 'rigid_avbd_alpha':'None -> 0.0 (compliant) or 0.95 (legacy)',
 'rigid_avbd_joint_alpha':'None -> resolved rigid_avbd_alpha',
 'rigid_avbd_contact_alpha':'None -> resolved rigid_avbd_alpha',
 'rigid_avbd_linear_beta':'None -> rigid_avbd_beta',
 'rigid_avbd_angular_beta':'None -> rigid_avbd_beta',
 'particle_self_contact_margin':'all omitted -> interaction 0.2; explicit gap -> margin (or 0.2); margin-only -> legacy query radius',
 'particle_self_contact_gap':'None -> 0 only in default/new convention; legacy radius/margin computes query minus interaction',
 'collision_frequency_type':'AUTO resolved per slot and active DAT family',
 'deterministic':'None -> wp.config.deterministic',
}

def parameters():
    raw=json.loads((ROOT/'solvers/vbd/parameters.raw.json').read_text(encoding='utf-8'))['records']
    meta={v[0]:v[1:] for l in PARAMS.splitlines() if (v:=l.split('|'))}
    assert set(meta)=={r['name'] for r in raw}
    out=[]
    for r in raw:
        group,units,description=meta[r['name']]
        out.append({**r,'category':group,'units':units,'summary_zh':description,
            'resolved_default':RESOLVED.get(r['name'],r['declared_default_expression']),
            'lifecycle':'construction; do not assume direct attribute edits refresh caches; use documented setter/notify or reconstruct',
            'suggested_tuning_range':None,'tuning_range_status':'not established by this KB',
            'status':'ignored_deprecated' if group=='已忽略' else ('deprecated' if group=='弃用兼容' else 'active'),
            'source_of_truth':'pinned signature + constructor/docstring + kernels; English raw doc retained for audit'})
    dump('solvers/vbd/parameters.json',{'schema_version':'1.0','solver':'SolverVBD','newton_version':'1.7.0','commit':SHA,'records':out})
    return out

# Claims and their scope are intentionally small; paper associations are not equivalence claims.
CLAIMS=[
 ('c:implicit','VBD 通过惯性势能与材料能量构造隐式积分问题，逐顶点解 3×3 局部系统；每次局部 Newton 更新不等于完整求解全局最小值。','particle','solve_elasticity','paper:vbd2024','PDF pp.3–4, Eqs.(2)–(9)', ['iterations']),
 ('c:step','step 的顺序为初始化、交错外迭代、最终输出；每个外迭代先刚体后粒子，最后更新速度及历史。','all','SolverVBD.step',None,None,['iterations']),
 ('c:alm_mode','Newton 1.7.0 省略 rigid_compliant_alm 实际选择 legacy False；推荐显式 True 启用 compliant ALM。','rigid','SolverVBD.__init__',None,None,['rigid_compliant_alm']),
 ('c:alm_math','compliant ALM 将材料刚度 K 与数值 rho 分开，s=K/(K+rho)，k_eff=K*rho/(K+rho)，行力项为 k_eff*C+s*lambda；并非直接等同 AVBD 论文 legacy 公式。','rigid compliant','_material_force_terms',None,None,['rigid_compliant_alm','rigid_joint_linear_ke']),
 ('c:dual','compliant 的有限刚度双边行按 lambda <- s*(lambda+rho*(C-alpha*C0)) 更新；单边接触还投影法向非负和切向 Coulomb 圆盘。','rigid compliant','_compliant_contact_dual_step',None,None,['rigid_avbd_alpha','rigid_avbd_contact_alpha']),
 ('c:legacy','legacy 硬行积累乘子，软行不按同样方式积累；beta 控制 penalty 增长，compliant 刚体结构行走内部 rho 策略。body-particle 路径仍有 penalty 更新。','legacy / body-particle','_update_joint_structural_dual','paper:avbd2025','PDF pp.3–6, Eqs.(8)–(12),(19), Algorithm 1',['rigid_avbd_beta','rigid_contact_hard']),
 ('c:friction','friction_epsilon 是速度平滑阈值，内核将它乘 dt；摩擦系数来自材料 mu。','contact','compute_friction',None,None,['friction_epsilon']),
 ('c:margin','1.7.0 的 margin 单独设置仍为旧检测半径语义；新语义必须显式设置 gap，query radius=margin+gap。','soft self-contact','SolverVBD.__init__',None,None,['particle_self_contact_margin','particle_self_contact_gap','particle_self_contact_radius']),
 ('c:dat','DAT 在候选接触定义的区域内截断位移；开启开关并不证明任意场景都无穿透或无翻转，初始合法性、候选覆盖及容量均需验证。','DAT conditional','apply_planar_truncation_parallel_by_collision','paper:dat2026','PDF pp.3–5, Sec.3, Eqs.(11)–(16)',['rigid_soft_enable_dat','dat_conservative_bound_relaxation']),
 ('c:capacity','顶点/边自接触容量溢出会静默丢弃候选对；不能用增大 iterations 补偿已丢弃的候选。','soft self-contact','SolverVBD.__init__',None,None,['particle_vertex_contact_buffer_size','particle_edge_contact_buffer_size']),
 ('c:external','integrate_with_external_rigid_solver=True 只让 VBD 使用外部已积分刚体状态，本选项文档定义为单向耦合。','external rigid','SolverVBD._solve_particle_iteration',None,None,['integrate_with_external_rigid_solver']),
 ('c:tile','tile solve 仅 CUDA 可用，构造时根据材料类别特化；三角形/边刚度改变后需重建，CPU 探针不覆盖该路径。','particle CUDA','SolverVBD._init_particle_system',None,None,['particle_enable_tile_solve']),
 ('c:history','rigid_contact_history 需要有效 contact matching；owned pipeline 禁用 matching 时构造会拒绝。跨帧对应关系属于 pipeline。','rigid history','SolverVBD.__init__',None,None,['rigid_contact_history']),
 ('c:ignored','三个 rigid_contact_stick_* 参数在 1.7.0 已弃用并忽略。','constructor','SolverVBD.__init__',None,None,['rigid_contact_stick_motion_eps','rigid_contact_stick_freeze_translation_eps','rigid_contact_stick_freeze_angular_eps']),
 ('c:schedule','solver 拥有 pipeline 时自己运行碰撞检测；AUTO 的 self-contact 和 rigid DAT 为 PRE_POST_INIT，普通 owned rigid 为 PRE_INIT。同时启用刚柔 DAT 与自接触时，RIGID/SOFT_SELF_CONTACT 必须同解析类型，ITERATIONS 时还须同频率。','collision ownership','SolverVBD._default_collision_frequency_type',None,None,['collision_pipeline','collision_frequency_type','collision_frequency']),
 ('c:support','VBD 支持 BALL/FIXED/FREE/REVOLUTE/PRISMATIC/D6/ROD；DISTANCE、joint_armature、joint_friction、effort/velocity limits、joint_target_mode 和 equality constraints 不在此版本支持集合。','rigid feature boundary','SolverVBD',None,None,[]),
 ('c:observable','CONTACT_F 在最终迭代构形导出刚体-刚体与刚柔接触记录；不包含软体自接触力，不能把它当作所有接触力。','observables','SolverVBD',None,None,[]),
 ('c:reset','VBD reset 清理自己的历史但不代替重新碰撞；突变重置还需 reset_contact_matching。JOINT_Q/QD 不直接作为最大坐标状态重置。','lifecycle','SolverVBD.reset',None,None,[]),
 ('c:cache','非 ROD 结构材料/布局/静止角在构造缓存；ROD target ke/kd 材料更新用 JOINT_DOF_PROPERTIES 或 JOINT_DOF_FORCE_PROPERTIES。ROD rest frame/rest pose 更新需 JOINT_PROPERTIES 或 BODY_PROPERTIES 才刷新静止弯扭角；直接改数组不保证派生量更新。','lifecycle','SolverVBD.notify_model_changed',None,None,['rigid_joint_linear_ke','rigid_joint_angular_ke']),
    ('c:attachment','粒子-刚体 attachment 要求 VBD 积分两端，不支持 external-rigid 模式；物理引擎支持 attachment 不等于真实抓取任务允许虚拟粘接。','model and task boundary','SolverVBD.__init__',None,None,['integrate_with_external_rigid_solver']),
    ('c:rigid_dat_requires','rigid_soft_enable_dat 要求 solver-owned collision_pipeline，禁止 external rigid solver，存在刚柔查询时要求 soft_contact_gap+最小粒子半径+最小 shape_margin 为正。','rigid-soft DAT','SolverVBD._init_rigid_penetration_free',None,None,['rigid_soft_enable_dat','collision_pipeline']),
    ('c:damping','1.7.0 膜/体积弹性内核使用基于 F^T F 的客观阻尼，不能直接把 VBD 2024 论文的简化 Rayleigh 阻尼公式当作当前 tri_kd/tet damping 实现。','particle material','evaluate_neo_hookean_membrane_force_hessian','paper:vbd2024','PDF p.4 Sec.3.3 is background, not current damping identity',[]),
]

def claims():
    rows=[]
    for cid,text,scope,name,paper,loc,params in CLAIMS:
        s=symbol(name)
        rows.append({'id':cid,'statement_zh':text,'scope':scope,'version':'1.7.0','commit':SHA,
            'evidence_kind':'source_reading_and_qualified_interpretation','source_refs':[s['source']],
            'symbol_ids':[s['id']],'paper_refs':[{'id':paper,'locator':loc,'relation':'method_background_not_implementation_identity'}] if paper else [],
            'parameter_ids':['newton:1.7.0:SolverVBD:'+p for p in params],
            'empirical_scope':None,'review_status':'source_checked; not an empirical universal guarantee'})
    # Add narrow source evidence instead of relying only on long class/constructor spans.
    extras={
        'c:alm_mode':('solver_vbd.py','rigid_compliant_alm = False'),
        'c:margin':('solver_vbd.py','if particle_self_contact_margin is not None and particle_self_contact_gap is None:'),
        'c:dual':('rigid_vbd_kernels.py','def _update_dual_vec3('),
        'c:legacy':('solver_vbd.py','kernel=update_duals_body_particle_contacts'),
        'c:friction':('particle_vbd_kernels.py','eps_U = friction_epsilon * dt'),
        'c:capacity':('solver_vbd.py','beyond this capacity are silently dropped'),
        'c:history':('solver_vbd.py','and collision_pipeline.contact_matching == "disabled"'),
        'c:ignored':('solver_vbd.py','are deprecated and ignored'),
        'c:schedule':('solver_vbd.py','def _validate_dat_collision_schedules('),
        'c:cache':('solver_vbd.py','def _refresh_rod_rest_bend_twist_cache('),
    }
    for r in rows:
        if r['id'] in extras:
            p,n=extras[r['id']];r['source_refs'].append(anchor('newton/_src/solvers/vbd/'+p,n))
    dump('solvers/vbd/claims.json',rows)
    return rows

MAPPINGS=[
 ('map:variational','惯性目标与隐式积分','paper:vbd2024','PDF p.3 Eqs.(2)–(4); p.4 Eq.(6)', ['SolverVBD._initialize_particles','solve_elasticity','SolverVBD._finalize_particles'],['iterations'],'exp:implicit_spring','implementation_of_core_idea; full nonlinear convergence not proven by probe'),
 ('map:block','局部 3×3 系统与着色','paper:vbd2024','PDF p.4 Eqs.(7)–(9); Sec.3.9', ['SolverVBD._solve_particle_iteration','solve_elasticity','make_solve_elasticity_tile'],['iterations','particle_enable_tile_solve'],'exp:implicit_spring','scalar and tile kernels are distinct implementations'),
 ('map:elastic','膜、弯曲与体积弹性','paper:vbd2024','Sec.3 material-energy framework', ['evaluate_neo_hookean_membrane_force_hessian','evaluate_dihedral_angle_based_bending_force_hessian','evaluate_volumetric_neo_hookean_force_and_hessian'],[] ,None,'constitutive-model correspondence, not identical discretization of every paper experiment'),
 ('map:legacy','legacy AVBD primal / dual / penalty','paper:avbd2025','PDF p.3 Eqs.(8)–(12); p.6 Algorithm 1', ['solve_rigid_body','ldlt6_solve','update_duals_joint','_ramp_penalty_k'],['rigid_avbd_beta','rigid_avbd_alpha','rigid_avbd_gamma'],'exp:default_modes','legacy foundation; source default beta=0/gamma=.999 differ from paper experiment settings'),
 ('map:compliant','compliant ALM 工程扩展',None,'source equations; no identical paper equation asserted', ['_compliant_alm_coefficients','_alm_relaxed_ascent','_material_force_terms','_compliant_contact_dual_step'],['rigid_compliant_alm','rigid_joint_linear_ke'],'exp:default_modes','source_extension; mode probe does not validate all ALM dynamics'),
 ('map:friction','平滑摩擦与接触投影','paper:vbd2024','Sec.3.6', ['compute_friction','_compliant_contact_dual_step'],['friction_epsilon'],None,'particle regularization vs compliant rigid Coulomb projection must be distinguished'),
 ('map:dat','平面划分与位移截断','paper:dat2026','PDF p.4 Eqs.(11)–(16); Sec.3', ['create_vertex_triangle_division_plane_closest_pt','create_edge_edge_division_plane_closest_pt','apply_planar_truncation_parallel_by_collision','rigid_trajectory_truncation_t'],['dat_conservative_bound_relaxation','rigid_soft_enable_dat','rigid_soft_dat_use_interval_arithmetic'],None,'conditional geometry mechanism; dense collision runtime validation pending'),
 ('map:detect','候选检测范围与兼容层','paper:dat2026','neighborhood coverage assumption; no constructor naming in paper', ['SolverVBD.__init__','SolverVBD._collision_detection_penetration_free'],['particle_self_contact_margin','particle_self_contact_gap','particle_vertex_contact_buffer_size','particle_edge_contact_buffer_size'],'exp:margin_compatibility','engineering API semantics; paper has no Newton parameter defaults'),
]

# Saved lab runs support only the named submechanisms, not the entire mapping.
# Keep these IDs distinct from the earlier exp:* constructor/CPU probes.
LOCAL_MAPPING_EVIDENCE = {
    'map:elastic': {
        'local_experiments': [
            {
                'record_id': 'lab:membrane',
                'scope': '固定单三角形和载荷下，同时改变 tri_ke 与 tri_ka 的薄膜位移响应。',
                'limitation': '联合干预不能分别识别两项贡献；没有验证 tet、厚度换算或网格收敛。',
            },
            {
                'record_id': 'lab:bending',
                'scope': '两个三角形折页中，保持面内材料不变并改变 edge_ke 的弯曲响应。',
                'limitation': '只支持该固定拓扑的方向性结果，不是连续弯曲模量或真实材料标定。',
            },
        ],
        'unvalidated_scope': [
            'tet 体积材料、近不可压条件及其收敛。',
            '客观阻尼在刚体旋转叠加下的响应、薄膜厚度换算与网格收敛。',
        ],
    },
    'map:friction': {
        'local_experiments': [
            {
                'record_id': 'lab:friction',
                'scope': '相同初速度的单粒子平面滑动，改变接触 mu 后的位移。',
                'limitation': '没有验证刚体 Coulomb 锥投影、抓持或密集堆叠。',
            },
            {
                'record_id': 'lab:friction_epsilon',
                'scope': '相同 mu、小恒力驱动单粒子时，friction_epsilon 改变低速蠕滑。',
                'limitation': '仅支持粒子平滑摩擦；不验证刚体接触历史和跨设备结果。',
            },
        ],
        'unvalidated_scope': [
            'compliant 刚体 Coulomb 投影、抓持/堆叠以及匹配历史摩擦。',
            '不同步长、载荷与几何下的摩擦参数泛化。',
        ],
    },
    'map:dat': {
        'local_experiments': [
            {
                'record_id': 'lab:dat',
                'scope': '零半径高速质点冲向薄板、弱 penalty 条件下，开启刚柔 DAT 后的位移截断。',
                'limitation': '不是任意无穿透证明；没有验证自接触平面分配、tet 翻转或旋转刚体轨迹。',
            },
            {
                'record_id': 'lab:dat_relaxation',
                'scope': '同一简单刚柔 DAT 场景中，保守系数改变接近接触面的过程。',
                'limitation': '没有验证密集候选、容量溢出、刚体 interval arithmetic 或所有调度组合。',
            },
        ],
        'unvalidated_scope': [
            'VT/EE 分隔平面机制的逐项验证与密集/初始相交场景。',
            '旋转刚体、interval arithmetic、复杂非凸候选覆盖和 tet 反转。',
        ],
    },
}

def mappings():
    rows=[]
    for mid,title,paper,locator,names,params,exp,status in MAPPINGS:
        row={'id':mid,'title_zh':title,'paper_id':paper,'paper_locator':locator,
            'symbols':[{'id':symbol(n)['id'],'name':n,'source':symbol(n)['source']} for n in names],
            'parameter_ids':['newton:1.7.0:SolverVBD:'+p for p in params],
            'experiment_id':exp,'correspondence':status,'version':'1.7.0'}
        if mid in LOCAL_MAPPING_EVIDENCE:
            row.update(LOCAL_MAPPING_EVIDENCE[mid])
            row['validation_status']='partial_local_evidence'
        rows.append(row)
    dump('solvers/vbd/paper-code-map.json',rows)
    return rows

def graph(params,cs,maps):
    nodes={};edges=[]
    def add(n): nodes[n['id']]=n
    def edge(a,r,b,**kw): edges.append({'source':a,'relation':r,'target':b,**kw})
    add({'id':'solver:VBD:1.7.0','type':'solver','label':'SolverVBD Newton 1.7.0','commit':SHA})
    for p in json.loads((ROOT/'manifests/papers.json').read_text(encoding='utf-8')):
        add({'id':p['id'],'type':'paper','label':p['title'],'file':p['local_path'],'sha256':p['sha256']})
    for s in SYMBOLS:
        add({'id':s['id'],'type':'code_symbol','label':s['name'],'source_ref':s['source']})
    for p in params:
        add({'id':p['id'],'type':'parameter','label':p['name'],'record_file':'solvers/vbd/parameters.json'})
        edge('solver:VBD:1.7.0','has_parameter',p['id'])
        edge(p['id'],'declared_in',symbol('SolverVBD.__init__')['id'])
    for c in cs:
        add({'id':c['id'],'type':'claim','label':c['statement_zh'],'record_file':'solvers/vbd/claims.json'})
        for s in c['symbol_ids']: edge(c['id'],'supported_by_source',s)
        for p in c['parameter_ids']: edge(c['id'],'concerns_parameter',p)
        for p in c['paper_refs']: edge(c['id'],'background_method',p['id'],locator=p['locator'])
    for m in maps:
        add({'id':m['id'],'type':'mechanism_mapping','label':m['title_zh'],'record_file':'solvers/vbd/paper-code-map.json'})
        if m['paper_id']: edge(m['id'],'explained_in',m['paper_id'],locator=m['paper_locator'])
        for s in m['symbols']: edge(m['id'],'implemented_or_extended_at',s['id'],qualification=m['correspondence'])
        for p in m['parameter_ids']: edge(m['id'],'configured_by',p)
        if m['experiment_id']:
            add({'id':m['experiment_id'],'type':'experiment','label':m['experiment_id'],'results_file':'experiments/results.cpu.json'})
            edge(m['id'],'narrow_probe',m['experiment_id'])
    add({'id':'exp:constructor_guards','type':'experiment','label':'constructor guards','results_file':'experiments/results.cpu.json'})
    for r in json.loads((ROOT/'solvers/vbd/model-inputs.json').read_text(encoding='utf-8')):
        add({'id':r['id'],'type':'model_input','label':r['field'],'source_ref':r['model_definition'],'record_file':'solvers/vbd/model-inputs.json'})
        edge('solver:VBD:1.7.0','consumes_model_input',r['id'])
        matched=[s for s in SYMBOLS if s['source']['url']==r['consumer']['url']]
        if matched: edge(r['id'],'consumed_at',matched[0]['id'])
    for r in json.loads((ROOT/'solvers/vbd/diagnostics.json').read_text(encoding='utf-8')):
        add({'id':r['id'],'type':'diagnostic','label':r['symptom'],'record_file':'solvers/vbd/diagnostics.json','status':r['status']})
        for cid in r['claim_ids']: edge(r['id'],'motivated_by',cid)
    dump('graph/knowledge-graph.json',{'schema_version':'1.0','scope':'VBD@1.7.0; curated relations, not LLM-inferred causality','nodes':list(nodes.values()),'edges':edges})

if __name__=='__main__':
    p=parameters();c=claims();m=mappings();graph(p,c,m)
    print({'parameters':len(p),'claims':len(c),'mappings':len(m)})
