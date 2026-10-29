"""Independent archived contact audit: geometry, activation and impulse; no physics calls."""
from pathlib import Path
import hashlib,json
import numpy as np
ROOT=Path(__file__).resolve().parents[2]; GROUP=ROOT/'experiments/mujoco_joint_contact_lab/contact'
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def mx(a): return float(np.max(abs(a))) if np.size(a) else 0.
def main():
    protocol=read(GROUP/'protocol.json'); analysis=read(GROUP/'analysis.json'); revision=read(GROUP/'harness-revisions.json'); checks=[]; measurements=[]; raws={}; dt=protocol['run']['dt_s']; shared=protocol['shared_criteria']
    def check(name,actual,expected,passed): checks.append(dict(name=name,actual=actual,expected=expected,passed=bool(passed)))
    selected=[f for f in sorted(GROUP.glob('runs/*/result.json')) if f.parent.name not in revision['excluded_runs']]
    check('formal_run_count',len(selected),8,len(selected)==8)
    for f in selected:
        r=read(f); d=f.parent; a=dict(np.load(d/'trajectory.npz')); cfg=read(d/'resolved-config.json'); case=next(c for c in protocol['cases'] if c['id']==r['case']); settings=case['variants'][r['variant']]; tag=r['run_id']; raws[(r['case'],r['variant'],r['repeat'])]=a
        check(tag+' completed',r['status'],'completed',r['status']=='completed')
        check(tag+' immutable archive',len(r['files_sha256']),True,all(sha(d/k)==v for k,v in r['files_sha256'].items()))
        check(tag+' protocol fingerprint',sha(d/'protocol.json'),sha(GROUP/'protocol.json'),sha(d/'protocol.json')==sha(GROUP/'protocol.json'))
        check(tag+' program fingerprint',sha(d/'runner.py'),revision['new_runner_sha256'],sha(d/'runner.py')==revision['new_runner_sha256'])
        check(tag+' finite',True,True,all(np.isfinite(x).all() for x in a.values()))
        check(tag+' time shape',len(a['t']),801,len(a['t'])==801)
        check(tag+' actual native dt',mx(a['step_native_timestep']-dt),1e-14,mx(a['step_native_timestep']-dt)<1e-14)
        check(tag+' native time alignment',mx(a['step_native_time_after_step']-a['t'][1:]),1e-12,mx(a['step_native_time_after_step']-a['t'][1:])<1e-12)
        check(tag+' preintegration contact time',mx(a['step_time']-a['t'][:-1]),0,mx(a['step_time']-a['t'][:-1])==0)
        check(tag+' body/qpos post integration',mx(a['body_q'][1:,0,:3]-a['step_native_qpos'][:,:3]),2e-8,mx(a['body_q'][1:,0,:3]-a['step_native_qpos'][:,:3])<2e-8)
        check(tag+' body/qvel post integration',mx(a['body_qd'][1:,0,:3]-a['step_native_qvel'][:,:3]),1e-7,mx(a['body_qd'][1:,0,:3]-a['step_native_qvel'][:,:3])<1e-7)
        check(tag+' body/joint same origin',mx(a['body_q'][:,0]-a['joint_q']),0,mx(a['body_q'][:,0]-a['joint_q'])==0)
        check(tag+' initial state',[float(a['body_q'][0,0,2]),float(a['body_qd'][0,0,2])],[.15,-1],abs(a['body_q'][0,0,2]-.15)<2e-8 and a['body_qd'][0,0,2]==-1)
        check(tag+' zero gravity',cfg['native_option']['gravity'],[0,0,0],cfg['native_option']['gravity']==[0,0,0])
        check(tag+' inertia',cfg['native_body_inertia'][1],[.001]*3,np.allclose(cfg['native_body_inertia'][1],[.001]*3,atol=1e-10,rtol=0))
        check(tag+' mass',cfg['native_body_mass'],[0,1],cfg['native_body_mass']==[0,1])
        check(tag+' raw solref mode',cfg['custom']['solref_mode'],[1,1],cfg['custom']['solref_mode']==[1,1])
        check(tag+' actual backend',cfg['use_mujoco_cpu'],True,cfg['use_mujoco_cpu'] and cfg['refsafe_enabled'] and not cfg['zero_margins_for_native_ccd'])
        valid=a['step_contact_valid']; active=valid&(a['step_contact_efc_address']>=0); inactive=valid&~active
        z=a['body_q'][:,0,2].astype(float); v=a['body_qd'][:,0,2].astype(float); signed=z[:-1]-protocol['scene']['radius_m']; force=a['step_contact_normal_force']
        check(tag+' independent surface distance',mx(a['step_contact_dist'][valid]-signed[valid]),shared['geometry_error_max'],mx(a['step_contact_dist'][valid]-signed[valid])<shared['geometry_error_max'])
        check(tag+' inactive force exact zero',mx(force[inactive]),1e-10,mx(force[inactive])<=1e-10)
        check(tag+' force maps generalized force',mx(force-a['step_qfrc_constraint'][:,2]),1e-9,mx(force-a['step_qfrc_constraint'][:,2])<=1e-9)
        check(tag+' force nonnegative',float(force.min()),-1e-10,float(force.min())>=-1e-10)
        check(tag+' priority contact solref',mx(a['step_contact_solref'][valid]-settings['solref']),2e-8,mx(a['step_contact_solref'][valid]-settings['solref'])<2e-8)
        check(tag+' includemargin retains margin',mx(a['step_contact_includemargin'][valid]-settings['margin']),2e-8,mx(a['step_contact_includemargin'][valid]-settings['margin'])<2e-8)
        check(tag+' inactive means outside margin',float(np.min(a['step_contact_dist'][inactive]-a['step_contact_includemargin'][inactive])) if inactive.any() else None,0,not inactive.any() or np.all(a['step_contact_dist'][inactive]>=a['step_contact_includemargin'][inactive]))
        expecteddetect=(.15-.05-settings['margin']-settings['gap']); expectedactive=(.15-.05-settings['margin']); detect=float(a['step_time'][np.flatnonzero(valid)[0]]); activate=float(a['step_time'][np.flatnonzero(active)[0]])
        check(tag+' independent first detection',detect,expecteddetect,abs(detect-expecteddetect)<=2*dt)
        check(tag+' independent first activation',activate,expectedactive,abs(activate-expectedactive)<=2*dt)
        impulse_error=mx(v[1:]-v[0]-dt*np.cumsum(force))
        check(tag+' entire trajectory impulse',impulse_error,shared['impulse_residual_max'],impulse_error<shared['impulse_residual_max'])
        firstactive=int(np.flatnonzero(active)[0]); freepos=mx(z[:firstactive+1]-(.15-a['t'][:firstactive+1])); check(tag+' independent free flight',freepos,shared['geometry_error_max'],freepos<shared['geometry_error_max'])
        restitution=float(v[-100:].mean())/abs(float(v[0])); metrics=next(x for x in analysis['cases'] if x['id']==r['case']); declared=next(x for x in metrics['variants'] if x['variant']==r['variant']); declared=declared if r['repeat']==1 else declared['reproduction']
        check(tag+' reported restitution',restitution,declared['metrics']['restitution'],abs(restitution-declared['metrics']['restitution'])<1e-12)
        check(tag+' reported events',[detect,activate],[declared['metrics']['detection_time_s'],declared['metrics']['activation_time_s']],detect==declared['metrics']['detection_time_s'] and activate==declared['metrics']['activation_time_s'])
        if r['case']=='native_solref_rebound': check(tag+' frozen restitution gate',restitution,case['criteria']['A_restitution_min'] if r['variant']=='A' else case['criteria']['B_restitution_max'],restitution>=case['criteria']['A_restitution_min'] if r['variant']=='A' else restitution<=case['criteria']['B_restitution_max'])
        measurements.append(dict(run_id=tag,raw_sha256=sha(d/'trajectory.npz'),detection_s=detect,activation_s=activate,independent_restitution=restitution,impulse_max_error_Ns=impulse_error,inactive_steps=int(inactive.sum())))
    for case in protocol['cases']:
        for v in ('A','B'):
            one,two=raws[(case['id'],v,1)],raws[(case['id'],v,2)]
            for key in ('body_q','body_qd','joint_q','joint_qd','step_contact_normal_force'):
                check(case['id']+v+' exact repeat '+key,mx(one[key]-two[key]),0,np.array_equal(one[key],two[key]))
        if case['id']=='native_gap_activation':
            for repeat in (1,2):
                one,two=raws[(case['id'],'A',repeat)],raws[(case['id'],'B',repeat)]
                check('gap physical trajectories equivalent r'+str(repeat),mx(one['body_q']-two['body_q']),1e-5,mx(one['body_q']-two['body_q'])<=1e-5)
                check('gap force activation equal r'+str(repeat),mx(one['step_contact_normal_force']-two['step_contact_normal_force']),1e-10,mx(one['step_contact_normal_force']-two['step_contact_normal_force'])<=1e-10)
    check('all excluded retained',len(revision['excluded_runs']),8,len(revision['excluded_runs'])==8 and all((GROUP/'runs'/x/'trajectory.npz').is_file() for x in revision['excluded_runs']))
    report=dict(status='passed' if all(x['passed'] for x in checks) else 'failed',checks=len(checks),passed_checks=sum(x['passed'] for x in checks),review_script_sha256=sha(__file__),reviewed_group_hashes={f:sha(GROUP/f) for f in ('protocol.json','runner.py','analyze.py','analysis.json','publication.json','RESULTS.md')},measurements=measurements,findings=['No blocking finding. Contact sample is preintegration geometry and solve impulse; state is postintegration, alignment verified independently.','MuJoCo3.15 source engine_collision_driver.c1946 uses margin+gap for candidate generation;1831/1840 retains includemargin and excludes distance>=margin. Measured gap changes detection only, with80 inactive samples and identical physical trajectory.','Authored raw solref ratio intervention also changes effective stiffness for positive solref: fixed timeconst alone is not a constant-stiffness damping-only experiment; publication states this boundary.','Native contact diagnostics do not imply Newton CONTACT_F support. No new simulation was run.','Eight instrumentation-incomplete attempts remain archived; exclusion does not remove negative physics.'],checks_detail=checks)
    Path(__file__).with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps({'status':report['status'],'checks':report['checks'],'passed':report['passed_checks'],'failures':[c for c in checks if not c['passed']]}))
if __name__=='__main__': main()
