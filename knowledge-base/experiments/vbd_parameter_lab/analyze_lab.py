"""Analyze recorded trajectories, make scientific figures, and produce report-ready evidence."""
from pathlib import Path
import hashlib,json,csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SHA='7e75abe28b8d69522bc0b34837aaed2c303dff5a'
BASE=f'https://github.com/newton-physics/newton/blob/{SHA}/'
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def anchor(path,needle):
    lines=(ROOT/'sources/newton-v1.7.0'/path).read_text(encoding='utf-8').splitlines()
    n=next(i for i,s in enumerate(lines,1) if needle in s)
    return {'path':path,'line':n,'url':BASE+path+'#L'+str(n),'needle':needle}

SOURCE={
 'full_surface':('newton/_src/sim/collide.py','enable_rigid_soft_full_surface_contact: Generate'),
 'iterations':('newton/_src/solvers/vbd/solver_vbd.py','for iter_num in range(self.iterations):'),
 'substeps':('newton/_src/solvers/vbd/particle_vbd_kernels.py','def solve_elasticity('),
 'stiffness':('newton/_src/solvers/vbd/particle_vbd_kernels.py','def evaluate_spring_force_and_hessian('),
 'damping':('newton/_src/solvers/vbd/particle_vbd_kernels.py','def evaluate_spring_force_and_hessian('),
 'self_contact':('newton/_src/solvers/vbd/solver_vbd.py','def _collision_detection_penetration_free('),
 'self_margin':('newton/_src/solvers/vbd/solver_vbd.py','if particle_self_contact_margin is not None and particle_self_contact_gap is None:'),
 'contact_stiffness':('newton/_src/solvers/vbd/rigid_vbd_kernels.py','def _evaluate_rigid_soft_contact_force_norm('),
 'friction':('newton/_src/solvers/vbd/particle_vbd_kernels.py','def compute_friction('),
 'friction_epsilon':('newton/_src/solvers/vbd/rigid_vbd_kernels.py','eps_u = friction_epsilon * dt'),
 'dat':('newton/_src/solvers/vbd/solver_vbd.py','def _init_rigid_penetration_free('),
 'dat_relaxation':('newton/_src/solvers/vbd/solver_vbd.py','rigid_soft_max_displacement = 0.5 * self.dat_conservative_bound_relaxation'),
 'rigid_mode':('newton/_src/solvers/vbd/rigid_vbd_kernels.py','def _material_force_terms('),
 'joint_stiffness':('newton/_src/solvers/vbd/rigid_vbd_kernels.py','def _material_force_terms('),
 'membrane':('newton/_src/solvers/vbd/particle_vbd_kernels.py','def evaluate_neo_hookean_membrane_force_hessian('),
 'bending':('newton/_src/solvers/vbd/particle_vbd_kernels.py','def evaluate_dihedral_angle_based_bending_force_hessian('),
 'stabilization':('newton/_src/solvers/vbd/rigid_vbd_kernels.py','C_update = C_vec - alpha * C0'),
}

def chain_reference(c,t):
    # All motion stays on z and springs stay ordered: exact backward-Euler linear system.
    n=15;mass=.1;ke=c['common']['ke'];dt=c['common']['dt']
    K=np.zeros((n,n))
    for i in range(n):
        K[i,i]+=ke
        if i>0:K[i-1,i-1]+=ke;K[i-1,i]-=ke;K[i,i-1]-=ke
    M=np.eye(n)*mass;A=M+dt*dt*K
    u=np.zeros(n);v=np.zeros(n);zs=[.325]
    for _ in t[1:]:
        new=np.linalg.solve(A,M@(u+dt*v)+dt*dt*np.full(n,mass*9.81))
        v=(new-u)/dt;u=new;zs.append(.325-u[-1])
    return np.asarray(zs)*1000

