"""Curated model fields, capability boundary, and diagnostic plans. No invented prior tuning results."""
import json
from curated import ROOT, anchor, dump, symbol

MODEL_ROWS=[
 ('particle_mass','particle_mass','kg','质量；零质量粒子为运动学粒子。与 dt 共同决定惯性块，不可用错误质量补偿尺度错误。','solve_elasticity'),
 ('particle_radius','particle_radius','m','刚柔碰撞粒子几何半径；不同于软体自接触 margin，也参与刚柔 DAT 查询半径下界。','SolverVBD._init_rigid_penetration_free'),
 ('tri_materials','tri_materials','官方 Model 标注 [Pa, Pa, Pa·s, Pa·s, Pa]；薄膜有效量纲/厚度换算待核验','前三项为膜弹性与阻尼；内核乘静止面积，不能仅按 Pa 标签把真实三维杨氏模量直接填入；需明确厚度与离散能量约定。后两项存在不等于 VBD 全部使用。','evaluate_neo_hookean_membrane_force_hessian'),
 ('edge_bending_properties','edge_bending_properties','官方 Model 标注 [N·m/rad, N·s]；有效刚度与静止边长约定待核验','二面角弯曲参数；内核还乘静止边长，不能直接替代连续材料弯曲模量。官方单位标签和离散系数换算需单独校验。','evaluate_dihedral_angle_based_bending_force_hessian'),
 ('tet_materials','tet_materials','[mu Pa, lambda Pa, damping Pa·s]','体积弹性参数与客观阻尼，内核内部乘静止体积。','evaluate_volumetric_neo_hookean_force_and_hessian'),
 ('particle_q','particle_q','m','模型初始/静止构形；参与自接触静止过滤，不能与可变 State.particle_q 混淆。','SolverVBD._init_particle_system'),
 ('soft_contact_ke','soft_contact_ke','N/m（具体势函数须核查）','软接触刚度；二次与 barrier 路径需按实际力函数解释。','evaluate_self_contact_force_norm'),
 ('soft_contact_kd','soft_contact_kd','N·s/m','软接触阻尼；不是全局刚体阻尼。','damp_collision'),
 ('soft_contact_mu','soft_contact_mu','无量纲','软接触材料摩擦系数；不同于 friction_epsilon。','compute_friction'),
 ('shape_material_ke','shape_material_ke','N/m','每形状接触刚度；最终有效接触材料由接触初始化/混合规则决定。','init_body_body_contacts_alm'),
 ('shape_material_kd','shape_material_kd','N·s/m','每形状接触阻尼；记录两侧材料与混合后的接触记录。','init_body_body_contacts_alm'),
 ('shape_material_mu','shape_material_mu','无量纲','每形状摩擦系数；不能把单一形状值当作每个接触的最终 mu。','init_body_body_contacts_alm'),
 ('body_mass','body_mass','kg','刚体质量，连同转动惯量、质心决定局部 6×6 系统。','solve_rigid_body'),
 ('body_inertia','body_inertia','kg·m²','刚体惯量，需与几何、质心、质量一致；不是任意的稳定性旋钮。','solve_rigid_body'),
 ('joint_target_ke','joint_target_ke','平移 N/m / 转动 N·m/rad','REVOLUTE/PRISMATIC/D6 drive 与 ROD 材料；与非 ROD structural ke 分层。ROD 材料更新用 JOINT_DOF_PROPERTIES 或 JOINT_DOF_FORCE_PROPERTIES，不负责静止构形缓存。','evaluate_joint_force_hessian'),
 ('joint_target_kd','joint_target_kd','平移 N·s/m / 转动 N·m·s/rad','绝对物理阻尼；ROD 材料更新用 JOINT_DOF_PROPERTIES 或 JOINT_DOF_FORCE_PROPERTIES。ROD rest frame/rest pose 缓存另需 JOINT_PROPERTIES/BODY_PROPERTIES。','evaluate_joint_force_hessian'),
 ('joint_limit_ke','joint_limit_ke','依线性/角度 DOF','支持的关节限位行材料，不等同结构连接刚度。','evaluate_joint_force_hessian'),
 ('joint_enabled','joint_enabled','布尔','使能标志读 live；JOINT_PROPERTIES 通知还会刷新派生接触 conditioning。','SolverVBD'),
 ('spring_stiffness','spring_stiffness','N/m','粒子弹簧刚度，本样板一维 CPU 探针使用的能量项。','evaluate_spring_force_and_hessian'),
 ('spring_damping','spring_damping','N·s/m','粒子弹簧阻尼，探针取 0 以便与解析隐式步比较。','evaluate_spring_force_and_hessian'),
]

