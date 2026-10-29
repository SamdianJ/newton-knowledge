"""Measured A/B experiments for official Newton 1.7.0; no visual motion is synthesized.

Each case changes only its declared treatment keys. All numerical states are exported.
Run: .venv/Scripts/python.exe -X utf8 experiments/vbd_parameter_lab/run_lab.py [--case ID]
"""
from pathlib import Path
import argparse, hashlib, importlib.metadata, json, platform, time, traceback, warnings
import numpy as np
import warp as wp
import newton

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SHA='7e75abe28b8d69522bc0b34837aaed2c303dff5a'
BASE=f'https://github.com/newton-physics/newton/blob/{SHA}/'
GUIDE='https://newton-physics.github.io/newton/latest/concepts/simulation_tuning.html'
VBD='https://newton-physics.github.io/newton/latest/concepts/simulation_tuning_vbd.html'
COLLISIONS='https://newton-physics.github.io/newton/latest/concepts/collisions.html'

def case(id,title,group,scene,parameter,a,b,duration,common,question,expectation,metric,unit,guide=GUIDE):
    return dict(id=id,title=title,group=group,scene=scene,parameter=parameter,values=[a,b],duration=duration,common=common,
        question=question,expectation=expectation,metric=metric,unit=unit,guide_url=guide)

