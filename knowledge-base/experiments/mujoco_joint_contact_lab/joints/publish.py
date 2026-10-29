from pathlib import Path
import json,hashlib
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'manifests/source-lock.json').exists())
def load(p):return json.loads(p.read_text(encoding='utf8'))
def rel(p):return p.relative_to(ROOT).as_posix()
a=load(HERE/'analysis.json');p=load(HERE/'protocol.json');cases=[]
observations={
'mujoco_joint_passive_damping':'初速1rad/s、无驱动时，被动damping从0变2，2s末速度从1降至0.0184623rad/s，动能剩0.03409%；无阻尼对照能量不变。符合含隐式被动阻尼的Euler独立参考。',
'mujoco_joint_armature_inertia':'armature从0增至3，在相同1N·m力矩下原生有效惯量约从1增至4kg·m²，速度和加速度降为约1/4；物理body质量及惯量没有增加。它改变惯量，不是耗散阻尼。',
'mujoco_joint_pd_damping':'固定kp25、目标0.1rad，target_kd从0变10，过冲从0.100001rad降为0，末误差5.50e-5rad。两者驱动力矩和轨迹均吻合独立离散参考；此处只扫描kd，不代表已经扫描kp。',
'mujoco_joint_upper_limit':'上限从0.1移至0.2rad，首次限位反力由0.448s延后至0.632s，末位置随范围平移约0.1rad。最大软穿越0.00607/0.00805rad，末残差约1.10e-4rad；末反力抵消1N·m外力矩，不是硬裁剪到限位。'}
for c in a['cases']:
    variants=[]
    for v in c['variants']:
        one,two=v['runs'];keys=('run_id','metrics','raw_file','raw_sha256','program_sha256','protocol_sha256','result_file');item={k:one[k] for k in keys};item['variant']=v['id'];item['environment']=load(ROOT/one['run']/'environment.json')
        item['config']={'treatment':one['config']['treatment'],'requested':one['config']['requested'],'actual_native_options':one['config']['opt_final'],'actual_native_model':one['config']['mj_model'],'full_config_file':one['run']+'/resolved-config.json','full_config_field':None}
        item['reproduction']={k:two[k] for k in keys};item['reproduction']['checks']=v['repeat_checks'];item['reproduction']['tolerances']={f:{'atol':1e-6,'rtol':1e-6} for f in ('body_q','body_qd','joint_q','joint_qd')};variants.append(item)
    cases.append({'id':c['id'],'record_id':'lab:'+c['id'],'solver':'mujoco','title':c['title'],'parameter':c['parameter'],'experiment_kind':'single_factor','observation':observations[c['id']],'physical_acceptance':c['status'],'variants':variants,'protocol_file':rel(HERE/'protocol.json'),'runner_file':rel(HERE/'runner.py'),'source_refs':c['source_refs'],'associations':['model:mujoco:'+c['parameter']],'association_relation':'measures_behavior_of','association_scope':'直接单因素干预 '+c['parameter']+'；其余导出参数只作固定场景的生效确认，不冒充参数扫描。','limitations':c['limitations'],'plot':c['plot'],'replay':{'time_field':'t','source':'saved raw Newton body/joint trajectory','force_time_field':'force_t','force_state_alignment':'force[n] evaluated at state[n]; state[n+1] is the integration output'},'acceptance_results':{'status':c['status'],'criteria':c['criteria'],'paired_checks':c['paired_checks'],'runs':[{'run_id':r['run_id'],'checks':r['checks'],'status':r['status']} for v in c['variants'] for r in v['runs']]}})
(HERE/'publication.json').write_text(json.dumps({'schema_version':'1.0','group':'joints','formal_runs':a['formal_runs'],'analysis_sha256':hashlib.sha256((HERE/'analysis.json').read_bytes()).hexdigest(),'cases':cases,'excluded_runs':a['excluded_runs']},indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
print(json.dumps({'cases':len(cases),'formal_runs':a['formal_runs']}))
