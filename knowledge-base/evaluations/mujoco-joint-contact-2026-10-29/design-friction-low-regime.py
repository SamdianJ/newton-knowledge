"""Pre-run analytical contact-QP checks only. No Newton/MuJoCo import or simulation."""
from pathlib import Path
import copy,hashlib,json
import numpy as np
ROOT=Path(__file__).resolve().parents[2];G=ROOT/'experiments/mujoco_joint_contact_lab/friction'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def solve(a,c,cfg,speed,slide,torsion):
    count=int(a['ncon'][0]);dim=int(a['contact_dim'][0,0]);J=[];S=np.zeros((count*dim,count));relative_R=[];positions=[];v=np.zeros(6);v[0 if c['shape']=='box' else 5]=speed
    for k in range(count):
        frame=a['contact_frame'][0,k];radius=a['contact_pos'][0,k]-a['pre_com'][0];sign=1 if a['contact_geom'][0,k,1]==cfg['dynamic_geom'] else -1
        for j in range(dim):J.append(sign*np.r_[frame[j],np.cross(radius,frame[j])] if j<3 else sign*np.r_[np.zeros(3),frame[0]])
        S[k*dim,k]=1;relative_R.extend([1,1,1]+([slide**2/torsion**2] if dim==4 else []));positions.extend([a['contact_dist'][0,k]]+[0]*(dim-1))
    J=np.array(J);vel=J@v;mu=np.array([slide,slide]+([torsion] if dim==4 else []));directions=[]
    for k in range(count):
        vv=vel[k*dim+1:(k+1)*dim];norm=np.linalg.norm(mu*vv);direction=mu*mu*vv/norm if norm else np.zeros_like(mu);S[k*dim+1:(k+1)*dim,k]=-direction;directions.append(direction)
    d=cfg['geom_solimp'][0][0];tc,zeta=cfg['geom_solref'][0];b=2/(d*tc);K=1/(d*d*tc*tc*zeta*zeta);ref=-b*vel-K*d*np.array(positions);A=J@np.diag(np.r_[np.ones(3),1/np.array(c['inertia_diagonal_kg_m2'])])@J.T;R=np.array(relative_R)*(1-d)/d;H=A+np.diag(R);linear=J@np.array([0,0,-9.81,0,0,0])-ref
    normals=np.linalg.solve(S.T@H@S,-S.T@linear);f=S@normals;gradient=H@f+linear;cone_lambda=[];residual=[]
    for k in range(count):
        ft=f[k*dim+1:(k+1)*dim];norm=np.linalg.norm(ft/mu)
        if norm:
            cone_grad=np.r_[-1,ft/(mu*mu*norm)];grad=gradient[k*dim:(k+1)*dim];lam=-np.dot(grad,cone_grad)/np.dot(cone_grad,cone_grad);cone_lambda.append(float(lam));residual.append(float(np.max(abs(grad+lam*cone_grad))))
        else:cone_lambda.append(0.);residual.append(float(np.max(abs(gradient[k*dim:(k+1)*dim]))))
    boundary_valid=bool(np.all(normals>0) and min(cone_lambda)>=-1e-9 and max(residual)<1e-8)
    unconstrained=-np.linalg.solve(H,linear);inside=[]
    for k in range(count):inside.append(float(np.linalg.norm(unconstrained[k*dim+1:(k+1)*dim]/mu)/unconstrained[k*dim]))
    if max(inside)<1 and all(unconstrained[k*dim]>0 for k in range(count)):chosen=unconstrained;branch='cone_interior'
    elif boundary_valid:chosen=f;branch='saturated_boundary'
    else:chosen=None;branch='unresolved_mixed_branches'
    net=J.T@chosen if chosen is not None else np.full(6,np.nan)
    return {'shape':c['shape'],'dim':dim,'speed':speed,'slide_coefficient':slide,'torsion_coefficient_m':torsion,'branch':branch,'boundary_kkt_lambda':cone_lambda,'boundary_kkt_residual':residual,'unconstrained_cone_utilization':inside,'normal_total_N':float(sum(chosen[k*dim] for k in range(count))) if chosen is not None else None,'world_force_N':net[:3].tolist(),'world_torque_Nm':net[3:].tolist(),'initial_vertical_acceleration_mps2':float(net[2]-9.81),'R_normal':float(R[0]),'R_torsion':float(R[3]) if dim==4 else None,'regularization_reference_b':float(b),'minimum_coefficient_above_native_floor':float(min(mu)),'native_mjMINMU':1e-5,'source_geometry':'original archived initial geometry only; all velocity/friction inputs overwritten analytically; no new trajectory generated'}
