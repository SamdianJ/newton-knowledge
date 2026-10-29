"""Independent scalar references; no Newton or MuJoCo imports."""
from pathlib import Path
import hashlib,json
import numpy as np
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'manifests/source-lock.json').exists())
def load(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
def mx(a):return float(np.max(np.abs(a))) if np.size(a) else 0.
def reference(cfg,h,N):
    I=1.+cfg['armature'];q=np.zeros(N+1);v=np.zeros(N+1);v[0]=cfg['initial_v'];act=np.zeros(N);pas=np.zeros(N)
    for n in range(N):
        act[n]=cfg['kp']*(cfg['qref']-q[n])-cfg['kd']*v[n] if cfg['mode']=='POSITION' else 0.
        pas[n]=-cfg['damping']*v[n]
        v[n+1]=(I*v[n]+h*(cfg['external_tau']+act[n]))/(I+h*cfg['damping'])
        q[n+1]=q[n]+h*v[n+1]
    return {'q':q,'v':v,'tau_act':act,'tau_passive':pas}
def plot(case,arrays,refs):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matplotlib.rcParams['svg.hashsalt']='mujoco-joints-v1'
    fig,axes=plt.subplots(2,2,figsize=(11.5,6.5),constrained_layout=True)
    for variant,color in (('A','tab:blue'),('B','tab:orange')):
        d=arrays[(variant,1)];r=refs[(variant,1)];t=d['t'];cfg={**case['base'],**case['variants'][variant]}
        label=variant+': '+', '.join(f'{k} = {v}' for k,v in case['variants'][variant].items())
        axes[0,0].plot(t,d['joint_q'][:,0],color=color,label=label)
        axes[0,1].plot(t,d['joint_qd'][:,0],color=color,label=variant)
        f=d['qfrc_applied'][:,0] if case['id'].endswith('armature_inertia') else d['qfrc_passive'][:,0]+d['qfrc_actuator'][:,0]+d['qfrc_constraint'][:,0]
        axes[1,0].plot(d['force_t'],f,color=color,label=variant)
        if case['id'].endswith('upper_limit'):
            axes[0,0].axhline(cfg['limit_upper'],color=color,linestyle=':',alpha=.6)
            axes[1,1].plot(t,d['joint_q'][:,0]-cfg['limit_upper'],color=color,label=variant)
        else:
            axes[0,0].plot(t,r['q'],color=color,linestyle=':',alpha=.5)
            axes[1,1].plot(t,np.abs(d['joint_q'][:,0]-r['q']),color=color,label=variant)
    for ax,label in zip(axes.flat,['Angle [rad]','Velocity [rad/s]','External torque [N m]' if case['id'].endswith('armature_inertia') else 'Response torque [N m]','Angle minus upper limit [rad]' if case['id'].endswith('upper_limit') else 'Angle reference error [rad]']):
        ax.set_xlabel('Time [s]');ax.set_ylabel(label);ax.grid(alpha=.25);ax.legend(fontsize=8)
    fig.suptitle(case['id']+' | repeat 1; both repeats checked')
    for ext in ('png','svg'):fig.savefig(HERE/(case['id']+'.'+ext),dpi=140,bbox_inches='tight',metadata={'Date':None} if ext=='svg' else None)
    plt.close(fig);return 'joints/'+case['id']+'.svg'
def main():
    p=load(HERE/'protocol.json');ph,rh=sha(HERE/'protocol.json'),sha(HERE/'runner.py');records=[];excluded=[]
    for f in sorted((HERE/'runs').glob('*/result.json')):
        r=load(f);r['path']=f.parent
        if r['status']=='completed' and r['protocol_sha256']==ph and r['runner_sha256']==rh:records.append(r)
        else:excluded.append({'run_id':r['run_id'],'status':r['status'],'error':r.get('error'),'runner_sha256':r['runner_sha256']})
    cases=[];allchecks=[]
    for c in p['cases']:
        variants=[];arrays={};refs={};paired=[]
        for var,treat in c['variants'].items():
            runs=sorted([r for r in records if r['case']==c['id'] and r['variant']==var],key=lambda r:r['repeat'])
            if [r['repeat'] for r in runs]!=[1,2]:raise ValueError('Require exactly2 repeats per frozen runner setting')
            outs=[]
            for r in runs:
                path=r['path'];d=dict(np.load(path/'trajectory.npz',allow_pickle=False));actual=load(path/'resolved-config.json');cfg={**c['base'],**treat};m=actual['mj_model'];h=p['run']['dt_s'];N=p['run']['steps'];I=1+cfg['armature'];ref=reference(cfg,h,N);arrays[(var,r['repeat'])]=d;refs[(var,r['repeat'])]=ref
                np.savez_compressed(HERE/(r['run_id']+'-reference.npz'),**ref)
                checks=[];metrics={}
                def check(name,value,passed,expected=None):checks.append({'name':name,'actual':value,'expected':expected,'passed':bool(passed)})
                def upper(name,value):
                    limit=p['common_criteria'].get(name,c['criteria'].get(name));metrics[name]=float(value);check(name,float(value),value<=limit,{'max':limit})
                def lower(name,value):
                    limit=c['criteria'][name];metrics[name]=float(value);check(name,float(value),value>=limit,{'min':limit})
                check('hashes',True,all(sha(path/k)==v for k,v in r['files_sha256'].items()))
                source=load(path/'installed-source-validation.json');check('809_locked_sources',source['checked_python_files'],source['checked_python_files']==809 and not source['missing'] and not source['changed'])
                check('all_arrays_finite',True,all(np.isfinite(v).all() for v in d.values()))
                check('sample_counts',[len(d['t']),len(d['force_t'])],len(d['t'])==1001 and len(d['force_t'])==1000)
                check('actual_backend_options',actual['opt_final'],actual['use_mujoco_cpu'] and actual['update_data_interval']==0 and actual['opt_final']['integrator']==0 and actual['opt_final']['solver']==2 and actual['opt_final']['iterations']==100 and actual['opt_final']['tolerance']==1e-10 and actual['opt_final']['timestep']==h)
                fields=(np.allclose(m['dof_damping'],[cfg['damping']],atol=1e-8) and np.allclose(m['dof_armature'],[cfg['armature']],atol=1e-8) and np.allclose(m['dof_frictionloss'],[0.],atol=1e-8) and np.allclose(m['body_mass'][-1],1.) and np.allclose(m['body_inertia'][-1],[1,1,1]) and np.allclose(m['body_ipos'][-1],[0,0,0]))
                if cfg['mode']=='POSITION':
                    fields &= actual['counts']['nu']==1 and np.allclose(np.asarray(m['actuator_gainprm'])[:,0],[cfg['kp']]) and np.allclose(np.asarray(m['actuator_biasprm'])[:,:3],[[0,-cfg['kp'],-cfg['kd']]]) and np.allclose(m['jnt_actfrcrange'],[[-100,100]])
                else:fields &= actual['counts']['nu']==0
                limited=c['id'].endswith('upper_limit');fields &= bool(m['jnt_limited'][0])==limited
                if limited:
                    fields &= np.allclose(m['jnt_range'],[[cfg['limit_lower'],cfg['limit_upper']]],atol=1e-7) and np.allclose(m['jnt_margin'],[0.])
                    invw=float(m['dof_invweight0'][0]);dmax=float(m['jnt_solimp'][0][1]);factor=invw*(1-dmax)
                    direct_ke=cfg['limit_ke']*factor;direct_kd=cfg['limit_kd']*factor
                    expected_solref=[2/direct_kd,direct_kd/(2*np.sqrt(direct_ke))]
                    fields &= np.allclose(m['jnt_solref'],[expected_solref],atol=1e-7,rtol=1e-6) and np.allclose(m['jnt_solimp'],[[.9,.95,.001,.5,2]],atol=1e-7)
                check('all_actual_fields_match',bool(fields),fields)
                check('initial_conditions',[float(d['joint_q'][0,0]),float(d['joint_qd'][0,0])],mx(d['joint_q'][0])==0 and float(d['joint_qd'][0,0])==cfg['initial_v'])
                upper('native_vs_newton_q_max_abs_rad',mx(d['joint_q'][:,0]-d['native_qpos'][:,0]));upper('native_vs_newton_v_max_abs_rad_s',mx(d['joint_qd'][:,0]-d['native_qvel'][:,0]));upper('anchor_max_norm_m',float(np.linalg.norm(d['body_q'][:,0,:3],axis=1).max()));upper('quat_norm_error_max',mx(np.linalg.norm(d['body_q'][:,0,3:],axis=1)-1))
                check('warnings_all_zero',int(d['warning_number'].max()),int(d['warning_number'].max())==0)
                q=d['joint_q'][:,0];v=d['joint_qd'][:,0];tor=d['qfrc_constraint'][:,0]
                end=N+1
                if limited:
                    active=np.flatnonzero(np.abs(tor)>1e-6);expected=np.flatnonzero(ref['q'][:-1]>=cfg['limit_upper'])
                    check('limit_activated',int(len(active)),len(active)>0)
                    first=int(active[0]) if len(active) else N;pred=int(expected[0]);end=first+1
                    metrics['first_constraint_time_s']=first*h
                    upper('first_constraint_time_error_max_s',abs(first-pred)*h)
                    upper('peak_upper_violation_max_rad',max(0,float(q.max()-cfg['limit_upper'])))
                    pen=float(q[-250:].mean()-cfg['limit_upper']);lower('tail_mean_violation_min_rad',pen);upper('tail_mean_violation_max_rad',pen)
                    upper('tail_speed_max_abs_rad_s',mx(v[-250:]));upper('tail_force_balance_max_abs_Nm',mx(tor[-250:]+cfg['external_tau']))
                    metrics['tail_mean_position_rad']=float(q[-250:].mean());metrics['tail_mean_constraint_torque_Nm']=float(tor[-250:].mean())
                upper('q_reference_max_abs_rad',mx(q[:end]-ref['q'][:end]));upper('v_reference_max_abs_rad_s',mx(v[:end]-ref['v'][:end]))
                force_error=max(mx(d['qfrc_passive'][:,0]-(-cfg['damping']*d['native_qvel'][:-1,0])),mx(d['qfrc_applied'][:,0]-cfg['external_tau']))
                if not limited:force_error=max(force_error,mx(d['qfrc_actuator'][:,0]-ref['tau_act']),mx(d['qfrc_passive'][:,0]-ref['tau_passive']))
                upper('force_reference_max_abs_Nm',force_error)
                metrics.update(final_q_rad=float(q[-1]),final_v_rad_s=float(v[-1]),max_native_iterations=int(d['solver_niter'].max()),effective_inertia_kg_m2=float(d['native_mass_matrix'][0,0,0]))
                if c['id'].endswith('passive_damping'):
                    E=.5*I*v*v;metrics['final_energy_ratio']=float(E[-1]/E[0]);upper('energy_positive_increment_max_J',max(0.,float(np.diff(E).max())))
                    if var=='A':upper('A_final_energy_relative_error_max',abs(float(E[-1]/E[0])-1))
                    else:upper('B_final_energy_ratio_max',float(E[-1]/E[0]))
                    metrics['continuous_velocity_max_error_rad_s']=mx(v-cfg['initial_v']*np.exp(-cfg['damping']*d['t']/I))
                elif c['id'].endswith('armature_inertia'):
                    upper('effective_inertia_max_abs_error_kg_m2',mx(d['native_mass_matrix'][:,0,0]-I));metrics['mean_acceleration_rad_s2']=float(d['qacc'][:,0].mean())
                elif c['id'].endswith('pd_damping'):
                    overshoot=max(0.,float(q.max()-cfg['qref']));upper(var+'_overshoot_max_rad',overshoot)
                    if var=='A':lower('A_overshoot_min_rad',overshoot)
                    else:upper('B_endpoint_error_max_rad',abs(float(q[-1]-cfg['qref'])));upper('B_endpoint_speed_max_rad_s',abs(float(v[-1])))
                    lower('minimum_effort_margin_Nm',100-mx(d['qfrc_actuator']))
                outs.append({'run_id':r['run_id'],'run':path.relative_to(ROOT).as_posix(),'repeat':r['repeat'],'status':'passed' if all(x['passed'] for x in checks) else 'failed_criteria','metrics':metrics,'checks':checks,'config':actual,'raw_file':(path/'trajectory.npz').relative_to(ROOT).as_posix(),'raw_sha256':sha(path/'trajectory.npz'),'program_sha256':rh,'protocol_sha256':ph,'result_file':(path/'result.json').relative_to(ROOT).as_posix()});allchecks+=checks
            repeat=[]
            for f in ('body_q','body_qd','joint_q','joint_qd'):
                a,b=arrays[(var,1)][f],arrays[(var,2)][f];repeat.append({'name':'repeat_'+f,'max_abs':mx(a-b),'passed':bool(np.allclose(a,b,atol=1e-6,rtol=1e-6))})
            allchecks+=repeat;variants.append({'id':var,'runs':outs,'repeat_checks':repeat})
        for rep in (1,2):
            am,bm=[v['runs'][rep-1]['metrics'] for v in variants]
            def pair(name,value,mincheck=False):
                limit=c['criteria'][name];paired.append({'name':name,'repeat':rep,'actual':float(value),'limit':limit,'passed':bool(value>=limit if mincheck else value<=limit)})
            if c['id'].endswith('passive_damping'):pair('B_to_A_final_speed_ratio_max',bm['final_v_rad_s']/am['final_v_rad_s'])
            elif c['id'].endswith('armature_inertia'):
                pair('B_to_A_speed_ratio_error_from_quarter_max',abs(bm['final_v_rad_s']/am['final_v_rad_s']-.25));pair('B_to_A_acceleration_ratio_error_from_quarter_max',abs(bm['mean_acceleration_rad_s2']/am['mean_acceleration_rad_s2']-.25))
            elif c['id'].endswith('upper_limit'):
                pair('B_minus_A_plateau_shift_error_from_0p1_max_rad',abs((bm['tail_mean_position_rad']-am['tail_mean_position_rad'])-.1));delay=bm['first_constraint_time_s']-am['first_constraint_time_s'];pair('B_minus_A_onset_delay_min_s',delay,True);pair('B_minus_A_onset_delay_max_s',delay)
        allchecks+=paired;passed=all(r['status']=='passed' for v in variants for r in v['runs']) and all(x['passed'] for x in paired) and all(x['passed'] for v in variants for x in v['repeat_checks'])
        cases.append({'id':c['id'],'title':c['title'],'parameter':c['parameter'],'status':'passed' if passed else 'failed_criteria','variants':variants,'paired_checks':paired,'criteria':{**p['common_criteria'],**c['criteria']},'plot':plot(c,arrays,refs),'limitations':p['limitations'],'source_refs':p['source_refs'],'interpretation':c['interpretation'] if 'interpretation' in c else c['reference_scope']})
    out={'status':'passed' if all(c['status']=='passed' for c in cases) else 'completed_with_failed_criteria','formal_runs':len(records),'protocol_sha256':ph,'runner_sha256':rh,'analyzer_sha256':sha(Path(__file__)),'passed_checks':sum(x['passed'] for x in allchecks),'failed_checks':sum(not x['passed'] for x in allchecks),'cases':cases,'excluded_runs':excluded}
    save(HERE/'analysis.json',out);print(json.dumps({k:out[k] for k in ('status','formal_runs','passed_checks','failed_checks')}))
if __name__=='__main__':main()