CASES=[
 case('full_surface','粗三角形能托住小球吗？','碰撞管线','full_surface','enable_rigid_soft_full_surface_contact',False,True,.4,{},
      '顶点没有碰到球，三角形内部接触是否仍被求解？','开启后应出现 edge/face 接触；仅粒子检测可能漏掉面内接触。','球底相对支撑面的高度','mm',COLLISIONS),
 case('iterations','弹簧链：求解预算','数值求解','chain','iterations',1,30,.4,{'ke':2000.,'kd':0.,'dt':1/240},
      '同一物理材料，少迭代是否产生更大的有限求解误差？','增加迭代改善收敛；不应被解释成材料刚度改变。','末端高度','mm'),
 case('substeps','高频振子：时间步与数值耗散','时间积分','oscillator','substeps',1,8,.8,{'ke':900.,'kd':0.,'frame_dt':1/30,'iterations':10},
      '相同物理时间，细分时间步如何影响振幅和相位？','更小 dt 降低时间离散误差，但计算量增加；并非单纯多做外迭代。','弹簧伸长','mm'),
 case('stiffness','悬挂质量：材料刚度','材料','hanging','spring_stiffness',50.,500.,2.,{'kd':10.,'iterations':10,'dt':1/120},
      '已知 1 kg 载荷，静态伸长是否随刚度降低？','线性弹簧静态平衡预期伸长 mg/k；这属于材料层参数。','弹簧伸长','mm'),
 case('damping','自由振动：材料阻尼','材料','oscillator','spring_damping',0.,8.,1.5,{'ke':100.,'dt':1/240,'iterations':10},
      '刚度相同，阻尼如何改变衰减速度？','增大阻尼耗散运动能；不应与数值耗散混为一个参数。','弹簧伸长','mm'),
 case('self_contact','两张三角薄片的接触','自接触','sheets','particle_enable_self_contact',False,True,.45,{'dt':1/120,'iterations':15,'margin':.01,'gap':.08},
      '没有刚体形状时，软体之间是否还会发生接触？','粒子自接触检测与 rigid-soft 管线不同；开关控制软体 vertex-triangle/edge-edge 处理。','上片中心离下片距离','mm',VBD),
 case('self_margin','自接触厚度：显式 margin + gap','自接触','sheets','particle_self_contact_margin',.005,.04,.45,{'dt':1/120,'iterations':15,'gap':.08,'self_contact':True},
      '候选检测 slack 相同，交互距离如何影响停靠间距？','新语义需显式 gap；margin 改交互距离，不能拿 margin 当纯检测范围。','上片中心离下片距离','mm',VBD),
 case('contact_stiffness','软粒子落地：法向刚度','接触材料','particle_ground','contact_ke',500.,50000.,1.,{'dt':1/240,'iterations':10,'kd':30.,'mu':0.},
      '同样的重力载荷，接触刚度如何改变静态压入量？','二次 penalty 接触的有限刚度会产生法向压入；不能只看动画是否“站稳”。','粒子表面离地高度','mm'),
 case('friction','滑块粒子：摩擦系数','接触材料','particle_slide','contact_mu',.05,.8,1.,{'dt':1/240,'iterations':10,'ke':50000.,'kd':50.,'epsilon':.001,'speed':1.},
      '法向接触相同，摩擦系数如何改变停止距离？','mu 控制摩擦强度；同时固定摩擦平滑阈值和接触材料混合设置。','水平位移','mm'),
 case('friction_epsilon','小推力：摩擦平滑与蠕滑','摩擦正则','particle_creep','friction_epsilon',.001,.2,1.,{'dt':1/240,'iterations':10,'ke':50000.,'kd':50.,'mu':.5,'push':1.},
      'mu 相同，小速度区间的正则化是否改变缓慢滑动？','epsilon 是速度阈值，内核以 epsilon*dt 转为位移阈值；不是 mu。','水平位移','mm',VBD),
 case('dat','高速质点撞薄板：DAT','几何截断','dat','rigid_soft_enable_dat',False,True,.15,{'dt':1/60,'iterations':3,'ke':100.,'kd':0.,'speed':-8.},
      '弱 penalty + 大位移下，DAT 是否限制穿越接触面？','owned pipeline 提供检测时刻参考，DAT 限制位移；效果仍依赖初态和候选覆盖。','质点离板顶高度','mm',COLLISIONS),
 case('dat_relaxation','同一 DAT：保守系数','几何截断','dat','dat_conservative_bound_relaxation',.25,.85,.15,{'dt':1/60,'iterations':3,'ke':100.,'kd':0.,'speed':-8.,'dat':True},
      '都启用 DAT，较保守系数怎样改变运动进度？','系数在 (0,1)，影响截断与运动预算；更保守不等于更真实。','质点离板顶高度','mm',VBD),
 case('rigid_mode','有限刚度关节：legacy / compliant','刚体约束','joint','rigid_compliant_alm',False,True,1.,{'dt':1/120,'iterations':15,'joint_ke':200.,'joint_kd':15.,'alpha':0.},
      '相同结构 ke，切换 formulation 会不会改变静态柔顺性？','compliant 把物理 K 与数值 rho 分开；legacy hard 行与有限刚度 ALM 不物理等价。','关节平移误差','mm',VBD),
 case('joint_stiffness','compliant 关节的结构刚度','刚体约束','joint','rigid_joint_linear_ke',200.,2000.,1.,{'dt':1/120,'iterations':15,'joint_kd':20.,'alpha':0.,'compliant':True},
      'compliant 模式下物理刚度是否控制载荷下的变形？','结构 ke 与 drive ke 分层；有限材料刚度应在静态响应中可见。','关节平移误差','mm',VBD),
 case('membrane','薄膜三角形：面内拉伸','薄膜材料','membrane','tri_ke + tri_ka',100.,10000.,1.,{'dt':1/240,'iterations':15,'tri_kd':20.},
      '固定上边、给下顶点相同载荷，膜材料系数如何改变伸长？','膜参数进入三角形能量；此处共同缩放两项，未声称单独识别剪切与面积响应。','下顶点下移量','mm',VBD),
 case('bending','双三角形铰链：弯曲刚度','薄膜材料','bending','edge_ke',.01,10.,2.,{'dt':1/240,'iterations':20,'edge_kd':.1,'tri_ke':10000.},
      '面内材料相同，二面角弯曲项怎样抵抗自由翼下垂？','edge_ke 控制二面角弯曲；固定网格下比较，不把离散系数当作直接测得的真实材料模量。','自由翼下移量','mm',VBD),
 case('stabilization','初始关节误差：alpha','刚体约束','joint','rigid_avbd_alpha',0.,.95,.5,{'dt':1/120,'iterations':15,'joint_ke':2000.,'joint_kd':5.,'compliant':True,'initial_offset':-.03,'gravity':False},
      '相同初始错位，误差稳定化是否改变纠正速度？','alpha 控制 C-alpha*C0 中的既存误差处理；它不是物理刚度。','关节平移误差','mm',VBD),
]

