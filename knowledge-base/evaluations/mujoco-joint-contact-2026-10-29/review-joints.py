"""Independent read-only joint evidence review, without importing group runner/analyzer."""
from pathlib import Path
import json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
G=ROOT/'experiments/mujoco_joint_contact_lab/joints'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def maximum(x):return float(np.max(np.abs(x))) if np.size(x) else 0.
def main():
    p=read(G/'protocol.json'); analysis=read(G/'analysis.json'); pub=read(G/'publication.json'); freeze=read(ROOT/'planning/mujoco-joint-contact-2026-10-29/joints-freeze.json'); checks=[]; measured=[]; arrays={}
    def ck(name,actual,expected,passed):checks.append({'name':name,'actual':actual,'expected':expected,'passed':bool(passed)})
    ck('frozen protocol',sha(G/'protocol.json'),freeze['sha256'],sha(G/'protocol.json')==freeze['sha256']); ck('analysis fingerprint',analysis['analyzer_sha256'],sha(G/'analyze.py'),analysis['analyzer_sha256']==sha(G/'analyze.py')); ck('publication analysis fingerprint',pub['analysis_sha256'],sha(G/'analysis.json'),pub['analysis_sha256']==sha(G/'analysis.json'))
    runs=[r for c in analysis['cases'] for v in c['variants'] for r in v['runs']]; ck('formal unique runs',len({r['run_id'] for r in runs}),16,len(runs)==16 and len({r['run_id'] for r in runs})==16)
    for run in runs:
        directory=ROOT/run['run']; r=read(directory/'result.json'); c=next(c for c in p['cases'] if c['id']==r['case']); cfg={**c['base'],**c['variants'][r['variant']]}; a=dict(np.load(directory/'trajectory.npz')); actual=read(directory/'resolved-config.json'); env=read(directory/'environment.json'); installed=read(directory/'installed-source-validation.json'); tag=r['run_id']; h=p['run']['dt_s'];N=p['run']['steps'];n=np.arange(N+1);I=1+cfg['armature'];d=cfg['damping'];kp=cfg['kp'];kd=cfg['kd'];qref=cfg['qref'];tau=cfg['external_tau'];v0=cfg['initial_v']; q=a['native_qpos'][:,0];v=a['native_qvel'][:,0]; m=actual['mj_model']; arrays[(r['case'],r['variant'],r['repeat'])]=a
        ck(tag+' archive integrity',len(r['files_sha256']),True,all(sha(directory/k)==value for k,value in r['files_sha256'].items())); ck(tag+' protocol/program',True,True,r['protocol_sha256']==freeze['sha256'] and r['runner_sha256']==sha(G/'runner.py')); ck(tag+' installed sources',installed['checked_python_files'],809,installed['checked_python_files']==809 and not installed['missing'] and not installed['changed']); ck(tag+' source ref current hashes',True,True,all(sha(ROOT/'sources/newton-v1.7.0'/k)==value for k,value in env['source_refs_sha256'].items())); ck(tag+' after freeze',r['started_at_utc'],freeze['frozen_at_utc'],r['started_at_utc']>freeze['frozen_at_utc'])
        ck(tag+' force time alignment',maximum(a['force_t']-a['t'][:-1]),0,np.array_equal(a['force_t'],a['t'][:-1]));ck(tag+' physical arrays finite',True,True,all(np.isfinite(value).all() for value in a.values())); ck(tag+' final backend',actual['opt_final'],p['solver'],actual['opt_final']['integrator']==0 and actual['opt_final']['timestep']==h and actual['use_mujoco_cpu'] and actual['update_data_interval']==0 and actual['opt_final']['gravity']==[0,0,0])
        MeasuredI=a['native_mass_matrix'][:,0,0]; ck(tag+' inertia',maximum(MeasuredI-I),1e-6,maximum(MeasuredI-I)<=1e-6)
        # Independent per-step impulse identity. Euler joint damping is implicit;
        # recorded passive force is evaluated before integration, not the implicit force.
        impulse=MeasuredI*np.diff(v)-h*(a['qfrc_applied'][:,0]+a['qfrc_actuator'][:,0]+a['qfrc_constraint'][:,0]-d*v[1:])
        ck(tag+' native momentum identity',maximum(impulse),1e-10,maximum(impulse)<=1e-10); ck(tag+' native semiimplicit position',maximum(np.diff(q)-h*v[1:]),1e-12,maximum(np.diff(q)-h*v[1:])<=1e-12)
        ck(tag+' reported passive pre-state',maximum(a['qfrc_passive'][:,0]+d*v[:-1]),1e-10,maximum(a['qfrc_passive'][:,0]+d*v[:-1])<=1e-10)
        expected_act=kp*(qref-q[:-1])-kd*v[:-1] if cfg['mode']=='POSITION' else np.zeros(N); ck(tag+' actual actuator pre-state',maximum(a['qfrc_actuator'][:,0]-expected_act),1e-6,maximum(a['qfrc_actuator'][:,0]-expected_act)<=1e-6)
        limited=c['id'].endswith('upper_limit')
        if cfg['mode']=='POSITION':
            # Homogeneous transition about equilibrium; matrix powers are independent
            # of the group's iterative scalar reference implementation.
            den=I+h*d; A=np.array([[1-h*h*kp/den,h*(I-h*kd)/den],[-h*kp/den,(I-h*kd)/den]])
            state=np.array([np.linalg.matrix_power(A,int(i))@np.array([-qref,v0]) for i in n]); qr=state[:,0]+qref;vr=state[:,1]
        elif d:
            factor=I/(I+h*d);vr=v0*factor**n; qr=h*v0*factor*(1-factor**n)/(1-factor)
        else:vr=v0+n*h*tau/I;qr=n*h*v0+h*h*tau*n*(n+1)/(2*I)
        end=N+1
        if limited:
            idx=int(np.flatnonzero(abs(a['qfrc_constraint'][:,0])>1e-6)[0]);pred=int(np.flatnonzero(qr[:-1]>=cfg['limit_upper'])[0]);end=idx+1
            ck(tag+' analytical first limit event',idx*h,pred*h,abs(idx-pred)*h<=c['criteria']['first_constraint_time_error_max_s']); ck(tag+' not hard clipped',float(q.max()-cfg['limit_upper']),'>0',q.max()>cfg['limit_upper']); ck(tag+' final reaction',maximum(a['qfrc_constraint'][-250:,0]+tau),.01,maximum(a['qfrc_constraint'][-250:,0]+tau)<=.01)
        ck(tag+' closed form q reference',maximum(a['joint_q'][:end,0]-qr[:end]),p['common_criteria']['q_reference_max_abs_rad'],maximum(a['joint_q'][:end,0]-qr[:end])<=p['common_criteria']['q_reference_max_abs_rad']); ck(tag+' closed form v reference',maximum(a['joint_qd'][:end,0]-vr[:end]),p['common_criteria']['v_reference_max_abs_rad_s'],maximum(a['joint_qd'][:end,0]-vr[:end])<=p['common_criteria']['v_reference_max_abs_rad_s'])
        ck(tag+' native warnings',int(a['warning_number'].max()),0,a['warning_number'].max()==0)
        measured.append({'id':r['case'],'variant':r['variant'],'repeat':r['repeat'],'momentum_identity_max_Nms':maximum(impulse),'native_inertia_kgm2':float(MeasuredI[0]),'q_reference_max_rad':maximum(a['joint_q'][:end,0]-qr[:end]),'v_reference_max_rad_s':maximum(a['joint_qd'][:end,0]-vr[:end]),'final_q_rad':float(q[-1]),'final_v_rad_s':float(v[-1]),'constraint_max_iterations':int(a['solver_niter'].max())})
    for c in p['cases']:
        for v in ['A','B']:
            one,two=[arrays[(c['id'],v,rep)] for rep in [1,2]]
            relevant=[k for k in one if k!='step_wall_s']; differences={k:maximum(one[k]-two[k]) for k in relevant};ck(c['id']+v+' independent repeats',differences,'all physical/diagnostic arrays exact',all(x==0 for x in differences.values()))
    revision=read(G/'harness-revisions.json')['revisions'][0];failed=read(G/'runs'/revision['failed_run']/'result.json'); ck('retained initial harness failure',failed['status'],'failed',failed['status']=='failed' and not (G/'runs'/revision['failed_run']/'trajectory.npz').exists())
    runner=(G/'runner.py').read_text();ck('native diagnostic only mass matrix',True,True,'mj_fullM(solver.mj_model,solver.mj_data,dense)' in runner and 'mj_forward' not in runner and 'mj_step(' not in runner)
    report={'status':'passed' if all(c['passed'] for c in checks) else 'failed','checks':len(checks),'passed_checks':sum(c['passed'] for c in checks),'reviewer':'independent contact agent','review_script_sha256':sha(Path(__file__)),'reviewed_files_sha256':{f:sha(G/f) for f in ['runner.py','analyze.py','analysis.json','protocol.json','publication.json','RESULTS.md']},'measurements':measured,'checks_detail':checks,'findings':[],'scope':'Independent closed-form/matrix-power references, native momentum identities, source and archive integrity, force/state alignment, repeat diagnostics, retained pre-step harness failure. No simulation and no group analyzer import.','limitations':['Only the frozen single-hinge Euler/native CPU scenes; no general gains or solver convergence claim.','Upper limit exact reference ends at activation; soft transient verified by bounded penetration and late force balance, not an invented analytic waveform.','Nominal inertia differs by float export rounding; measured inertia used only for separate momentum identity, frozen nominal reference remains unchanged.']}
    out=Path(__file__).with_suffix('.json');out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'status':report['status'],'checks':len(checks),'passed':report['passed_checks'],'failures':[c for c in checks if not c['passed']]},ensure_ascii=False))
if __name__=='__main__':main()
