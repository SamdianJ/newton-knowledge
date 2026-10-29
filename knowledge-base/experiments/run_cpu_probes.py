"""Small release-specific behavioral probes; not a solver benchmark or real2sim validation."""
from pathlib import Path
import hashlib, importlib.metadata, json, platform, sys, warnings
import numpy as np
import warp as wp
import newton

ROOT=Path(__file__).resolve().parents[1]
wp.init()
results=[]

def check(name, fn):
    try:
        details=fn()
        results.append({'id':name,'status':'passed','details':details})
    except Exception as exc:
        results.append({'id':name,'status':'failed','error':repr(exc)})

def particle_model():
    b=newton.ModelBuilder(gravity=(0.,0.,0.))
    b.add_particle(pos=(1.,0.,0.),vel=(0.,0.,0.),mass=1.)
    b.color()
    return b.finalize(device='cpu')

def modes():
    b=newton.ModelBuilder(gravity=(0.,0.,0.))
    b.add_body(mass=1.)
    b.color()
    m=b.finalize(device='cpu')
    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter('always')
        old=newton.solvers.SolverVBD(m)
    new=newton.solvers.SolverVBD(m,rigid_compliant_alm=True)
    assert old.rigid_compliant_alm is False and new.rigid_compliant_alm is True
    assert abs(old.rigid_joint_alpha-.95)<1e-7 and new.rigid_joint_alpha==0.
    return {'omitted_mode':old.rigid_compliant_alm,'omitted_alpha':old.rigid_joint_alpha,'compliant_alpha':new.rigid_joint_alpha,'warnings':[str(w.message) for w in ws]}

def margins():
    m=particle_model()
    s=newton.solvers.SolverVBD(m,particle_enable_self_contact=True,particle_self_contact_margin=.005,particle_self_contact_gap=.005)
    assert abs(s._self_contact_query_radius-.01)<1e-8
    try:
        newton.solvers.SolverVBD(m,particle_enable_self_contact=True,particle_self_contact_margin=.005)
    except ValueError as exc:
        return {'new_margin':s.particle_self_contact_margin,'gap':s.particle_self_contact_gap,'query_radius':s._self_contact_query_radius,'margin_only_error':str(exc)}
    raise AssertionError('margin-only compatibility case should reject')

def spring_step():
    # 1-D motion, one anchored endpoint, no gravity/contact/damping; exact implicit Euler reference.
    b=newton.ModelBuilder(gravity=(0.,0.,0.))
    b.add_particle(pos=(0.,0.,0.),vel=(0.,0.,0.),mass=0.)
    b.add_particle(pos=(1.,0.,0.),vel=(0.,0.,0.),mass=1.)
    b.add_spring(0,1,ke=100.,kd=0.,control=0.)
    b.color()
    m=b.finalize(device='cpu')
    a,z=m.state(),m.state()
    q=a.particle_q.numpy();q[1,0]=1.2;a.particle_q.assign(q)
    solver=newton.solvers.SolverVBD(m,iterations=10,particle_enable_tile_solve=False)
    dt=.01
    expected=(1.2+dt*dt*100.*1.)/(1.+dt*dt*100.)
    solver.step(a,z,m.control(),None,dt)
    got=float(z.particle_q.numpy()[1,0])
    np.testing.assert_allclose(got,expected,atol=2e-6,rtol=0)
    np.testing.assert_allclose(z.particle_q.numpy()[0],[0,0,0],atol=1e-7)
    return {'dt':dt,'mass':1.,'stiffness':100.,'rest_length':1.,'initial_x':1.2,'expected_implicit_euler_x':expected,'actual_x':got,'absolute_error':abs(got-expected),'contact':False,'scope':'single linearized 1D spring step only'}

def guards():
    m=particle_model(); evidence=[]
    for kwargs in [{'dat_conservative_bound_relaxation':1.0},{'rigid_avbd_beta':-1.0},{'particle_self_contact_radius':.01,'particle_self_contact_gap':.01}]:
        try: newton.solvers.SolverVBD(m,**kwargs)
        except ValueError as exc: evidence.append({'input':kwargs,'error':str(exc)})
        else: raise AssertionError(f'Expected rejection: {kwargs}')
    return evidence

check('exp:default_modes',modes)
check('exp:margin_compatibility',margins)
check('exp:implicit_spring',spring_step)
check('exp:constructor_guards',guards)
installed=Path(newton.__file__).parent/'_src/solvers/vbd/solver_vbd.py'
snapshot=ROOT/'sources/newton-v1.7.0/newton/_src/solvers/vbd/solver_vbd.py'
same=installed.read_bytes()==snapshot.read_bytes()
report={'date':'2026-10-27','device':'cpu','python':sys.version,'platform':platform.platform(),'newton':importlib.metadata.version('newton'),'warp':wp.__version__,'numpy':np.__version__,'installed_solver_sha256':hashlib.sha256(installed.read_bytes()).hexdigest(),'solver_matches_pinned_snapshot':same,'tests':results,'scope_limit':'No GPU/tile performance, dense contact, DAT safety, trajectory fitting or real-world validation.'}
(ROOT/'experiments/results.cpu.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
sys.exit(0 if same and all(x['status']=='passed' for x in results) else 1)
