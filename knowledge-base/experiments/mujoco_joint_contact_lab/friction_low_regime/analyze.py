"""Read-only scoring of frozen native friction runs; no physics is executed."""
from pathlib import Path
import hashlib, json, sys
import numpy as np
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'manifests/source-lock.json').exists())
HERE=Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def clean(x):
    if hasattr(x,'tolist'): return clean(x.tolist())
    if isinstance(x,dict): return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)): return [clean(v) for v in x]
    return x
def save(p,x): Path(p).write_text(json.dumps(clean(x),ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def rel(p): return Path(p).relative_to(ROOT).as_posix()
def diff(a,b,p=''):
    if isinstance(a,dict) and isinstance(b,dict):
        return sum((diff(a.get(k),b.get(k),p+'.'+k if p else k) for k in sorted(set(a)|set(b))),[])
    return [] if a==b else [{'path':p,'A':a,'B':b}]
def rot(q):
    q=np.asarray(q,float); q=q/np.linalg.norm(q,axis=-1,keepdims=True); x,y,z,w=q.T
    return np.stack([1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w),2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w),2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)],axis=-1).reshape(-1,3,3)

def score(out,p,c):
    result=read(out/'result.json'); cfg=read(out/'resolved-config.json'); a=dict(np.load(out/'trajectory.npz')); checks=[]; metrics={}
    def check(name,value,limit,op='<=',kind='physical'):
        value=clean(value); passed={'<=':lambda:value<=limit,'>=':lambda:value>=limit,'==':lambda:value==limit}[op]()
        checks.append(dict(name=name,value=value,operator=op,limit=limit,passed=bool(passed),kind=kind))
    check('completed',result['status'],'completed','==','evidence')
    for file,h in result['files_sha256'].items(): check('hash:'+file,sha(out/file),h,'==','evidence')
    check('protocol_sha256',sha(out/'protocol.json'),sha(HERE/'protocol.json'),'==','evidence')
    check('program_sha256',sha(out/'runner.py'),result['runner_sha256'],'==','evidence')
    check('raw_sha256',sha(out/'trajectory.npz'),result['raw_sha256'],'==','evidence')
    source=read(out/'installed-source-validation.json')
    check('source_count',source['checked_python_files'],809,'==','evidence'); check('source_mismatches',source['mismatches'],[],'==','evidence')
    check('source_all_equal',source['expected']==source['actual'],True,'==','evidence')
    check('samples',len(a['t']),c['steps']+1,'==','evidence'); dt=p['run']['dt_s']; v=result['variant']; common=p['common_criteria']; crit=c['criteria']; choice=c['variants'][v]
    check('time_spacing',float(np.max(abs(np.diff(a['t'])-dt))),1e-12,kind='evidence')
    check('native_timestep',float(np.max(abs(a['native_timestep']-dt))),1e-12,kind='evidence')
    check('finite_all',all(np.isfinite(x).all() for x in a.values()),True,'==','evidence')
    for k in ('solver','integrator','cone','jacobian','iterations','tolerance','ls_iterations','impratio'): check('option:'+k,cfg['options'][k],p['solver'][k],'==','evidence')
    check('backend',cfg['backend'],{'use_mujoco_cpu':True,'use_mujoco_contacts':True,'update_data_interval':1},'==','evidence')
    dg,gg=cfg['dynamic_geom'],cfg['ground_geom']
    check('body_mass',float(abs(cfg['body_mass'][cfg['geom_bodyid'][dg]]-p['common_scene']['mass_kg'])),1e-7,kind='evidence')
    check('body_principal_inertia',float(np.max(abs(np.sort(cfg['body_inertia'][cfg['geom_bodyid'][dg]])-np.sort(c['inertia_diagonal_kg_m2'])))),1e-7,kind='evidence')
    check('newton_inertia',float(np.max(abs(np.asarray(cfg['newton_body_inertia'])[0]-np.diag(c['inertia_diagonal_kg_m2'])))),1e-7,kind='evidence')
    check('body_COM',float(np.max(abs(np.asarray(cfg['newton_body_com'])[0]-p['common_scene']['com_m']))),1e-8,kind='evidence')
    check('initial_velocity',float(np.max(abs(a['body_qd'][0,0]-c['initial_velocity_world']))),1e-7,kind='evidence')
    initial_height=c.get('radius_m',c.get('half_extents_m',[0,0,0])[2])-p['common_scene']['initial_penetration_m']
    check('initial_position',float(np.max(abs(a['body_q'][0,0,:3]-[0,0,initial_height]))),1e-8,kind='evidence')
    check('initial_orientation',float(np.max(abs(a['body_q'][0,0,3:]-p['common_scene']['initial_quaternion_xyzw']))),1e-8,kind='evidence')
    check('gravity',float(np.max(abs(np.asarray(cfg['options']['gravity'])-p['common_scene']['gravity_m_s2']))),1e-6,kind='evidence')
    check('dynamic_geom_friction',float(np.max(abs(np.asarray(cfg['geom_friction'][dg])-[choice['body_mu'],c['body_mu_torsional_m'],c['body_mu_rolling_m']]))),1e-7,kind='evidence')
    check('ground_geom_friction',cfg['geom_friction'][gg],[0,0,0],'==','evidence')
    check('actual_geom_dim_body',cfg['geom_condim'][dg],choice['body_condim'],'==','evidence')
    check('actual_geom_dim_ground',cfg['geom_condim'][gg],3,'==','evidence')
    check('actual_margin',float(np.max(abs(np.asarray(cfg['geom_margin'])))),0.,kind='evidence')
    check('geom_priorities',cfg['geom_priority'],[0,0],'==','evidence')
    for k in ('dof_damping','dof_armature','dof_frictionloss'): check(k,float(np.max(abs(np.asarray(cfg[k])))),0.,kind='evidence')
    for k,expected in [('geom_solref',p['common_scene']['raw_solref']),('geom_solimp',p['common_scene']['raw_solimp'])]: check(k,float(np.max(abs(np.array(cfg[k])-expected))),1e-7,kind='evidence')
    check('geom_solmix',cfg['geom_solmix'],[1,1],'==','evidence')
    mask=np.arange(16)[None,:]<a['ncon'][:,None]; active=mask & (a['contact_efc_address']>=0)
    target=np.maximum(np.max(np.asarray(cfg['geom_friction']),axis=0)[[0,0,1,2,2]],1e-5)
    check('contact_friction',float(np.max(abs(a['contact_friction'][mask]-target))),common['contact_friction_abs_error'],kind='evidence')
    check('contact_dim',bool(np.all(a['contact_dim'][mask]==choice['body_condim'])),True,'==','evidence')
    pairs=a['contact_geom'][mask]; check('contact_pair',bool(np.all(np.sort(pairs,axis=1)==sorted([dg,gg]))),True,'==','evidence')
    check('contact_exists',int(mask.sum()),1,'>=','evidence')
    q=a['body_q'][:,0].astype(float); vel=a['body_qd'][:,0].astype(float); R=rot(q[:,3:]); wlocal=np.einsum('nji,nj->ni',R,vel[:,3:])
    kinetic=.5*np.sum(vel[:,:3]**2,axis=1)+.5*np.sum(wlocal*wlocal*np.array(c['inertia_diagonal_kg_m2']),axis=1)
    force=a['world_contact_force']; torque=a['world_contact_torque']; t=a['t']; settled=t[:-1]>=p['run']['settled_analysis_starts_s']-1e-12; anchor=int(round(p['run']['settled_analysis_starts_s']/dt)); tail=t>=t[anchor]-1e-12
    normal=(a['contact_wrench'][:,:,0]*active).sum(axis=1)
    tangent=(np.linalg.norm(a['contact_wrench'][:,:,1:3],axis=2)*active).sum(axis=1)
    spin=(abs(a['contact_wrench'][:,:,3])*active).sum(axis=1)
    impulse=dt*np.cumsum(force+np.array([0,0,-9.81]),axis=0)
    m=dict(final_vx_m_s=vel[-1,0],final_omega_z_rad_s=vel[-1,5],linear_impulse_balance_max_error_Ns=float(np.max(abs(vel[1:,:3]-vel[0,:3]-impulse))),settled_contact_present_fraction=float(np.mean(active[settled].any(axis=1))),settled_positive_normal_force_fraction=float(np.mean(normal[settled]>0)),settled_mean_normal_force_N=float(np.mean(normal[settled])),settled_mean_normal_force_relative_error=float(abs(np.mean(normal[settled])-9.81)/9.81),max_penetration_m=float(max(0,-a['contact_dist'][mask].min())),lateral_speed_max_m_s=float(np.max(abs(vel[:,1]))) if c['shape']=='box' else float(np.max(np.linalg.norm(vel[:,:2],axis=1))),height_deviation_from_initial_max_m=float(np.max(abs(q[:,2]-q[0,2]))),kinetic_energy_max_positive_step_J=float(max(0,np.max(np.diff(kinetic)))),integrated_tangential_impulse_Ns=float(dt*tangent.sum()),integrated_torsion_impulse_Nms=float(dt*spin.sum()),contact_count_min=int(a['ncon'].min()),contact_count_max=int(a['ncon'].max()),solver_iterations_max=int(a['solver_niter'].max()),native_warning_count=int(a['warning_number'].max()),settled_contact_tangential_normal_ratio=float(tangent[settled].sum()/normal[settled].sum()),settled_contact_torsional_normal_ratio_m=float(spin[settled].sum()/normal[settled].sum()))
    for key,limit in [('linear_impulse_balance_max_error_Ns',common['linear_impulse_balance_max_error_Ns']),('settled_mean_normal_force_relative_error',common['settled_mean_normal_force_relative_error_max']),('max_penetration_m',common['max_penetration_m'])]: check(key,m[key],limit)
    for key in ('settled_contact_present_fraction','settled_positive_normal_force_fraction'): check(key,m[key],common[key+'_min'],'>=')
    for key in ('lateral_speed_max_m_s','height_deviation_from_initial_max_m','kinetic_energy_max_positive_step_J'): check(key,m[key],crit[key])
    if c['shape']=='box':
        reference=vel[anchor,0]-choice['body_mu']*9.81*(t-t[anchor])
        m.update(analytic_sliding_velocity_max_error_m_s=float(np.max(abs(vel[tail,0]-reference[tail]))),contact_force_ratio_abs_error=abs(m['settled_contact_tangential_normal_ratio']-choice['body_mu']),minimum_sliding_speed_m_s=float(vel[:,0].min()),tilt_from_vertical_max_rad=float(np.arccos(np.clip(R[:,2,2],-1,1)).max()))
        for k in ('analytic_sliding_velocity_max_error_m_s','contact_force_ratio_abs_error','tilt_from_vertical_max_rad'): check(k,m[k],crit[k])
        check('minimum_sliding_speed_m_s',m['minimum_sliding_speed_m_s'],crit['minimum_sliding_speed_m_s'],'>=')
    else:
        reference=vel[anchor,5]-(c['body_mu_torsional_m']*9.81/c['inertia_diagonal_kg_m2'][2] if v=='B' else 0.)*(t-t[anchor])
        m.update(analytic_spin_velocity_max_error_rad_s=float(np.max(abs(vel[tail,5]-reference[tail]))),spin_max_change_rad_s=float(np.max(abs(vel[:,5]-vel[0,5]))),torsion_max_abs_torque_Nm=float(spin.max()),torsion_ratio_abs_error_m=abs(m['settled_contact_torsional_normal_ratio_m']-c['body_mu_torsional_m']),minimum_spin_speed_rad_s=float(vel[:,5].min()),off_axis_angular_speed_max_rad_s=float(np.linalg.norm(vel[:,3:5],axis=1).max()),angular_impulse_balance_max_error_Nms=float(np.max(abs(c['inertia_diagonal_kg_m2'][2]*(vel[1:,5]-vel[0,5])-dt*np.cumsum(torque[:,2])))))
        for k in ('analytic_spin_velocity_max_error_rad_s','off_axis_angular_speed_max_rad_s','angular_impulse_balance_max_error_Nms'): check(k,m[k],crit[k])
        check('minimum_spin_speed_rad_s',m['minimum_spin_speed_rad_s'],crit['minimum_spin_speed_rad_s'],'>=')
        if v=='A': check('spin_A_max_change_rad_s',m['spin_max_change_rad_s'],crit['spin_A_max_change_rad_s']); check('torsion_A_max_abs_torque_Nm',m['torsion_max_abs_torque_Nm'],crit['torsion_A_max_abs_torque_Nm'])
        else: check('torsion_B_ratio_abs_error_m',m['torsion_ratio_abs_error_m'],crit['torsion_B_ratio_abs_error_m'])
        check('single_point_contact',int(a['ncon'].max()),1,'==','evidence')
    # Reconstruct world wrench independently from raw rows, avoiding stored aggregates.
    F=np.zeros_like(force); T=np.zeros_like(torque)
    for n,k in np.argwhere(mask):
        sign=1 if a['contact_geom'][n,k,1]==dg else -1
        f=sign*np.matmul(a['contact_frame'][n,k].T,a['contact_wrench'][n,k,:3]); tau=sign*np.matmul(a['contact_frame'][n,k].T,a['contact_wrench'][n,k,3:])
        F[n]+=f; T[n]+=tau+np.cross(a['contact_pos'][n,k]-q[n,:3],f)
    check('world_force_reconstruction',float(abs(F-force).max()),1e-12,kind='evidence'); check('world_torque_reconstruction',float(abs(T-torque).max()),1e-12,kind='evidence')
    m['first_normal_force_N']=float(normal[0])
    m['maximum_vertical_speed_m_s']=float(np.max(abs(vel[:,2])))
    if 'native_efc_R' in a:
        errors_R=[]; errors_force=[]; errors_J=[]; errors_mu=[]
        for n,k in np.argwhere(active):
            start=int(a['contact_efc_address'][n,k]); dim=int(a['contact_dim'][n,k]); Rn=a['native_efc_R'][n,start]; fr=a['contact_friction'][n,k]
            expected=np.r_[Rn,Rn/p['solver']['impratio'],Rn/p['solver']['impratio']]
            if dim==4: expected=np.r_[expected,Rn/p['solver']['impratio']*fr[0]**2/fr[2]**2]
            errors_R.append(float(np.max(abs(a['native_efc_R'][n,start:start+dim]-expected)/np.maximum(abs(expected),1e-30))))
            errors_force.append(float(np.max(abs(a['native_efc_force'][n,start:start+dim]-a['contact_wrench'][n,k,:dim]))))
            errors_mu.append(abs(a['native_contact_regularized_mu'][n,k]-fr[0]/np.sqrt(p['solver']['impratio'])))
        for n,nrow in enumerate(a['native_nefc']): errors_J.append(float(np.max(abs(a['native_efc_J'][n,:nrow].T@a['native_efc_force'][n,:nrow]-a['native_qfrc_constraint'][n]))))
        check('native_R_scaling_relative_error',max(errors_R,default=0),1e-10,kind='evidence')
        check('native_force_rows_match_contact',max(errors_force,default=0),1e-10,kind='evidence')
        check('native_J_transpose_force',max(errors_J,default=0),1e-10,kind='evidence')
        check('native_regularized_mu',max(errors_mu,default=0),1e-10,kind='evidence')
    if (HERE/'supplemental-observations.json').exists() and (c['shape']=='box' or v=='B'):
        supplement=read(HERE/'supplemental-observations.json'); coefficient=choice['body_mu'] if c['shape']=='box' else c['body_mu_torsional_m']
        utilization=(tangent if c['shape']=='box' else spin)/np.maximum(normal*coefficient,1e-30)
        early=(t[:-1]<supplement['early_window_s']-1e-12)&(normal>0)&active.any(axis=1)
        saturated=early&(utilization>=supplement['saturation_utilization_min'])&(utilization<=supplement['saturation_utilization_max'])
        m['supplemental_early_saturated_steps']=int(saturated.sum()); m['supplemental_early_active_steps']=int(early.sum())
        m['supplemental_early_utilization_min']=float(utilization[early].min()); m['supplemental_early_utilization_max']=float(utilization[early].max())
    return dict(run_id=result['run_id'],variant=v,repeat=result['repeat'],directory=rel(out),metrics=m,checks=checks,evidence_validity='passed' if all(x['passed'] for x in checks if x['kind']=='evidence') else 'failed',physical_acceptance='passed' if all(x['passed'] for x in checks if x['kind']=='physical') else 'failed_criteria'),a,dict(t=t,velocity=vel[:,0] if c['shape']=='box' else vel[:,5],reference=reference,normal=normal,ratio=tangent/np.maximum(normal,1e-30) if c['shape']=='box' else spin/np.maximum(normal,1e-30),kinetic=kinetic)