def note(c,variants):
    a,b=[v['metrics'] for v in variants];f=lambda x:f'{x:.3g}'
    id=c['id'];unit=c['unit']
    if id=='full_surface':return f"A 未生成接触，球底降到支撑面下 {f(-a['final'])} mm；B 生成面接触并被托住，终态压入约 {f(-b['final'])} mm。覆盖面内接触得到支持，但有限 penalty 仍有小压入。"
    if id=='iterations':return f"对同 dt 的全局线性隐式参考，末端轨迹 RMSE：A {f(a['reference_rmse_mm'])} / B {f(b['reference_rmse_mm'])} mm。30 次更接近参考；这是收敛误差，不是改了材料。"
    if id in ('substeps','damping'):return f"末态机械能/初始能：A {f(a['final_energy_fraction']*100)}% / B {f(b['final_energy_fraction']*100)}%。"+('同一物理振子，更多子步保留了更多振动能量，但仍有隐式 Euler 数值耗散。' if id=='substeps' else 'A 的衰减仍含数值耗散；B 另有明确的材料阻尼耗散。')
    if id=='stiffness':return f"末 20% 时间的平均伸长：A {f(a['tail_mean'])} / B {f(b['tail_mean'])} mm；mg/k 预测为 196.2 / 19.62 mm。静态响应支持刚度作用。"
    if id=='self_contact':return f"关闭后上片穿过下片；开启后停在约 {f(b['tail_mean'])} mm，接近配置的 10 mm 交互距离。固定下片、零初始穿插。"
    if id=='self_margin':return f"末段平均间距为 {f(a['tail_mean'])} / {f(b['tail_mean'])} mm，分别接近 5 / 40 mm。gap 固定 80 mm；这不是只改检测速度。"
    if id=='contact_stiffness':return f"末段压入约 {f(-a['tail_mean'])} / {f(-b['tail_mean'])} mm，与 mg/k 的 19.62 / 0.1962 mm 一致。刚度不是无代价的开关，冲击峰值见曲线。"
    if id=='friction':return f"1 秒水平位移：A {f(a['final'])} / B {f(b['final'])} mm。高 mu 明显缩短停止距离；两侧均设相同 ke/kd/epsilon。"
    if id=='friction_epsilon':return f"1 N 小推力作用 1 秒，位移为 {f(a['final'])} / {f(b['final'])} mm。较大平滑阈值在此案例产生更多蠕滑，mu 始终为 0.5。"
    if id=='dat':return f"A 质点穿过薄板，最低 {f(a['min'])} mm；B 保持在板顶以上，最低 {f(b['min'])} mm。此例支持截断效果，不外推为所有网格/初始穿插都安全。"
    if id=='dat_relaxation':return f"两侧都未穿板，较保守 A 更缓慢接近接触面。终态间距 {f(a['final'])} / {f(b['final'])} mm；速度被截断后的轨迹不同，不以更大间距判优。"
    if id=='rigid_mode':return f"同 ke=200，末态关节误差 A {f(a['final'])} / B {f(b['final'])} mm；compliant B 接近 mg/k=49.05 mm。模式切换改变约束解释，不能说误差较小的一侧自动更真实。"
    if id=='joint_stiffness':return f"末态误差 {f(a['final'])} / {f(b['final'])} mm，接近 mg/k 的 49.05 / 4.905 mm。支持 finite-material compliant 的结构刚度解释。"
    if id=='membrane':return f"相同 0.5 kg 载荷，末态顶点下移 {f(a['final'])} / {f(b['final'])} mm。此次同时缩放 ke/ka，不能把差异单独归因于其中一项。"
    if id=='bending':return f"自由翼末态下移 {f(a['final'])} / {f(b['final'])} mm；较大弯曲系数明显抵抗折叠。瞬态过冲仍可见，固定的是同一网格和面内材料。"
    if id=='stabilization':return f"A 快速纠错并越过目标 {f(-a['min'])} mm；B 无本次过冲但 0.5 秒后仍有 {f(b['final'])} mm 残差。体现纠正速度与误差注入之间的取舍。"

def main():
    cases=read(HERE/'cases.json');rows=[]
    plots=HERE/'plots';plots.mkdir(exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
    for c in cases:
        vs=[read(HERE/'data'/c['id']/f'{tag}.json') for tag in ['A','B']]
        ref=None
        if c['id']=='iterations':
            ref=chain_reference(c,vs[0]['curve']['time'])
            for v in vs:v['metrics']['reference_rmse_mm']=float(np.sqrt(np.mean((np.array(v['curve']['value'])-ref)**2)))
        if c['id']=='substeps':ref=120*np.cos(30*np.array(vs[1]['curve']['time']))
        for v in vs:
            v['metrics']['estimated_solver_ms_total']=v['metrics']['step_ms_median_after_warmup']*v['metrics']['steps']
        fig,ax=plt.subplots(figsize=(3.25,1.72),dpi=180)
        for v,color in zip(vs,['#2563eb','#d76823']):
            ax.plot(v['curve']['time'],v['curve']['value'],color=color,linewidth=1.75,label=v['variant'])
        if ref is not None:
            rt=vs[0 if c['id']=='iterations' else 1]['curve']['time'];ax.plot(rt,ref,'--',color='#697487',linewidth=1,label='Reference')
        ax.axhline(0,color='#bac3d0',linewidth=.6);ax.grid(axis='y',alpha=.16)
        ax.set_xlabel('Time (s)',fontsize=9,labelpad=2);ax.set_ylabel(c['unit'],fontsize=9,labelpad=2)
        ax.tick_params(labelsize=8);ax.legend(loc='best',frameon=False,fontsize=8,ncol=3,handlelength=1.3)
        fig.tight_layout(pad=.55)
        fig.savefig(plots/(c['id']+'.svg'));fig.savefig(plots/(c['id']+'.png'));plt.close(fig)
        row={**c,'variants':vs,'source':anchor(*SOURCE[c['id']]),'observation':note(c,vs),'plot':'plots/'+c['id']+'.svg',
             'comparison_status':'observed_in_this_minimal_case','reference_kind':'exact linear backward-Euler recurrence' if c['id']=='iterations' else ('continuous undamped oscillator; not same discretization' if c['id']=='substeps' else None)}
        rows.append(row)
    save(HERE/'report-data.json',{'environment':read(HERE/'environment.json'),'experiments':rows})
    with (HERE/'metrics.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['experiment','variant','parameter','value','metric','unit','final','tail_mean','min','max','step_ms_median_after_warmup','steps'])
        w.writeheader()
        for r in rows:
            for v in r['variants']:w.writerow({'experiment':r['id'],'variant':v['variant'],'parameter':r['parameter'],'value':v['value'],'metric':r['metric'],'unit':r['unit'],**{k:v['metrics'][k] for k in ['final','tail_mean','min','max','step_ms_median_after_warmup','steps']}})
    print(json.dumps({'experiments':len(rows),'variants':2*len(rows),'iterations_rmse_mm':[v['metrics']['reference_rmse_mm'] for v in next(r for r in rows if r['id']=='iterations')['variants']]},ensure_ascii=False))

if __name__=='__main__':main()
