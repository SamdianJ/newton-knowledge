"""Package analyzed friction evidence without rerunning simulation."""
from pathlib import Path
import hashlib,json
import numpy as np
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'manifests/source-lock.json').exists())
HERE=Path(__file__).resolve().parent
def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rel(p): return Path(p).relative_to(ROOT).as_posix()
def save(p,x): Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
analysis=read(HERE/'analysis.json'); protocol=read(HERE/'protocol.json'); cases=[]
limitations=['仅固定Newton1.7.0 / native MuJoCo3.15.0 CPU单world；GPU、Newton外部contact路径未测。','两组均未通过完整事前物理验收，不能将可观测的摩擦作用标为持续接触机制已验证。','滑动无量纲；扭转系数单位m，输出摩擦力N、扭矩Nm。mj_contactForce为原生诊断，不代表Newton CONTACT_F受支持。','未测静摩擦启滑、滚动condim6、非等priority、显式pair、各向异性、复杂堆叠。','默认geom_gap约.1m使ncon包含分离候选；active efc_address和正法向力必须单独检查。','构造前步长快照为.002s；逐步native_timestep原始记录与正式dt均为.001s。','t≥.05解析参考以测得速度作锚点；全程独立动量平衡不依赖该锚点。']
for case in analysis['cases']:
    slide='sliding' in case['id']; variants=[]; replay=[]
    for v in ('A','B'):
        r=next(x for x in case['runs'] if x['variant']==v and x['repeat']==1); rr=next(x for x in case['runs'] if x['variant']==v and x['repeat']==2)
        d=ROOT/r['directory']; d2=ROOT/rr['directory']; result=read(d/'result.json'); result2=read(d2/'result.json'); cfg=read(d/'resolved-config.json'); env=read(d/'environment.json')
        variants.append(dict(variant=v,label=('mu = '+str(cfg['treatment']['body_mu']) if slide else 'condim = '+str(cfg['treatment']['body_condim'])),run_id=r['run_id'],metrics=r['metrics'],raw_file=rel(d/'trajectory.npz'),raw_sha256=sha(d/'trajectory.npz'),program_sha256=sha(d/'runner.py'),protocol_sha256=sha(d/'protocol.json'),result_file=rel(d/'result.json'),config=dict(treatment=cfg['treatment'],backend=cfg['backend'],options=cfg['options'],snapshot_phase=cfg['snapshot_phase'],actual_step_timestep_s=.001,geom_friction=cfg['geom_friction'],geom_condim=cfg['geom_condim'],geom_priority=cfg['geom_priority'],resolved_config_file=rel(d/'resolved-config.json')),environment={k:env[k] for k in ('python','packages','device','source_commit')},reproduction=dict(run_id=rr['run_id'],raw_file=rel(d2/'trajectory.npz'),raw_sha256=sha(d2/'trajectory.npz'),result_file=rel(d2/'result.json'),program_sha256=sha(d2/'runner.py'),protocol_sha256=sha(d2/'protocol.json'),metrics=rr['metrics'])))
        with np.load(d/'trajectory.npz') as a: replay.append(dict(variant=v,label=v,times=a['t'].tolist(),body_q=a['body_q'].tolist(),body_names=['specimen']))
    am,bm=variants[0]['metrics'],variants[1]['metrics']
    negatives=[x for r in case['runs'] if r['repeat']==1 for x in r['checks'] if x['kind']=='physical' and not x['passed']]
    failure_text='；'.join(f"{x['name']}={x['value']:.6g}未达{x['operator']}{x['limit']:.6g}" for x in negatives)
    if slide:
        observation=f"μ={variants[0]['config']['treatment']['body_mu']}/{variants[1]['config']['treatment']['body_mu']}，末vx={am['final_vx_m_s']:.6f}/{bm['final_vx_m_s']:.6f}m/s，速度分离{am['final_vx_m_s']-bm['final_vx_m_s']:.6f}m/s；实际积分切向/法向比={am['settled_contact_tangential_normal_ratio']:.6g}/{bm['settled_contact_tangential_normal_ratio']:.6g}，完整线冲量误差≤{max(am['linear_impulse_balance_max_error_Ns'],bm['linear_impulse_balance_max_error_Ns']):.3g}Ns。"
        associations=['model:mujoco:shape_material_mu']; scope='唯一直接干预body shape_material_mu，ground μ=0且priority相同；记录真实max混合。效应和冲量吻合不替代持续承载门槛。'
    else:
        observation=f"固定扭转系数{variants[1]['config']['geom_friction'][1][1]:.6g}m，仅改condim3/4，末ωz={am['final_omega_z_rad_s']:.6f}/{bm['final_omega_z_rad_s']:.6f}rad/s；A扭矩0，B积分扭矩/法向比={bm['settled_contact_torsional_normal_ratio_m']:.6g}m、角冲量误差{bm['angular_impulse_balance_max_error_Nms']:.3g}Nms。"
        associations=['model:mujoco:mujoco.condim','model:mujoco:shape_material_mu_torsional']; scope='唯一直接干预body mujoco.condim=3/4；shape_material_mu_torsional为固定机制关联，并未扫描其数值，不能晋级为该参数单因素覆盖。'
    observation+=f"t≥.05有效承载比例{am['settled_contact_present_fraction']:.2%}/{bm['settled_contact_present_fraction']:.2%}；完整物理验收{case['physical_acceptance']}。"+(('未通过：'+failure_text+'。') if negatives else '各冻结物理门槛通过。')
    prefix={'friction':'原始高速度/较高摩擦边界','friction_stable':'提高impratio假设对照','friction_low_regime':'低摩擦/低速区域'}[HERE.name]
    title=prefix+'：'+('滑动μ单因素' if slide else 'condim3/4扭转机制')
    if HERE.name=='friction_stable': observation='公共impratio仅由1改为1000，组内对照不变。'+observation+' 提高该值未消除间歇承载；目录stable只是设计时名称，不表示稳定效果。'
    if HERE.name=='friction_low_regime': observation='新低量级场景，不能推论原高速/较高摩擦条件已解决。'+observation
    d=ROOT/next(r for r in case['runs'] if r['variant']=='A' and r['repeat']==1)['directory']
    cases.append(dict(id=case['id'],record_id='lab:'+case['id'],solver='mujoco',title=title,parameter='shape_material_mu' if slide else 'mujoco.condim shape_material_mu_torsional',experiment_kind='mechanism',observation=observation,physical_acceptance=case['physical_acceptance'],evidence_validity=case['evidence_validity'],limitations=limitations if HERE.name!='friction_low_regime' else [x for x in limitations if '两组均未通过' not in x],association_scope=scope,associations=associations,association_relation='measures_behavior_of',association_roles=[{'id':x,'role':'direct_intervention' if i==0 else 'fixed_mechanism_association'} for i,x in enumerate(associations)],source_refs=case['source_refs'],native_source_refs=protocol['native_source_refs'],variants=variants,protocol_file=rel(d/'protocol.json'),runner_file=rel(d/'runner.py'),replay=replay,plot=case['plot'],sample_kind='time',acceptance_results={'runs':[{'run_id':r['run_id'],'physical_acceptance':r['physical_acceptance'],'evidence_validity':r['evidence_validity'],'physical_checks':[x for x in r['checks'] if x['kind']=='physical'],'full_checks_file':rel(HERE/'analysis.json')} for r in case['runs']],'pair_and_repeat':case['checks'],'full_config_diff':case['config_diff']}))
evidence=dict(analysis['evidence_files'])
for f in [HERE/'analysis.json',HERE/'publish.py',HERE/'RESULTS.md',HERE/'REPRODUCE.md',*HERE.glob('*.svg'),*HERE.glob('*.png')]:
    if f.is_file(): evidence[rel(f)]=sha(f)
save(HERE/'publication.json',dict(schema_version='1.0',group=HERE.name,formal_runs=8,status=analysis['status'],protocol_sha256=sha(HERE/'protocol.json'),analysis_sha256=sha(HERE/'analysis.json'),cases=cases,evidence_files=evidence,excluded_or_failed_runs=analysis['excluded_or_failed_runs']))
print('Published',len(cases),'cases',len(evidence),'evidence files')