def main():
    p=read(HERE/'protocol.json'); excluded=read(HERE/'harness-revisions.json')['excluded_run_ids'] if (HERE/'harness-revisions.json').exists() else []
    cases=[]; failures=[]; evidence={}
    import matplotlib
    matplotlib.use('Agg'); matplotlib.rcParams['svg.hashsalt']='mujoco-native-friction-2026'; import matplotlib.pyplot as plt
    for c in p['cases']:
        runs=[]; arrays={}; curves={}
        for out in sorted((HERE/'runs').iterdir()):
            result=read(out/'result.json')
            if result['case']!=c['id']: continue
            if result['status']!='completed' or out.name in excluded:
                failures.append({'run_id':out.name,'status':result['status'],'reason':'excluded observation schema without step timestep' if out.name in excluded else result.get('error')})
                for f in out.iterdir():
                    if f.is_file(): evidence[rel(f)]=sha(f)
                continue
            scoredata,a,curve=score(out,p,c); runs.append(scoredata); arrays[(result['variant'],result['repeat'])]=a; curves[(result['variant'],result['repeat'])]=curve
            for f in out.iterdir():
                if f.is_file(): evidence[rel(f)]=sha(f)
        assert len(runs)==4 and set(arrays)=={('A',1),('A',2),('B',1),('B',2)}, 'Exactly four eligible runs required'
        checks=[]
        for variant in ('A','B'):
            for key in ('body_q','body_qd','joint_q','joint_qd','world_contact_force','world_contact_torque','contact_wrench'):
                x,y=arrays[(variant,1)][key],arrays[(variant,2)][key]; atol=p['common_criteria']['repeat_force_atol'] if 'force' in key or 'torque' in key or 'wrench' in key else p['common_criteria']['repeat_qd_atol'] if 'qd' in key else p['common_criteria']['repeat_q_atol']
                checks.append(dict(name=f'repeat_{variant}_{key}',value=float(abs(x-y).max()),operator='allclose',atol=atol,rtol=p['common_criteria']['repeat_rtol'],exact=bool(np.array_equal(x,y)),passed=bool(np.allclose(x,y,atol=atol,rtol=p['common_criteria']['repeat_rtol'])),kind='evidence'))
        diffs=[]
        for repeat in (1,2):
            ra=next(x for x in runs if x['variant']=='A' and x['repeat']==repeat); rb=next(x for x in runs if x['variant']=='B' and x['repeat']==repeat)
            changes=diff(read(ROOT/ra['directory']/'resolved-config.json'),read(ROOT/rb['directory']/'resolved-config.json'))
            allowed={'geom_friction','treatment.body_mu'} if c['shape']=='box' else {'geom_condim','treatment.body_condim'}
            checks.append(dict(name=f'config_diff_r{repeat}',value=[d['path'] for d in changes],allowed=sorted(allowed),passed=set(d['path'] for d in changes)==allowed,kind='evidence')); diffs.append({'repeat':repeat,'changes':changes})
            am,bm=ra['metrics'],rb['metrics']
            pair={'final_vx_A_minus_B_min_m_s':am['final_vx_m_s']-bm['final_vx_m_s'],'integrated_tangential_impulse_B_minus_A_min_Ns':bm['integrated_tangential_impulse_Ns']-am['integrated_tangential_impulse_Ns']} if c['shape']=='box' else {'final_omega_A_minus_B_min_rad_s':am['final_omega_z_rad_s']-bm['final_omega_z_rad_s'],'integrated_torsion_impulse_B_min_Nms':bm['integrated_torsion_impulse_Nms']}
            for k,val in pair.items(): checks.append(dict(name=f'{k}_r{repeat}',value=val,operator='>=',limit=c['paired_criteria'][k],passed=bool(val>=c['paired_criteria'][k]),kind='physical'))
        physical=all(r['physical_acceptance']=='passed' for r in runs) and all(x['passed'] for x in checks if x['kind']=='physical')
        valid=all(r['evidence_validity']=='passed' for r in runs) and all(x['passed'] for x in checks if x['kind']=='evidence')
        fig,axes=plt.subplots(3,1,figsize=(9,8),sharex=True)
        for v,color in [('A','#2563eb'),('B','#dc2626')]:
            curve=curves[(v,1)]; axes[0].plot(curve['t'],curve['velocity'],label=v,color=color); keep=curve['t']>=.05-1e-12; axes[0].plot(curve['t'][keep],curve['reference'][keep],'--',color=color,alpha=.6)
            axes[1].plot(curve['t'][:-1],curve['normal'],label=v,color=color); axes[2].plot(curve['t'][:-1],curve['ratio'],label=v,color=color)
        for ax in axes: ax.grid(alpha=.2); ax.legend(loc='best')
        axes[0].set_ylabel('vx (m/s)' if c['shape']=='box' else 'omega z (rad/s)'); axes[1].set_ylabel('Normal force (N)'); axes[2].set_ylabel('Tangential / normal' if c['shape']=='box' else 'Torsion / normal (m)'); axes[2].set_xlabel('Time (s)'); fig.tight_layout(); fig.savefig(HERE/(c['id']+'.svg'),metadata={'Date':None}); fig.savefig(HERE/(c['id']+'.png'),dpi=120); plt.close(fig)
        cases.append(dict(id=c['id'],title=c['title'],runs=runs,checks=checks,config_diff=diffs,evidence_validity='passed' if valid else 'failed',physical_acceptance='passed' if physical else 'failed_criteria',source_refs=p['source_refs'],plot='friction_low_regime/'+c['id']+'.svg'))
    allchecks=[x for c in cases for x in c['checks']]+[x for c in cases for r in c['runs'] for x in r['checks']]
    for f in [HERE/'protocol.json',HERE/'analyze.py',HERE/'DESIGN.md',HERE/'harness-revisions.json',HERE/'supplemental-observations.json',*list((HERE/'native-source').iterdir())]:
        if f.is_file(): evidence[rel(f)]=sha(f)
    result=dict(schema_version='1.0',status='passed' if all(c['evidence_validity']=='passed' for c in cases) else 'failed_evidence',formal_runs=sum(len(c['runs']) for c in cases),checks_total=len(allchecks),checks_passed=sum(x['passed'] for x in allchecks),cases=cases,excluded_or_failed_runs=failures,analyzer_sha256=sha(__file__),evidence_files=evidence)
    save(HERE/'analysis.json',result)
    print(json.dumps({k:result[k] for k in ('status','formal_runs','checks_total','checks_passed')}))
    for c in cases: print(c['id'],c['physical_acceptance'],[(r['variant'],r['repeat'],r['metrics']) for r in c['runs']]); print('FAILED', [x for x in c['checks'] if not x['passed']]+[x for r in c['runs'] for x in r['checks'] if not x['passed']])
if __name__=='__main__': main()
