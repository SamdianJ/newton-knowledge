"""Read archived evidence; independent geometry/momentum checks, no Newton import."""
from pathlib import Path
import hashlib,json
import numpy as np
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text(encoding='utf8'))
def plain(x):
    if isinstance(x,dict): return {k:plain(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)): return [plain(v) for v in x]
    if hasattr(x,'tolist'): return plain(x.tolist())
    return x
def save(p,x): Path(p).write_text(json.dumps(plain(x),ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def rel(p): return p.relative_to(ROOT).as_posix()
def main():
    p=read(HERE/'protocol.json'); shared=p['shared_criteria']; dt=p['run']['dt_s']; revision=read(HERE/'harness-revisions.json'); excluded=revision['excluded_runs']; allchecks=[]; analyzed=[]; publications=[]; formal=[]
    results=[(f.parent,read(f)) for f in sorted((HERE/'runs').glob('*/result.json')) if f.parent.name not in excluded]
    assert len(results)==8 and all(r['status']=='completed' for _,r in results)
    for case in p['cases']:
        checks=[]; variants=[]; raws={}; metrics={}
        def check(name,actual,expected,passed): checks.append({'name':name,'actual':plain(actual),'expected':plain(expected),'passed':bool(passed)})
        def upper(name,val,limit): check(name,val,{'max':limit},val<=limit)
        for label in ['A','B']:
            selected=sorted([(d,r) for d,r in results if r['case']==case['id'] and r['variant']==label],key=lambda dr:dr[1]['repeat']); assert len(selected)==2 and [r['repeat'] for d,r in selected]==[1,2]
            v=case['variants'][label]; runs=[]
            for directory,r in selected:
                formal.append(r['run_id']); a=dict(np.load(directory/'trajectory.npz')); conf=read(directory/'resolved-config.json'); tag=f"{label} r{r['repeat']}"; n=a['step_contact_valid']; act=n & (a['step_contact_efc_address']>=0); indices=np.flatnonzero(act); detected=np.flatnonzero(n)
                assert len(indices) and len(detected),'Required events absent'
                z=a['body_q'][:,0,2].astype(float); vel=a['body_qd'][:,0,2].astype(float); dist=z[:-1]-.05; first=int(indices[0]); detection=float(a['step_time'][detected[0]]); activation=float(a['step_time'][first]); inactive=n & (np.arange(len(n))<first)
                energy=.5*np.sum(a['body_qd'][:,0,:3].astype(float)**2,axis=1)+.0005*np.sum(a['body_qd'][:,0,3:].astype(float)**2,axis=1)
                met={'detection_time_s':detection,'activation_time_s':activation,'restitution':float(vel[-100:].mean()),'tail_velocity_peak_to_peak_mps':float(np.ptp(vel[-100:])),'final_surface_distance_m':float(z[-1]-.05),'inactive_pre_force_samples':int(inactive.sum()),'inactive_force_max_N':float(max(np.max(np.abs(a['step_qfrc_constraint'][inactive,2]),initial=0),np.max(np.abs(a['step_contact_normal_force'][inactive]),initial=0))),'impulse_residual_Ns':float(abs(vel[-1]-vel[0]-np.sum(a['step_qfrc_constraint'][:,2])*dt)),'geometry_error_m':float(np.max(np.abs(a['step_contact_dist'][n]-dist[n]))),'freeflight_position_error_m':float(np.max(np.abs(z[:first+1]-(.15-a['t'][:first+1])))),'freeflight_velocity_error_mps':float(np.max(np.abs(vel[:first+1]+1))),'max_energy_ratio':float(energy.max()/energy[0]),'off_axis_speed_max':float(np.max(np.abs(a['body_qd'][:,0,[0,1,3,4,5]]))),'peak_normal_force_N':float(a['step_contact_normal_force'].max()),'min_surface_distance_m':float(np.min(z-.05)),'solver_iterations_max':int(a['step_solver_niter'].max()),'actual_timestep_s':float(a['step_native_timestep'][0])}
                check(tag+' all finite',True,True,all(np.isfinite(x).all() for x in a.values())); check(tag+' samples',len(a['t']),801,len(a['t'])==801); check(tag+' installed 809 hashes',read(directory/'installed-source-validation.json'),{'files':809,'changed':[],'missing':[]},read(directory/'installed-source-validation.json')=={'checked_python_files':809,'changed':[],'missing':[]})
                check(tag+' all archive hashes',len(r['files_sha256']),True,all(sha(directory/k)==h for k,h in r['files_sha256'].items())); check(tag+' protocol',r['protocol_sha256'],sha(HERE/'protocol.json'),r['protocol_sha256']==sha(HERE/'protocol.json')); check(tag+' program',r['program_sha256'],sha(HERE/'runner.py'),r['program_sha256']==sha(HERE/'runner.py'))
                check(tag+' native CPU refsafety margin workaround',conf['use_mujoco_cpu'] and conf['refsafe_enabled'] and not conf['zero_margins_for_native_ccd'],True,conf['use_mujoco_cpu'] and conf['refsafe_enabled'] and not conf['zero_margins_for_native_ccd']); upper(tag+' actual dt max error',float(np.max(np.abs(a['step_native_timestep']-dt))),1e-15)
                g=conf['native_geom']; sphere=int(np.flatnonzero(np.array(g['geom_type'])==2)[0]); floor=int(np.flatnonzero(np.array(g['geom_type'])==0)[0])
                for key,expected in [('geom_solref',v['solref']),('geom_margin',v['margin']),('geom_gap',v['gap']),('geom_priority',1),('geom_condim',1),('geom_solimp',p['scene']['solimp'])]: check(tag+' '+key,g[key][sphere],expected,np.allclose(g[key][sphere],expected,rtol=0,atol=2e-8))
                check(tag+' floor solref',g['geom_solref'][floor],[.08,1],np.allclose(g['geom_solref'][floor],[.08,1],atol=2e-8,rtol=0)); check(tag+' imported raw mode',conf['custom']['solref_mode'],[1,1],conf['custom']['solref_mode']==[1,1]); upper(tag+' contact priority solref error',float(np.max(np.abs(a['step_contact_solref'][n]-v['solref']))),2e-8); upper(tag+' contact includemargin error',float(np.max(np.abs(a['step_contact_includemargin'][n]-v['margin']))),2e-8)
                check(tag+' mass',conf['native_body_mass'],[0,1],np.allclose(conf['native_body_mass'],[0,1],rtol=0,atol=1e-10)); upper(tag+' geometry',met['geometry_error_m'],shared['geometry_error_max']); upper(tag+' freeflight position',met['freeflight_position_error_m'],shared['geometry_error_max']); upper(tag+' freeflight velocity',met['freeflight_velocity_error_mps'],shared['freeflight_velocity_error_max']); upper(tag+' impulse',met['impulse_residual_Ns'],shared['impulse_residual_max']); upper(tag+' energy',met['max_energy_ratio'],shared['energy_ratio_max']); upper(tag+' off axis',met['off_axis_speed_max'],shared['off_axis_velocity_abs_max']); check(tag+' nonnegative force',float(a['step_contact_normal_force'].min()),shared['normal_force_min'],a['step_contact_normal_force'].min()>=shared['normal_force_min']); upper(tag+' detection prediction error',abs(detection-case['criteria']['detection_time_s'][label]),shared['event_tolerance_dt']*dt)
                if case['id']=='native_solref_rebound':
                    upper(tag+' tail plateau',met['tail_velocity_peak_to_peak_mps'],case['criteria']['tail_velocity_peak_to_peak_max']); check(tag+' separated outgoing',[met['final_surface_distance_m'],met['restitution']],'>0',met['final_surface_distance_m']>0 and met['restitution']>0)
                    check(tag+' restitution gate',met['restitution'],{'>=':.35} if label=='A' else {'<=':.25},met['restitution']>=case['criteria']['A_restitution_min'] if label=='A' else met['restitution']<=case['criteria']['B_restitution_max'])
                else:
                    upper(tag+' activation prediction error',abs(activation-case['criteria']['activation_time_s']),2*dt)
                    if label=='B': check(tag+' inactive count',met['inactive_pre_force_samples'],{'min':case['criteria']['inactive_samples_B_min']},met['inactive_pre_force_samples']>=case['criteria']['inactive_samples_B_min']); upper(tag+' inactive force',met['inactive_force_max_N'],case['criteria']['inactive_force_abs_max'])
                runs.append({'run_id':r['run_id'],'variant':label,'repeat':r['repeat'],'metrics':met,'raw_file':rel(directory/'trajectory.npz'),'raw_sha256':sha(directory/'trajectory.npz'),'program_sha256':r['program_sha256'],'protocol_sha256':r['protocol_sha256'],'result_file':rel(directory/'result.json'),'config':{'scene':v,'native_options':conf['native_option'],'actual_timestep_s':met['actual_timestep_s'],'native_option_snapshot':'before_first_step','native_geom':g,'refsafe_enabled':conf['refsafe_enabled'],'use_mujoco_cpu':True}}); raws[(label,r['repeat'])]=a; metrics[(label,r['repeat'])]=met
            one,two=raws[(label,1)],raws[(label,2)]
            for k,tol in [('body_q',shared['repeat_position_atol']),('joint_q',shared['repeat_position_atol']),('body_qd',shared['repeat_velocity_atol']),('joint_qd',shared['repeat_velocity_atol'])]: upper(label+' repeat '+k,float(np.max(np.abs(one[k]-two[k]))),tol)
            for k in ['detection_time_s','activation_time_s']: upper(label+' repeat '+k,abs(metrics[(label,1)][k]-metrics[(label,2)][k]),dt)
            runs[0]['reproduction']=runs[1]; runs[0]['label']=('ratio .2' if label=='A' else 'ratio 1') if case['id']=='native_solref_rebound' else ('gap 0 m' if label=='A' else 'gap .04 m'); variants.append(runs[0])
        for rep in [1,2]:
            A,B=metrics[('A',rep)],metrics[('B',rep)]
            if case['id']=='native_solref_rebound': check('restitution intervention r'+str(rep),A['restitution']-B['restitution'],{'min':.2},A['restitution']-B['restitution']>=case['criteria']['restitution_difference_min'])
            else:
                upper('detection advance error r'+str(rep),abs(A['detection_time_s']-B['detection_time_s']-.04),2*dt); upper('activation timing difference r'+str(rep),abs(A['activation_time_s']-B['activation_time_s']),dt)
                upper('gap physical position equivalence r'+str(rep),float(np.max(np.abs(raws[('A',rep)]['body_q']-raws[('B',rep)]['body_q']))),case['criteria']['position_AB_max']); upper('gap physical velocity equivalence r'+str(rep),float(np.max(np.abs(raws[('A',rep)]['body_qd']-raws[('B',rep)]['body_qd']))),case['criteria']['velocity_AB_max'])
        passed=all(c['passed'] for c in checks); allchecks+=checks
        if case['id']=='native_solref_rebound': observation=f"固定 timeconst .02 s，阻尼比 .2 / 1 的实测回弹速度比为 {metrics[('A',1)]['restitution']:.6f} / {metrics[('B',1)]['restitution']:.6f}；该正值 solref 干预同时改变有效刚度。"
        else: observation=f"gap 0 / .04 m 的首次检测为 {metrics[('A',1)]['detection_time_s']:.4f} / {metrics[('B',1)]['detection_time_s']:.4f} s；首次激活均为 {metrics[('A',1)]['activation_time_s']:.4f} s。较大 gap 提供 {metrics[('B',1)]['inactive_pre_force_samples']} 个提前检测但无力样本，A/B 轨迹等价。"
        refs=[{'path':r['path'],'line':r['lines'][0],'commit':p['source_commit'],'sha256':r['sha256'],'url':f"https://github.com/newton-physics/newton/blob/{p['source_commit']}/{r['path']}#L{r['lines'][0]}"} for r in p['source_refs']]
        record={'id':case['id'],'record_id':'lab:'+case['id'],'solver':'mujoco','title':case['title'],'parameter':'solref' if case['id']=='native_solref_rebound' else 'shape_gap shape_margin','physical_acceptance':'passed' if passed else 'failed_criteria','observation':observation,'limitations':p['limitations'],'source_refs':refs,'official_sources':p['official_sources'],'associations':['model:mujoco:mujoco.solref'] if case['id']=='native_solref_rebound' else ['model:mujoco:shape_gap','model:mujoco:shape_margin'],'association_relation':'measures_behavior_of','association_scope':'Supported MJCF authored raw solref ratio A/B; time constant, priority, solimp, condim and backend fixed.' if case['id']=='native_solref_rebound' else 'Only gap varied directly; margin fixed geometric activation reference, not a margin A/B sweep.','variants':variants,'protocol_file':rel(HERE/'protocol.json'),'runner_file':rel(HERE/'runner.py'),'acceptance_results':checks,'plot':'contact/'+case['id']+'.svg','replay':[{'variant':v,'label':variants[i]['label'],'times':raws[(v,1)]['t'][::4].tolist(),'body_q':raws[(v,1)]['body_q'][::4].tolist(),'body_names':['sphere']} for i,v in enumerate(['A','B'])]}
        publications.append(record); analyzed.append({k:v for k,v in record.items() if k!='replay'})
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,axes=plt.subplots(3,1,figsize=(9,8),sharex=True)
        for v in ['A','B']:
            a=raws[(v,1)]; axes[0].plot(a['t'],a['body_q'][:,0,2]-.05,label=v); axes[1].plot(a['t'],a['body_qd'][:,0,2],label=v); axes[2].plot(a['step_time'],a['step_contact_normal_force'],label=v)
            if case['id']=='native_gap_activation': axes[0].axvline(metrics[(v,1)]['detection_time_s'],ls=':',alpha=.7,label=v+' detected')
        for ax in axes: ax.grid(alpha=.25); ax.legend()
        axes[0].set_ylabel('Surface distance (m)'); axes[1].set_ylabel('Vertical velocity (m/s)'); axes[2].set_ylabel('Contact normal force (N)'); axes[2].set_xlabel('Time (s)'); fig.suptitle(case['id']); fig.tight_layout(); fig.savefig(HERE/(case['id']+'.svg')); fig.savefig(HERE/(case['id']+'.png'),dpi=150); plt.close(fig)
    report={'status':'passed' if all(c['passed'] for c in allchecks) else 'failed_criteria','checks':len(allchecks),'passed_checks':sum(c['passed'] for c in allchecks),'analyzer_sha256':sha(__file__),'cases':analyzed,'formal_runs':formal,'excluded_attempts':revision}; save(HERE/'analysis.json',report); save(HERE/'publication.json',{'cases':publications,'formal_runs':formal})
    (HERE/'RESULTS.md').write_text('# Native MuJoCo contact results\n\n'+f"Frozen checks: {report['passed_checks']}/{report['checks']}; {len(formal)} independent formal runs.\n\n"+'\n\n'.join(c['observation'] for c in publications)+'\n\nEight earlier completed attempts are retained as instrumentation-incomplete because their configuration snapshot preceded the first step and lacked the actual per-step timestep. No physical outcome was used to exclude them. New formal runs record actual .0005 s at every step. CUDA driver warning is retained; actual backend is CPU.\n\n'+ '\n'.join('- '+x for x in p['limitations'])+'\n',encoding='utf8')
    print(json.dumps({'status':report['status'],'passed':report['passed_checks'],'checks':report['checks'],'failures':[c for c in allchecks if not c['passed']]},ensure_ascii=False))
if __name__=='__main__': main()