def T(x,y,z):return wp.transform(wp.vec3(x,y,z),wp.quat_identity())
def body(builder,pos,mass=.5,radius=.08,linked=False):
    inertia=wp.mat33(*np.diag([.4*mass*radius**2]*3).ravel().tolist())
    fn=builder.add_link if linked else builder.add_body
    return fn(xform=T(*pos),mass=mass,inertia=inertia,lock_inertia=True)

def build(c,value):
    cfg=c['common'].copy();key=c['parameter'];cfg[key]=value;scene=c['scene']
    b=newton.ModelBuilder(gravity=(0.,0.,0.));b.default_shape_cfg.density=0.
    dt=cfg.get('dt',cfg.get('frame_dt',1/120)/cfg.get('substeps',1))
    kwargs=dict(iterations=cfg.get('iterations',10),particle_enable_tile_solve=False,rigid_compliant_alm=cfg.get('rigid_compliant_alm',cfg.get('compliant',True)))
    pipeline_kwargs={};initial=None;force=None;visual=dict(view='xz',body_shapes=[],triangles=[],springs=[],fixed=[],floor=None)
    if scene in ('oscillator','hanging','chain'):
        ke=cfg.get('spring_stiffness',cfg.get('ke',100.));kd=cfg.get('spring_damping',cfg.get('kd',0.))
        if scene=='chain':
            b.gravity=(0.,0.,-9.81)
            for i in range(16):b.add_particle((0.,0.,1.-i*.045),(0.,0.,0.),0. if i==0 else .1,radius=.007)
            for i in range(15):b.add_spring(i,i+1,ke=ke,kd=kd,control=0.)
            visual['fixed']=[0];visual['springs']=[[i,i+1] for i in range(15)]
        else:
            b.add_particle((0.,0.,.6),(0.,0.,0.),0.,radius=.015)
            b.add_particle((0.,0.,.3),(0.,0.,0.),1.,radius=.03)
            b.add_spring(0,1,ke=ke,kd=kd,control=0.)
            visual.update(fixed=[0],springs=[[0,1]])
            if scene=='oscillator':initial=np.array([[0,0,.6],[0,0,.18]],dtype=np.float32)
            else:b.gravity=(0.,0.,-9.81)
    elif scene=='full_surface':
        b.gravity=(0.,0.,-9.81)
        for p in [(-.3,-.3,0),(.3,-.3,0),(0,.3,0)]:b.add_particle(wp.vec3(*p),wp.vec3(0.),0.,radius=0.)
        b.add_triangle(0,1,2)
        bid=body(b,(0,0,.14),radius=.1)
        b.default_shape_cfg.ke=20000.;b.default_shape_cfg.kd=100.;b.default_shape_cfg.mu=0.
        b.add_shape_sphere(bid,radius=.1)
        visual.update(view='iso',fixed=[0,1,2],triangles=[[0,1,2]],body_shapes=[dict(body=bid,type='sphere',radius=.1)])
        pipeline_kwargs=dict(broad_phase='nxn',soft_contact_gap=.06,enable_rigid_soft_full_surface_contact=value)
    elif scene=='sheets':
        b.gravity=(0.,0.,-9.81)
        for p in [(-.4,-.4,0),(.4,-.4,0),(.4,.4,0),(-.4,.4,0)]:b.add_particle(wp.vec3(*p),wp.vec3(0.),0.,radius=.004)
        for p in [(-.1,-.1,.16),(.1,-.1,.16),(.1,.1,.16),(-.1,.1,.16)]:b.add_particle(wp.vec3(*p),wp.vec3(0.),.05,radius=.004)
        for offset in [0,4]:
            b.add_triangle(offset,offset+1,offset+2,tri_ke=2000.,tri_ka=2000.,tri_kd=2.)
            b.add_triangle(offset,offset+2,offset+3,tri_ke=2000.,tri_ka=2000.,tri_kd=2.)
            b.add_edge(offset+1,offset+3,offset,offset+2,edge_ke=1.,edge_kd=.01)
        kwargs.update(particle_enable_self_contact=cfg.get('particle_enable_self_contact',cfg.get('self_contact',True)),particle_self_contact_margin=cfg.get('particle_self_contact_margin',cfg.get('margin',.01)),particle_self_contact_gap=cfg.get('gap',.08))
        visual.update(view='iso',triangles=[[0,1,2],[0,2,3],[4,5,6],[4,6,7]],fixed=[0,1,2,3])
    elif scene in ('particle_ground','particle_slide','particle_creep','dat'):
        b.gravity=(0,0,-9.81) if scene!='dat' else (0,0,0)
        ke=cfg.get('contact_ke',cfg.get('ke',10000.));mu=cfg.get('contact_mu',cfg.get('mu',0.));kd=cfg.get('kd',30.)
        b.default_shape_cfg.ke=ke;b.default_shape_cfg.kd=kd;b.default_shape_cfg.mu=mu
        radius=.025;z=.08 if scene=='particle_ground' else radius
        vel=(cfg.get('speed',0.) if scene=='particle_slide' else 0.,0.,0.)
        if scene=='dat':
            z=.12;vel=(0,0,cfg['speed']);radius=0.
            b.add_shape_box(body=-1,xform=T(0,0,-.02),hx=.4,hy=.4,hz=.02)
            visual['slab']=[-.4,.4,-.04,0.]
            pipeline_kwargs=dict(broad_phase='nxn',soft_contact_gap=.2)
            kwargs.update(rigid_soft_enable_dat=cfg.get('rigid_soft_enable_dat',cfg.get('dat',False)),dat_conservative_bound_relaxation=cfg.get('dat_conservative_bound_relaxation',.85))
        else:
            b.add_ground_plane();pipeline_kwargs=dict(broad_phase='nxn',soft_contact_gap=.08)
            visual['floor']=0.
        b.add_particle((0,0,z),vel,1.,radius=radius)
        kwargs['friction_epsilon']=cfg.get('friction_epsilon',cfg.get('epsilon',.01))
        if scene=='particle_creep':force=np.array([[cfg['push'],0,0]],np.float32)
    elif scene in ('membrane','bending'):
        b.gravity=(0,0,-9.81)
        if scene=='membrane':
            for p,mass in [((-.15,0,.45),0.),((.15,0,.45),0.),((0,0,.15),.5)]:b.add_particle(wp.vec3(*p),wp.vec3(0.),mass,radius=.008)
            k=cfg['tri_ke + tri_ka'];b.add_triangle(0,2,1,tri_ke=k,tri_ka=k,tri_kd=cfg['tri_kd'])
            visual.update(triangles=[[0,2,1]],fixed=[0,1])
        else:
            for p,mass in [((-.25,0,.4),0.),((.25,0,.4),.2),((0,-.15,.4),0.),((0,.15,.4),0.)]:b.add_particle(wp.vec3(*p),wp.vec3(0.),mass,radius=.008)
            b.add_triangle(0,2,3,tri_ke=cfg['tri_ke'],tri_ka=cfg['tri_ke'],tri_kd=5.)
            b.add_triangle(1,3,2,tri_ke=cfg['tri_ke'],tri_ka=cfg['tri_ke'],tri_kd=5.)
            b.add_edge(0,1,2,3,edge_ke=cfg['edge_ke'],edge_kd=cfg['edge_kd'])
            visual.update(view='iso',triangles=[[0,2,3],[1,3,2]],fixed=[0,2,3])
    elif scene=='joint':
        b.gravity=(0,0,-9.81) if cfg.get('gravity',True) else (0,0,0)
        bid=body(b,(0,0,.35),mass=1.,radius=.055,linked=True)
        j=b.add_joint_fixed(-1,bid,parent_xform=T(0,0,.35));b.add_articulation([j])
        kwargs.update(rigid_joint_linear_ke=cfg.get('rigid_joint_linear_ke',cfg.get('joint_ke',200.)),rigid_joint_linear_kd=cfg.get('joint_kd',15.),rigid_avbd_alpha=cfg.get('rigid_avbd_alpha',cfg.get('alpha',0.)))
        visual.update(body_shapes=[dict(body=bid,type='sphere',radius=.055)],anchor=[0,0,.35])
    else:raise ValueError(scene)
    b.color();m=b.finalize(device='cpu')
    if scene in ('particle_ground','particle_slide','particle_creep','dat'):
        m.soft_contact_ke=ke;m.soft_contact_kd=kd;m.soft_contact_mu=mu
    if scene=='full_surface':m.soft_contact_ke=20000.;m.soft_contact_kd=100.;m.soft_contact_mu=0.
    if scene=='sheets':m.soft_contact_ke=30000.;m.soft_contact_kd=50.;m.soft_contact_mu=0.
    pipeline=newton.CollisionPipeline(m,**pipeline_kwargs) if pipeline_kwargs else None
    if pipeline:kwargs['collision_pipeline']=pipeline
    solver=newton.solvers.SolverVBD(m,**kwargs)
    s0,s1=m.state(),m.state()
    if initial is not None:s0.particle_q.assign(initial)
    if scene=='joint' and 'initial_offset' in cfg:
        q=s0.body_q.numpy();q[0,2]+=cfg['initial_offset'];s0.body_q.assign(q)
    visual['particle_radii']=m.particle_radius.numpy().tolist() if m.particle_count else []
    config={'solver':{k:v for k,v in kwargs.items() if k!='collision_pipeline'},'pipeline':pipeline_kwargs,'common':c['common'],'treatment':{key:value},'dt':dt,'duration':c['duration'],'gravity':list(b.gravity),
       'model_counts':{'particles':m.particle_count,'bodies':m.body_count,'triangles':m.tri_count,'springs':m.spring_count},'particle_mass':m.particle_mass.numpy().tolist() if m.particle_count else [],'body_mass':m.body_mass.numpy().tolist() if m.body_count else [],'seed':'deterministic construction; no RNG'}
    return m,solver,s0,s1,dt,force,visual,config