def main():
    p=read(G/'protocol.json');rev=read(G/'harness-revisions.json');out=[]
    for file in sorted(G.glob('runs/*/result.json')):
        result=read(file)
        if result['run_id'] in rev['excluded_run_ids'] or result['repeat']!=1:continue
        a=dict(np.load(file.parent/'trajectory.npz'));c=next(c for c in p['cases'] if c['id']==result['case']);cfg=read(file.parent/'resolved-config.json')
        if c['shape']=='box':
            slide={'A':.001,'B':.004}[result['variant']]
            for speed in [.2,.02]:out.append({'variant':result['variant'],**solve(a,c,cfg,speed,slide,0)})
        else:
            for slide in [.3,.03]:out.append({'variant':result['variant'],**solve(a,c,cfg,1.,slide,2e-5)})
    report={'status':'analytical_design_only','no_new_physics':True,'script_sha256':sha(Path(__file__)),'calculations':out,'counterfactual_status':'These are pre-run design calculations, not measured experiment results. Cone-interior outcomes must not be described as saturated.','reference_expected_effects':{'box_v0_0p2_T0p3':{'A_delta_v_mps':.001*9.81*.3,'B_delta_v_mps':.004*9.81*.3,'A_minus_B_final_speed_mps':.003*9.81*.3},'box_v0_0p02_T0p3':{'A_final_speed_mps':.02-.001*9.81*.3,'B_final_speed_mps':.02-.004*9.81*.3,'A_minus_B_final_speed_mps':.003*9.81*.3},'sphere_T0p5':{'B_omega_loss_radps':2e-5*9.81/.004*.5,'B_torsional_impulse_Nms':2e-5*9.81*.5}},'recommended_gates':{'box':{'minimum_positive_speed_mps':.005,'settled_reference_velocity_error_mps_max':.001,'force_ratio_abs_error_max':.0003,'A_minus_B_final_speed_mps_min':.007,'integrated_tangent_impulse_B_minus_A_Ns_min':.007,'early_active_positive_normal_saturated_samples_min':20,'early_window_s':.02,'cone_utilization_min':.98,'cone_utilization_max':1.00001},'sphere':{'minimum_spin_speed_radps':.95,'settled_reference_spin_error_radps_max':.005,'A_max_spin_change_radps':.001,'B_to_A_final_spin_gap_radps_min':.018,'B_torsional_impulse_Nms_min':.000075,'B_torque_normal_ratio_error_m_max':2e-6,'early_active_positive_normal_saturated_samples_min':20,'early_window_s':.02,'cone_utilization_min':.98,'cone_utilization_max':1.00001},'shared':'Keep independent impulse checks, >=99% actual bearing after .05s, full transient geometry and energy retained. Candidate ncon is not bearing. Require physical effect and nonempty saturation. Suggested early20 samples assumes dt=1e-4, adjust explicit count to time-window if protocol chooses .001.'},'limitations':['The box v0=.2 proposal produces initial N slightly above mg; stable bearing is not proven by the first-step result.','The box v0=.02 alternative has initial N below mg and sustained positive-speed Coulomb prediction through .3s; full nonlinear stability still requires experiment.','Sphere slide=.3 gives cone-interior weak torque for torsion2e-5/omega1 at impratio1; slide=.03 restores initial saturation without changing A/B condim intervention.','Native floor1e-5 is below torsion2e-5; floor is not the cause of weak torque.']}
    Path(__file__).with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8');print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