def main():
    rows=[]
    for name,needle,unit,note,fn in MODEL_ROWS:
        rows.append({'id':'model:'+name,'field':name,'units':unit,'description_zh':note,
          'model_definition':anchor('newton/_src/sim/model.py','self.'+needle+':'),
          'consumer':symbol(fn)['source'],'constructor_parameter':False,
          'default_policy':'Read instantiated model and builder/importer configuration; no universal scene default asserted.',
          'version':'1.7.0'})
    dump('solvers/vbd/model-inputs.json',rows)
    caps={
     'version':'1.7.0','evidence':symbol('SolverVBD')['source'],
     'supported':['cloth triangles and bending edges','tetrahedral deformables','particle springs','rigid bodies','BALL','FIXED','FREE','REVOLUTE','PRISMATIC','D6','ROD','particle-body compliant attachments when VBD owns both','joint-owned mimic for supported joint types'],
     'unsupported':['DISTANCE joint','joint_armature','joint_friction','joint_effort_limit','joint_velocity_limit','joint_target_mode','equality constraints','deprecated sparse mimic constraints'],
     'conditional':['rigid-soft DAT requires owned collision pipeline and no external-rigid solver','CONTACT_F excludes soft self-contact','tile solve CUDA only','contact history requires matching','ROD Dahl requires authored positive custom parameters'],
     'not_claimed':['automatic differentiability or calibrated gradient pipeline','global nonpenetration/inversion guarantee for arbitrary scenes','OGC full availability; pinned docs say future work','physical identification from monocular video alone'],
     'status':'experimental according to release source'}
    dump('solvers/vbd/capabilities.json',caps)
    plans=[
     ('diag:penetration','薄布穿透/自接触遗漏',['c:margin','c:capacity','c:dat'],['先确认接触类别与 initial intersection；检查候选覆盖、尺度、margin/gap、primitive filters 与容量','固定材料，比较更密检测/更小 dt；观察穿透深度和候选数量，再单独增加迭代'],['max penetration','candidate counts/capacity','dt','iterations'],'不能只靠加大 ke 或 iterations'),
     ('diag:slip','抓取滑落',['c:friction','c:observable','c:attachment'],['核对真实夹紧位移/控制、两侧接触法向和接触几何','分开扫描材料 mu、摩擦平滑阈值和法向刚度；保持执行轨迹相同'],['slip displacement','contact wrench','object pose error'],'不能以 attachment 或人为位置锁定宣称恢复真实摩擦抓取'),
     ('diag:soft','材料太软/关节漂移',['c:alm_math','c:legacy','c:cache'],['先分离物理材料、结构刚度、drive 参数与数值收敛','固定物理参数增加预算检查解是否收敛，再改变材料并比较静态形变'],['static deflection','joint residual','runtime'],'外观变硬不等于已识别真实刚度'),
     ('diag:oscillation','抖动或过度阻尼',['c:damping','c:friction','c:implicit'],['核对阻尼量纲和模型尺度；不要套用旧版 tri_kd 经验','固定物理参数分别扫 dt 和 iterations，再扫材料 damping；记录相位、幅度和静态形变'],['amplitude decay','phase error','kinetic energy'],'数值耗散与物理阻尼可能混淆'),
     ('diag:coupling','刚体未受软体反力影响',['c:external'],['确认是否启用 external rigid 单向模式','需要双向时选统一 VBD 或审查专门 coupled solver 数据交换与力反馈'],['two-side momentum change','contact force','coupling schedule'],'单个 True 选项不会自动创建反力闭环'),
     ('diag:reset','复位后突然跳动',['c:reset','c:history'],['同时核对模型默认位姿与 episode 位姿','reset 后重做 FK/碰撞并清除 pipeline matching 历史，再进入固定步长'],['first-step displacement','history validity'],'状态重置不能保留过期接触对应关系'),
     ('diag:performance','迭代慢/显存或容量不足',['c:capacity','c:tile','c:schedule'],['把 JIT 编译排除出稳态计时，记录设备和 Warp 版本','记录 mesh/颜色数、候选数、buffer 与检测频率；比较 tile 路径但保持物理配置'],['steady step ms','memory','contact overflow','color count'],'不要靠默默漏检获得速度'),
     ('diag:dat_config','刚柔 DAT 构造失败',['c:rigid_dat_requires'],['检查 solver-owned pipeline、external-rigid 开关与正的最小查询半径','按报错修正配置后运行密集接触用例；不是放宽所有校验'],['constructor error','query radius','contact schedule'],'参数通过校验不等于几何鲁棒性已验证'),
    ]
    rows=[{'id':i,'symptom':s,'claim_ids':c,'plan':p,'metrics':m,'caution':w,'status':'proposed_diagnostic_plan_not_measured_experience','version':'1.7.0'} for i,s,c,p,m,w in plans]
    dump('solvers/vbd/diagnostics.json',rows)
    dump('experience/experiment-template.json',{
      'id':'replace-with-run-id','status':'template_not_run','newton_commit':None,'warp_version':None,'device':None,'solver_mode':None,
      'scene_hash':None,'reference_hash':None,'reference_kind':'video/robot trajectory/force sensor','units_and_frames':None,
      'reference_uncertainty':None,'geometry_and_material':{},'collision_config':{},'constructor_config':{},'dt':None,'substeps':None,'control_policy':None,'seed':None,
      'baseline_metrics':{},'intervention':{'changed_parameters':{},'all_other_conditions_fixed':None},'result_metrics':{},'cost_metrics':{},
      'success_criteria_frozen_before_run':[],'artifacts':[],'conclusion':None,'supported_claim_ids':[],'applicability_conditions':[],'counterexamples':[],
      'promotion_status':'unreviewed','historical_version_migration_validated':False})
    tests=[
      ('self-contact barrier continuity','test_self_contact_barrier_c2_at_tau'),
      ('self-contact barrier near minimum distance','test_self_contact_barrier_c2_at_d_min'),
      ('rigid DAT trajectory','test_rigid_dat_trajectory_truncation'),
      ('interval arithmetic returning trajectory','test_rigid_dat_interval_flag_catches_returning_sdf_arc'),
      ('rigid DAT sphere drop','test_rigid_dat_sphere_drop_penetration_free'),
      ('rigid DAT graph capture','test_rigid_dat_graph_capture_replays_match_eager'),
      ('owned pipeline dependency','test_rigid_dat_requires_owned_pipeline'),
      ('positive query radius','test_rigid_dat_requires_positive_rigid_soft_query_radius'),
    ]
    dump('solvers/vbd/upstream-tests.json',[{'topic':topic,'symbol':name,'source':anchor('newton/tests/test_solver_vbd.py','def '+name+'('),'execution_status':'not_run_in_this_delivery'} for topic,name in tests])
    print({'model_inputs':len(MODEL_ROWS),'diagnostic_plans':len(rows)})

if __name__=='__main__': main()