def run_variant(c,value,tag):
    m,solver,s0,s1,dt,force,visual,config=build(c,value)
    times=[];positions=[];bodies=[];velocities=[];counts=[];durations=[]
    steps=round(c['duration']/dt)
    def save(t):
        times.append(t);positions.append(s0.particle_q.numpy().copy() if m.particle_count else np.empty((0,3),np.float32))
        bodies.append(s0.body_q.numpy().copy() if m.body_count else np.empty((0,7),np.float32))
        velocities.append(s0.particle_qd.numpy().copy() if m.particle_count else np.empty((0,3),np.float32))
        con=solver.contacts
        if con is not None:
            n=min(int(con.soft_contact_count.numpy()[0]),con.soft_contact_max)
            idx=con.soft_contact_indices.numpy()[:n]
            counts.append([n,int(np.sum(idx[:,1]>=0)),int(con.rigid_contact_count.numpy()[0])])
        else:counts.append([0,0,0])
    save(0.)
    for step in range(steps):
        s0.clear_forces()
        if force is not None:s0.particle_f.assign(force)
        begin=time.perf_counter();solver.step(s0,s1,None,None,dt);wp.synchronize_device('cpu');durations.append(time.perf_counter()-begin)
        s0,s1=s1,s0;save((step+1)*dt)
        if not (np.isfinite(positions[-1]).all() and np.isfinite(bodies[-1]).all()):raise RuntimeError('non-finite state')
    p=np.asarray(positions);q=np.asarray(bodies);v=np.asarray(velocities);t=np.asarray(times);cnt=np.asarray(counts)
    scene=c['scene']
    if scene in ('oscillator','hanging'):series=(np.linalg.norm(p[:,1]-p[:,0],axis=1)-.3)*1000
    elif scene=='chain':series=p[:,-1,2]*1000
    elif scene=='full_surface':series=(q[:,0,2]-.1)*1000
    elif scene=='sheets':series=p[:,4:,2].mean(axis=1)*1000
    elif scene in ('particle_slide','particle_creep'):series=p[:,0,0]*1000
    elif scene in ('particle_ground','dat'):series=(p[:,0,2]-visual['particle_radii'][0])*1000
    elif scene=='joint':series=(.35-q[:,0,2])*1000
    elif scene=='membrane':series=(.15-p[:,2,2])*1000
    elif scene=='bending':series=(.4-p[:,1,2])*1000
    metrics={'final':float(series[-1]),'min':float(series.min()),'max':float(series.max()),'tail_mean':float(series[max(1,int(len(series)*.8)):].mean()),
       'step_ms_median_after_warmup':float(np.median(durations[min(5,len(durations)-1):])*1000),'max_soft_contact_records':int(cnt[:,0].max()),'max_edge_face_records':int(cnt[:,1].max()),'finite':True,'steps':steps}
    if scene=='hanging':metrics['static_prediction_mm']=9.81/config['treatment'].get('spring_stiffness',cfg_ke(c))*1000
    if scene=='oscillator':
        stiffness=c['common'].get('ke',100.); extension=series/1000
        energy=.5*(v[:,1]**2).sum(axis=1)+.5*stiffness*extension**2
        metrics['final_energy_fraction']=float(energy[-1]/energy[0])
    folder=HERE/'data'/c['id'];folder.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(folder/f'{tag}.npz',time=t,particle_q=p,particle_qd=v,body_q=q,contacts=cnt,series=series,step_seconds=np.asarray(durations))
    stride=max(1,round((1/30)/dt));ix=np.unique(np.r_[np.arange(0,len(t),stride),len(t)-1])
    result={'variant':tag,'value':value,'config':config,'visual':visual,'metrics':metrics,'program_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'times':np.round(t[ix],7).tolist(),'particle_q':np.round(p[ix],7).tolist(),'body_q':np.round(q[ix],7).tolist(),
        'curve':{'time':np.round(t,7).tolist(),'value':np.round(series,7).tolist()},'contact_counts':cnt[ix].tolist(),'raw_file':f'data/{c["id"]}/{tag}.npz'}
    (folder/f'{tag}.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    return result

def cfg_ke(c):return c['common'].get('ke',100.)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--case',action='append');a=ap.parse_args()
    wp.init();chosen=[c for c in CASES if not a.case or c['id'] in a.case]
    failures=[]
    for c in chosen:
        for tag,value in zip(['A','B'],c['values']):
            print(f'RUN {c["id"]} {tag} {c["parameter"]}={value}',flush=True)
            try:
                with warnings.catch_warnings(record=True) as ws:
                    warnings.simplefilter('always');result=run_variant(c,value,tag)
                result['warnings']=[str(w.message) for w in ws]
                p=HERE/'data'/c['id']/f'{tag}.json';p.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
                print(json.dumps({'id':c['id'],'variant':tag,'metrics':result['metrics']},ensure_ascii=False),flush=True)
            except Exception as e:
                failures.append({'id':c['id'],'variant':tag,'error':repr(e)});traceback.print_exc()
    (HERE/'cases.json').write_text(json.dumps(CASES,ensure_ascii=False,indent=2),encoding='utf-8')
    installed=Path(newton.__file__).parent/'_src/solvers/vbd/solver_vbd.py';pinned=ROOT/'sources/newton-v1.7.0/newton/_src/solvers/vbd/solver_vbd.py'
    env={'date':'2026-10-27','newton':importlib.metadata.version('newton'),'warp':wp.__version__,'numpy':np.__version__,'python':platform.python_version(),'device':'cpu','platform':platform.platform(),'source_commit':SHA,'solver_file_sha256':hashlib.sha256(installed.read_bytes()).hexdigest(),'solver_file_matches_snapshot':installed.read_bytes()==pinned.read_bytes(),'failures':failures,'timing_scope':'CPU solver.step including owned collision, after first 5 steps; excludes numpy readback/rendering; not GPU benchmark'}
    (HERE/'environment.json').write_text(json.dumps(env,ensure_ascii=False,indent=2),encoding='utf-8')
    if failures:raise SystemExit(1)

if __name__=='__main__':main()
