"""Freeze PRD 0.2 scope, schemas, migration inventory and acceptance contracts.

This records targets and observed baseline separately. It does not publish planned
articles or mark any later phase complete.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import sqlite3
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'sources/newton-v1.7.0'
OUT = ROOT / 'planning/p0'
VERSION = '1.7.0'
COMMIT = '7e75abe28b8d69522bc0b34837aaed2c303dff5a'
STAGES = ['asset_import', 'preprocess', 'initialization', 'control', 'collision', 'solver_step', 'output']
SOLVERS = ['vbd', 'mujoco', 'kamino', 'featherstone', 'implicit-mpm', 'semi-implicit', 'style3d', 'xpbd']


def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def write(path, value):
    path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def exports(path):
    tree = ast.parse((SRC / path).read_text(encoding='utf-8'))
    imports={}
    for node in tree.body:
        if isinstance(node,ast.ImportFrom) and node.level:
            base=(SRC/path).parent
            for _ in range(node.level-1):
                base=base.parent
            if node.module:
                base=base.joinpath(*node.module.split('.'))
            for alias in node.names:
                target=base/alias.name
                resolved=target.with_suffix('.py') if target.with_suffix('.py').is_file() else target/'__init__.py'
                if resolved.is_file():imports[alias.asname or alias.name]=resolved.relative_to(SRC).as_posix()
    def literal(node):
        if isinstance(node,ast.Constant) and isinstance(node.value,str):return node.value
        if isinstance(node,(ast.List,ast.Tuple)):
            result=[]
            for element in node.elts:
                if isinstance(element,ast.Starred):result.extend(literal(element.value))
                else:result.append(literal(element))
            return result
        if isinstance(node,ast.Attribute) and node.attr=='__all__' and isinstance(node.value,ast.Name) and node.value.id in imports:
            return exports(imports[node.value.id])
        if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Add):return literal(node.left)+literal(node.right)
        raise ValueError('Unsupported static __all__ expression in '+path+': '+ast.unparse(node))
    result=[]
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == '__all__' for t in node.targets):
            result=literal(node.value)
        elif isinstance(node,ast.AugAssign) and isinstance(node.target,ast.Name) and node.target.id=='__all__' and isinstance(node.op,ast.Add):
            result+=literal(node.value)
    return result


def entry(key, family, title, source, target, stages, module, aliases=None):
    if not (SRC / source).is_file():
        raise FileNotFoundError(source)
    return {'id': key, 'family': family, 'title': title, 'source_path': source, 'owner_module': module,
            'stages': stages, 'target_depth': target, 'observed_depth': 'not_curated', 'phase': 'P2',
            'aliases': aliases or [], 'canonical_path': 'knowledge/pages/' + key.replace(':', '/') + '.md',
            'deferred': '首版按目标深度交付；逐符号教程和额外物理实验按任务扩充。'}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    prd = (ROOT / 'planning/PRD.md').read_bytes()
    head = subprocess.check_output(['git', '-C', str(SRC), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = subprocess.check_output(['git', '-C', str(SRC), 'status', '--porcelain'], text=True).strip()
    if head != COMMIT or dirty:
        raise ValueError('Pinned source HEAD or working-tree integrity mismatch')
    tracked = subprocess.check_output(['git', '-C', str(SRC), 'ls-files', '-z']).decode('utf-8').split('\0')
    files = {p: hashlib.sha256((SRC / p).read_bytes()).hexdigest() for p in tracked if p and (SRC / p).is_file()}
    write('manifests/source-lock.json', {'version': VERSION, 'commit': COMMIT, 'verified_clean_git': True, 'files': files})
    modules = [
        ('newton', '核心对象与生命周期', 'newton/__init__.py', 'E', ['initialization', 'control', 'collision', 'solver_step']),
        ('actuators', '执行器与驱动', 'newton/actuators.py', 'E', ['control']),
        ('controllers', '机器人控制器', 'newton/controllers.py', 'E', ['control']),
        ('geometry', '几何与碰撞工具', 'newton/geometry.py', 'E', ['preprocess', 'collision']),
        ('ik', '逆运动学', 'newton/ik.py', 'E', ['initialization', 'control']),
        ('math', '空间数学与坐标', 'newton/math.py', 'I', ['preprocess', 'control', 'solver_step']),
        ('selection', '批量对象选择', 'newton/selection.py', 'E', ['initialization', 'control']),
        ('sensors', '传感器与量测', 'newton/sensors.py', 'E', ['initialization', 'output']),
        ('solvers', '求解器接口与后端', 'newton/solvers.py', 'E', ['solver_step']),
        ('usd', 'USD 资产与 Schema', 'newton/usd.py', 'E', ['asset_import', 'preprocess']),
        ('utils', '预处理与开发工具', 'newton/utils.py', 'I', ['preprocess', 'output']),
        ('viewer', '查看 记录与导出', 'newton/viewer.py', 'E', ['output']),
    ]
    registry = []
    api = {}
    for name, title, path, depth, stages in modules:
        module = 'newton' if name == 'newton' else 'newton.' + name
        item = entry('module:' + name, 'api', title, path, depth, stages, module, [module])
        item['public_exports'] = exports(path)
        api[module] = item['public_exports']
        registry.append(item)
    concepts = [
        ('worlds', 'Worlds 与批量场景', 'worlds', ['initialization', 'control']),
        ('articulations', '关节与机械系统', 'articulations', ['asset_import', 'initialization', 'solver_step']),
        ('deformables', '可变形体与离散化', 'deformable_objects', ['preprocess', 'solver_step']),
        ('mass-inertia', '质量 惯量与质心', 'mass_inertia', ['preprocess', 'solver_step']),
        ('sites', 'Sites 与参考坐标', 'sites', ['initialization', 'output']),
        ('sensors', '传感器生命周期', 'sensors', ['initialization', 'output']),
        ('conventions', '单位 坐标与布局约定', 'conventions', STAGES),
        ('usd-parsing', 'USD 解析与 Schema', 'usd_parsing', ['asset_import']),
        ('custom-attributes', '自定义属性与注册', 'custom_attributes', ['initialization', 'solver_step']),
        ('solver-observables', '求解器观测资源', 'solver_observables', ['initialization', 'solver_step', 'output']),
        ('collisions', '碰撞与 Contacts', 'collisions', ['preprocess', 'collision', 'solver_step']),
        ('simulation-tuning', '仿真调参与诊断', 'simulation_tuning', ['control', 'collision', 'solver_step', 'output']),
        ('coupling', '多求解器耦合', 'coupling', ['initialization', 'collision', 'solver_step']),
        ('actuators', '执行器组合与控制', 'actuators', ['control', 'solver_step']),
    ]
    for key, title, filename, stages in concepts:
        registry.append(entry('concept:' + key, 'concept', title, 'docs/concepts/' + filename + '.rst', 'E', stages, 'newton'))
    catalog = read('site/dist/catalog.json')
    graph = read('site/dist/graph.json')
    old_solver_ids = {n.get('solver', 'vbd'): n['id'] for n in graph['nodes'] if n['type'] == 'solver'}
    for slug, class_name in [('vbd','SolverVBD'),('mujoco','SolverMuJoCo'),('kamino','SolverKamino'),('featherstone','SolverFeatherstone'),('implicit-mpm','SolverImplicitMPM'),('semi-implicit','SolverSemiImplicit'),('style3d','SolverStyle3D'),('xpbd','SolverXPBD')]:
        item = entry('solver:' + slug, 'solver', class_name, 'newton/solvers.py', 'E' if slug in catalog['solvers'] else 'I', ['solver_step'], 'newton.solvers', [class_name] + ([old_solver_ids[slug]] if slug in old_solver_ids else []))
        item.update(solver=slug, public_class=class_name, observed_depth='explained' if slug in catalog['solvers'] else 'not_curated',
                    existing_experiment_count=len(catalog['solvers'].get(slug, {}).get('experiments', [])))
        registry.append(item)
    topics = [
        ('robot-control', '运动学与机器人控制', 'newton/controllers.py', ['initialization','control'], 'T'),
        ('worlds-batching', 'Worlds 与批量复位', 'docs/concepts/worlds.rst', ['initialization','control','solver_step'], 'T'),
        ('coupling', '刚体与可变形体耦合', 'docs/concepts/coupling.rst', ['initialization','collision','solver_step'], 'T'),
        ('differentiable-simulation', '可微仿真', 'docs/solvers/index.rst', ['initialization','solver_step'], 'E'),
        ('lifecycle-observation', '生命周期 复位与量测', 'docs/concepts/solver_observables.rst', ['initialization','solver_step','output'], 'T'),
        ('environment', '环境与兼容', 'docs/guide/compatibility.rst', ['initialization'], 'E'),
        ('development-testing', '开发规范与 Newton 测试', 'docs/guide/development.rst', [], 'E'),
        ('migration-integrations', '版本迁移与外部集成', 'docs/migration.rst', [], 'I'),
    ]
    for key, title, path, stages, depth in topics:
        registry.append(entry('topic:' + key, 'topic', title, path, depth, stages, 'newton'))
    workflow = [
        ('asset_import','资产导入','docs/guide/overview.rst'),('preprocess','构建与预处理','docs/concepts/collisions.rst'),
        ('initialization','Model 与运行时初始化','docs/guide/overview.rst'),('control','Control 与外力','docs/concepts/actuators.rst'),
        ('collision','碰撞检测与 Contacts','docs/concepts/collisions.rst'),('solver_step','Solver step 与状态推进','docs/solvers/index.rst'),
        ('output','观测 记录 导出与渲染','docs/guide/visualization.rst'),
    ]
    for key,title,path in workflow:
        registry.append(entry('stage:' + key, 'stage', title, path, 'E', [key], 'newton'))
    recipes = [
        ('external-collision','外部碰撞与步进','docs/concepts/solver_observables.rst',['initialization','collision','solver_step','output']),
        ('solver-owned-collision','Solver 持有碰撞资源','docs/concepts/solver_observables.rst',['initialization','collision','solver_step','output']),
        ('mujoco-native-contact','MuJoCo 原生接触量测','docs/concepts/solver_observables.rst',['initialization','collision','solver_step','output']),
        ('coupled-rigid-deformable','刚体与 VBD 耦合方案','docs/concepts/coupling.rst',['initialization','collision','solver_step']),
        ('ik-mujoco-contact','多机器人 IK 控制与接触力','docs/concepts/sensors.rst',['asset_import','initialization','control','solver_step','output']),
        ('worlds-reset','批量选择与复位','docs/concepts/worlds.rst',['initialization','control','solver_step']),
    ]
    for key,title,path,stages in recipes:
        registry.append(entry('recipe:' + key, 'recipe', title, path, 'T', stages, 'newton'))
    for item in registry:
        item['source_refs'] = [{'path':item['source_path'],'line':1,'commit':COMMIT,'sha256':files[item['source_path']],
                               'url':f"https://github.com/newton-physics/newton/blob/{COMMIT}/{item['source_path']}"}]
    payload = {'schema_version':'2.0','version':VERSION,'commit':COMMIT,'prd_sha256':hashlib.sha256(prd).hexdigest(),
               'stages':STAGES,'solver_keys':SOLVERS,'entries':registry,'counts':{family:sum(e['family']==family for e in registry) for family in ['api','concept','solver','topic','stage','recipe']}}
    write('knowledge/registry.json', payload)
    write('planning/p0/public-exports.json', api)
    # Every baseline ID and route is frozen, including duplicates that later become explicit aliases.
    with sqlite3.connect((ROOT/'site/data/site.sqlite').as_uri()+'?mode=ro',uri=True) as con:
        con.row_factory=sqlite3.Row
        old_records=[dict(r) for r in con.execute('SELECT id,kind,title,route,solver FROM records ORDER BY id')]
    snapshot={'version':VERSION,'commit':COMMIT,'counts':catalog['total_counts'],'search_records':old_records,
              'documents':catalog['documents'],'parameter_ids':[p['id'] for c in catalog['solvers'].values() for p in c['parameters']],
              'graph_ids':[n['id'] for n in graph['nodes']], 'experiments':[]}
    for e in catalog['experiments']:
        refs=[ROOT/'experiments/vbd_parameter_lab'/v['raw_file'] for v in e['variants']]
        snapshot['experiments'].append({'id':e['record_id'],'case_id':e['id'],'solver':'vbd','files':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in refs}})
    baseline=OUT/'migration-baseline.json'
    if not baseline.exists():
        write('planning/p0/migration-baseline.json',snapshot)
    frozen=json.loads(baseline.read_text(encoding='utf-8'))
    migration=[]
    for row in frozen['search_records']:
        solver=row['solver'];kind=row['kind'];route=row['route']
        if kind=='parameter':target='#/solvers/'+solver+'/parameters/'+route.rsplit('/',1)[-1]
        elif kind=='model_input':target='#/solvers/'+solver+'/inputs/'+route.rsplit('/',1)[-1]
        elif kind=='lab_experiment':target='#/solvers/vbd/experiments?'+route.partition('?')[2]
        elif kind=='document':target='#/document/'+route.removeprefix('#doc/')
        elif kind=='paper':target='#/solvers/'+solver+'/papers'
        else:target='#/record/'+row['id']
        source='solvers/'+solver+'/' if solver in ('vbd','mujoco','kamino') else 'shared document'
        generators=['scripts/extract_sources.py','scripts/model_and_cases.py','scripts/curated.py','scripts/author_docs.py'] if solver=='vbd' else ['scripts/extend_solvers.py'] if solver in ('mujoco','kamino') else []
        if kind=='lab_experiment':source='experiments/vbd_parameter_lab/report-data.json';generators=['experiments/vbd_parameter_lab/analyze_lab.py','experiments/vbd_parameter_lab/build_report.py']
        if kind=='document':source=route.removeprefix('#doc/')
        migration.append({**row,'canonical_id':row['id'],'new_route':target,'authoring_source':source,'generators':generators,
                          'generated_artifact':'site/dist/catalog.json','index':'site/data/site.sqlite','alias_policy':'preserve ID or explicit alias to canonical record; never drop silently'})
    write('planning/p0/migration-map.json',{'records':migration,'graph_alias_policy':'Preserve all baseline graph IDs; any canonical merge requires an explicit alias.',
          'pipeline':['authoring source','generator','catalog and graph','SQLite','UI route and MCP read'],
          'legacy_routes':{'#home':'#/','#parameters':'#/solvers/vbd/parameters','#experiments':'#/solvers/vbd/experiments','#papers':'#/solvers/vbd/papers','#docs':'#/library'},
          'preserve_query_keys':['case','line','section','view','tab','q']})
    write('planning/p0/coverage-plan.json',payload)
    record_schema={'$schema':'https://json-schema.org/draft/2020-12/schema','title':'Newton knowledge canonical record','type':'object',
                   'required':['id','record_type','title','domain','stages','record_scope','owner_module','applicable_solvers','support_status','coverage','source_refs','version','commit'],
                   'properties':{'id':{'type':'string','minLength':1},'record_type':{'type':'string'},'title':{'type':'string'},
                    'domain':{'enum':['framework','workflow','solver','development']},'stages':{'type':'array','items':{'enum':STAGES},'uniqueItems':True},
                    'record_scope':{'enum':['shared','solver']},'owner_module':{'type':'string'},'owner_solver':{'type':['string','null']},
                    'applicable_solvers':{'type':'array','items':{'enum':SOLVERS},'uniqueItems':True},'support_status':{'enum':['supported','unsupported','unknown']},
                    'coverage':{'type':'object','required':['indexed','explained','task_validated','experiment_validated'],
                                'properties':{k:{'type':'boolean'} for k in ['indexed','explained','task_validated','experiment_validated']}},
                    'source_refs':{'type':'array','items':{'type':'object','required':['path','commit','sha256']}},
                    'version':{'const':VERSION},'commit':{'const':COMMIT}},'additionalProperties':True}
    write('planning/p0/record.schema.json',record_schema)
    tools={
        'search_knowledge':{'query':{'type':'string','minLength':1,'maxLength':300},'kind':{'type':'string','default':'all'},'domain':{'enum':['all','framework','workflow','solver','development'],'default':'all'},'stage':{'enum':['all']+STAGES,'default':'all'},'solver':{'enum':['all','shared']+SOLVERS,'default':'all'},'include_shared':{'type':'boolean','default':False},'limit':{'type':'integer','minimum':1,'maximum':20,'default':6},'cursor':{'type':['string','null'],'default':None}},
        'get_parameter':{'name':{'type':'string','default':''},'record_id':{'type':'string','default':''},'solver':{'enum':['shared']+SOLVERS,'default':'vbd'}},
        'get_experiment':{'experiment_id':{'type':'string'},'detail':{'enum':['summary','full'],'default':'summary'},'solver':{'enum':SOLVERS,'default':'vbd'}},
        'get_relations':{'node_id':{'type':'string'},'limit':{'type':'integer','minimum':1,'maximum':30,'default':12},'offset':{'type':'integer','minimum':0,'default':0},'cursor':{'type':['string','null'],'default':None},'edge_cursor':{'type':['string','null'],'default':None}},
        'get_document':{'path':{'type':'string','default':''},'record_id':{'type':'string','default':''},'section':{'type':'string','default':''},'start_line':{'type':'integer','minimum':1,'default':1},'max_lines':{'type':'integer','minimum':1,'maximum':200,'default':100},'limit':{'type':'integer','minimum':1,'maximum':100,'default':50},'cursor':{'type':['string','null'],'default':None},'include_outline':{'type':'boolean','default':False}},
        'get_source':{'path':{'type':'string','default':''},'symbol_id':{'type':'string','default':''},'start_line':{'type':'integer','minimum':1,'default':1},'max_lines':{'type':'integer','minimum':1,'maximum':200,'default':100},'scope':{'enum':['newton','experiment'],'default':'newton'}},
    }
    required={'search_knowledge':['query'],'get_parameter':[],'get_experiment':['experiment_id'],'get_relations':['node_id'],'get_document':[],'get_source':[]}
    contract={}
    for name, props in tools.items():
        props['version']={'type':'string','default':VERSION,'maxLength':32}
        contract[name]={'inputSchema':{'type':'object','properties':props,'required':required[name],'additionalProperties':False},
                        'outputSchema':{'type':'object','required':['status','version','source_commit','build_id','read_only','requested_scope','resolved_scope','applied_filters'],
                                        'properties':{'status':{'type':'string'},'version':{'const':VERSION},'source_commit':{'const':COMMIT},'build_id':{'type':'string'},'read_only':{'const':True},
                                                      'requested_scope':{'type':'object'},'resolved_scope':{'type':'object'},'applied_filters':{'type':'object'}},'additionalProperties':True},
                        'annotations':{'readOnlyHint':True,'destructiveHint':False,'idempotentHint':True,'openWorldHint':False}}
    write('planning/p0/mcp-contract.json',{'schema_version':'2.0','version':VERSION,'tools':contract,
          'statuses':['ok','no_match','not_indexed','no_measured_evidence','unsupported_feature','unsupported_version'],
          'errors':['INVALID_ARGUMENT','UNKNOWN_ARGUMENT','INVALID_CURSOR','STALE_CURSOR','SCOPE_CONFLICT','SOURCE_INTEGRITY_MISMATCH','BUILD_MISMATCH'],
          'envelope_required':['status','version','source_commit','build_id','read_only','requested_scope','resolved_scope','applied_filters'],
          'budgets':{'compact_search_5_max_chars':6000,'text_window_max_chars':18000,'response_max_chars':32000,'parameter_task_calls':4,'cross_module_task_calls':8}})
    paths=[
        ('R01',['concept:collisions','pipeline:enable_rigid_soft_full_surface_contact','lab:full_surface']),
        ('R02',['module:controllers','module:ik','topic:robot-control','recipe:ik-mujoco-contact','solver:mujoco']),
        ('R03',['module:sensors','concept:solver-observables','recipe:mujoco-native-contact','recipe:ik-mujoco-contact']),
        ('R04',['concept:coupling','topic:coupling','recipe:coupled-rigid-deformable','solver:vbd','solver:mujoco']),
        ('R05',['concept:worlds','module:selection','topic:worlds-batching','recipe:worlds-reset']),
        ('R06',['topic:differentiable-simulation','module:solvers','solver:vbd','solver:xpbd']),
    ]
    write('planning/p0/required-paths.json',{'paths':[{'id':key,'required_records':ids,'require_source_refs':True,'scope':'knowledge navigation; not causal inference'} for key,ids in paths]})
    task_specs=[
        ('T01','比较 VBD MuJoCo Kamino iterations 默认值和实测依据',['solver:vbd','solver:mujoco','solver:kamino'],'default_comparison',['Do not rank performance by equal iteration counts']),
        ('T02','球穿过粗三角布面 full surface 穿模',['concept:collisions','pipeline:enable_rigid_soft_full_surface_contact','lab:full_surface'],'full_surface',['Do not infer other solver support from VBD measurement']),
        ('T03','导入多机器人 使用 IK controller 下发 MuJoCo 目标并读取接触力',['recipe:ik-mujoco-contact','module:controllers','module:selection','concept:solver-observables'],'ik_contact',['Do not claim this recipe was physically executed']),
        ('T04','MuJoCo 刚体和 VBD 布料双向耦合 ownership attachment 子步',['recipe:coupled-rigid-deformable','concept:coupling'],'coupling',['External rigid flag alone is not two-way coupling']),
        ('T05','选择部分 world 的机器人控制并掩码复位',['recipe:worlds-reset','module:selection','concept:worlds'],'batch_reset',['Do not reset all worlds silently']),
        ('T06','SensorContact CONTACT_F observables 初始化和 sensor update',['recipe:mujoco-native-contact','concept:solver-observables','module:sensors'],'observable_order',['Do not allocate contact observables before resolving capacities']),
        ('T07','requires_grad Warp Tape 选择可微仿真后端',['topic:differentiable-simulation','solver:xpbd','solver:vbd'],'differentiability',['Do not generalize differentiability to all backends']),
        ('T08','SolverXPBD 参数与公开源码入口',['solver:xpbd'],'indexed_backend',['Do not substitute another solver parameter']),
        ('T09','确认未索引符号与随机词无命中的区别',['module:controllers'],'negative_lookup',['No match does not mean unsupported']),
        ('T10','未知参数 stage 范围 冲突 ID',['module:geometry'],'argument_contract',['Do not ignore unsupported arguments']),
        ('T11','搜索 目录 图邻居与边分页完整性',[],'pagination',['No duplicate or missing entries']),
        ('T12','未知版本 无实测 proposed 证据边界',['solver:mujoco'],'evidence_boundaries',['Never turn proposed into measured']),
    ]
    answer_points={
        'T01':['VBD 声明默认 10、MuJoCo 声明 None 与解析策略、Kamino PADMM 上限 200 分开读取','按所查询内容世代报告实测存在性'],
        'T02':['定义 owner 为 CollisionPipeline，声明默认 False','动态来源行号与 VBD A/B 指标一致','其他 backend 依据适用性来源，未知则明确 unknown'],
        'T03':['定位导入、Worlds、ArticulationView、IK/controller 和目标布局','驱动支持与 MuJoCo 路径有条件说明','说明 Contacts/observables 分配和 SensorContact 更新顺序'],
        'T04':['ModelView 与所有权划分','Proxy 与 ADMM 的职责和入口','子 solver、接触、子步、attachment 的实际支持边界'],
        'T05':['选择索引与 world 对应','目标数组布局与掩码范围','只有支持的 reset 路径才可承诺保留其他 world'],
        'T06':['先解析容量，再为同一 Contacts 请求 CONTACT_F','step 写出目标 State 后按传感器 API 更新','说明原生与外部碰撞路径初始化顺序差异'],
        'T07':['使用版本化 backend 可微能力表','定位 requires_grad、Warp Tape 与状态历史示例','不宣称执行过梯度验证'],
        'T08':['SolverXPBD 精确符号可被搜索发现并读来源','未整理的参数返回 not_indexed 并提供受支持续读'],
        'T09':['真实存在性由公开符号表判定','随机未知词是 no_match，不是不支持'],
        'T10':['未知参数立即拒绝','已支持过滤与基准集合一致','ID 与 solver 冲突不自动改查'],
        'T11':['搜索、目录、邻居、边能遍历到最后','无重复或遗漏','旧世代或条件不一致的 cursor 明确失效'],
        'T12':['版本不回退','缺失实测不借用其他案例','proposed 不升级 measured'],
    }
    write('planning/p0/acceptance-tasks.json',{'tasks':[{'id':key,'query':query,'required_record_ids':ids,'check':check,'answer_points':answer_points[key],'forbidden_conclusions':forbidden,
          'mode':'boundary' if int(key[1:])>=9 else 'positive','target_max_calls':8 if key!='T11' else None,
          'needs_preknown_internal_path':False,'runtime_simulation_required':False} for key,query,ids,check,forbidden in task_specs]})
    contract_text='''# P0 冻结的范围与调用契约

依据 PRD 0.2 与固定 Newton 1.7.0 快照。知识内容的目标深度和当前达成状态分别记录。

- `knowledge/registry.json`：12 API、14 Concepts、8 backend、8 跨阶段主题、7 阶段与6配方的稳定目标、公共导出、来源和深度。
- `manifests/source-lock.json`：干净固定源码快照的全部已跟踪文件哈希。
- `record.schema.json`：公共/solver归属、定义所有者、适用性、证据与覆盖状态的共同字段。
- `mcp-contract.json`：六工具输入输出契约、严格参数、版本、范围、分页、明确错误与响应预算。
- `migration-baseline.json` / `migration-map.json`：现有全部文档、参数、图ID、检索ID、A/B原始数据及生成链、路由和兼容映射。
- `required-paths.json`：R01–R06，验收端点和来源；关系仅表示有出处的对应，不推断因果。
- `acceptance-tasks.json`：T01–T12，必需记录、答案要点、禁止结论、预算与边界用例。

## 首版范围语义

`solver=all` 发现公共及全部八 backend；`solver=shared` 仅公共内容；`solver=X` 为X专属，显式 `include_shared=true` 加入有来源支持的适用公共记录。unknown不等于unsupported。旧参数查询省略solver保留VBD，但必须标明legacy_default。

每次命中和图邻居都有可执行精确读取；文档/记录、源码、搜索和关系分页标明剩余内容。先过滤再排序，cursor绑定构建世代和查询。未知输入不静默忽略。no_match、not_indexed、no_measured_evidence、unsupported_feature、unsupported_version分别处理。

输出保留旧成功记录字段，新增status、build_id、范围与应用过滤；业务错误必须机器可解析。错误和未知条件只在有来源时判定，不从空命中猜测。JSONschema约束后仍需校验互斥path/record_id或path/symbol_id、分页条件和范围冲突。

## 构建与发布

源记录是唯一编辑入口。构建输出的catalog、graph与SQLite拥有共同build_id；部分构建不一致要明确拒绝。被引用文件核对source-lock，无法核对的来源只能标local_snapshot_unverified_file。

P1通过范围、导航、旧ID/路径、原始实验不变和构建一致性；P2通过全部模块入口、R01–R06、T01–T12及真实stdio契约测试。P3增加任务深度，P4新增物理A/B，P5持续维护并交付可重复执行的更新检查。
'''
    (OUT/'CONTRACT.md').write_text(contract_text,encoding='utf-8')
    timestamp=datetime.now(UTC).isoformat()
    progress=ROOT/'planning/progress.json'
    if not progress.exists():
        write('planning/progress.json',{'goal':'按 PRD 构建 Newton 知识库并逐阶段汇报飞书','prd':'0.2','started_at':timestamp,
              'phases':[{'id':f'P{i}','status':'in_progress' if i==0 else 'pending','evidence':[],'notification':'pending'} for i in range(6)]})
    write('planning/notifications/config.json',{'provider':'lark-cli','identity':'bot','chat_id':'oc_ad77e9fd76e3c8e9d0a3c569da812f7e',
          'authorized_purpose':'PRD phase completion reports','skill':'lark-im','send_only_after_verified_phase':True})
    print(json.dumps({'registry_counts':payload['counts'],'source_locked_files':len(files),'baseline_search_records':len(old_records),'contract_tools':len(contract)}))


if __name__=='__main__':
    main()
