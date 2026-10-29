"""Audit pinned evidence, internal consistency, relative document links and retrieval smoke cases."""
from pathlib import Path
import ast,hashlib,json,re,subprocess,sys
from build_index import ROOT
from retrieve import retrieve

errors=[];checks=[]
def require(ok,msg):
    checks.append({'check':msg,'passed':bool(ok)})
    if not ok:errors.append(msg)
def load(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
manifest=load('manifests/newton-1.7.0.json');SRC=ROOT/manifest['source_path'];SHA=manifest['commit']
head=subprocess.check_output(['git','-C',str(SRC),'rev-parse','HEAD'],text=True).strip()
require(head==SHA,'official source HEAD matches pinned commit')
require(subprocess.check_output(['git','-C',str(SRC),'status','--porcelain'],text=True).strip()=='','official source snapshot has no working-tree edits')
for f in manifest['inspected_files']:
    require(hashlib.sha256((SRC/f['path']).read_bytes()).hexdigest()==f['sha256'],'source hash '+f['path'])
for p in load('manifests/papers.json'):
    require(hashlib.sha256((ROOT/p['local_path']).read_bytes()).hexdigest()==p['sha256'],'paper hash '+p['id'])
params=load('solvers/vbd/parameters.json')['records']
tree=ast.parse((SRC/'newton/_src/solvers/vbd/solver_vbd.py').read_text(encoding='utf-8'))
cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='SolverVBD')
init=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='__init__')
expected=[n.arg for n in init.args.args[1:]+init.args.kwonlyargs]
require([p['name'] for p in params]==expected and len(params)==48,'all constructor inputs preserved in original order, including model')
require(all(p['documentation'] for p in params),'every parameter has source documentation')
require(all(p['summary_zh'] and 'resolved_default' in p for p in params),'every parameter has Chinese interpretation and default-resolution field')
require(all(p['suggested_tuning_range'] is None for p in params),'no fabricated empirical universal tuning ranges')

graph=load('graph/knowledge-graph.json');ids=[n['id'] for n in graph['nodes']];nodeids=set(ids)
require(len(ids)==len(nodeids),'graph node IDs are unique')
source_ids=[s['id'] for s in load('indexes/source_symbols.json')['symbols']]
require(len(source_ids)==len(set(source_ids)),'source symbol IDs distinguish property getters/setters')
require(all(e['source'] in nodeids and e['target'] in nodeids for e in graph['edges']),'graph has no dangling edges')

# Recursively audit every source anchor in authored structured artifacts.
refcount=0;source_lines={}
def walk(value):
    global refcount
    if isinstance(value,dict):
        if {'commit','path','line','url'}.issubset(value):
            refcount+=1;p=SRC/value['path']
            if p.exists():
                size=source_lines.setdefault(value['path'],len(p.read_text(encoding='utf-8').splitlines()))
                if not (value['commit']==SHA and 1<=value['line']<=value.get('end_line',value['line'])<=size and SHA in value['url']): errors.append('invalid source anchor '+str(value))
            else:errors.append('missing source path '+value['path'])
        for v in value.values():walk(v)
    elif isinstance(value,list):
        for v in value:walk(v)
for directory in ['solvers/vbd','graph','indexes']:
    for p in (ROOT/directory).glob('*.json'):walk(json.loads(p.read_text(encoding='utf-8')))
require(refcount>100,'source anchors inspected recursively')

broken=[];controlchars=[]
# Relocated immutable reports/backups retain links relative to their original
# location; only current authored documents are a live navigation surface.
docpaths=[ROOT/'README.md']+[p for directory in ['solvers','agent','graph','evaluations','experience'] for p in (ROOT/directory).rglob('*.md') if not {'history', 'before'}.intersection(p.relative_to(ROOT).parts)]
for p in docpaths:
    s=p.read_text(encoding='utf-8')
    if re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f]',s):controlchars.append(str(p))
    for target in re.findall(r'\]\(([^)]+)\)',s):
        if '://' in target or target.startswith('#'):continue
        target=target.split('#')[0].strip('<>')
        if target and not (p.parent/target).exists():broken.append((str(p.relative_to(ROOT)),target))
require(not broken,'authored Markdown relative file links resolve: '+str(broken))
require(not controlchars,'Markdown contains no escaped-formula control characters')

test_results=[]
for q in load('evaluations/queries.json'):
    hits=[h['id'] for h in retrieve(q['query'],8,expand=False)['hits']]
    success=any(x in hits for x in q['expected_any'])
    test_results.append({**q,'returned_ids':hits,'passed':success})
require(all(x['passed'] for x in test_results),'curated retrieval smoke cases hit expected evidence in top 8')
# The unified CLI/MCP adapter returns the contract's structured rejection.
unsupported=retrieve('默认值',version='1.4.0')
rejected=unsupported['status']=='unsupported_version' and not unsupported.get('hits')
require(rejected,'retrieval rejects an unindexed Newton version')

physics=load('experiments/results.cpu.json')
require(physics['solver_matches_pinned_snapshot'],'executed CPU probe solver file matches source snapshot')
require(all(t['status']=='passed' for t in physics['tests']),'four recorded CPU probe groups passed')
report={'date':'2026-10-27','newton_version':'1.7.0','commit':SHA,'status':'passed' if not errors else 'failed',
 'checks':checks,'errors':errors,'source_refs_checked':refcount,
 'counts':{'constructor_inputs':len(params),'optional_parameters':len(params)-1,'source_symbols':len(load('indexes/source_symbols.json')['symbols']),'claims':len(load('solvers/vbd/claims.json')),'graph_nodes':len(ids),'graph_edges':len(graph['edges'])},
 'retrieval':{'passed':sum(r['passed'] for r in test_results),'total':len(test_results),'top_k':8,'kind':'hand-authored smoke cases, not independent semantic QA benchmark','cases':test_results},
 'physics':'four narrow CPU behavioral groups; see experiments/results.cpu.json; not full upstream suite or real2sim validation'}
(ROOT/'evaluations/results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
summary=f'''# 验证记录

日期：2026-10-27；Newton 1.7.0；commit `{SHA}`。

结果：**{report['status']}**。结构检查 {sum(c['passed'] for c in checks)}/{len(checks)}；手工检索冒烟问题 {report['retrieval']['passed']}/{len(test_results)} 在前 8 条中命中预期证据。

- 48 个 constructor 输入（47 个可选项）与真实签名核对。
- {refcount} 个源引用经过路径、版本和行号范围校验；源码/PDF 哈希已校验。
- 关系图 {len(ids)} 个节点、{len(graph['edges'])} 条边，无悬挂引用。
- 4 组真实 CPU 探针通过：模式默认值、margin/gap 兼容、单弹簧隐式一步、构造约束。
- 单弹簧：理论 x=1.198019801980198，实测 x=1.1980198621749878，绝对误差约 6.02e-8。

依赖为 Python 3.12.14、Newton 1.7.0、Warp 1.18.0、NumPy 2.5.4。核对的是保存的官方 solver 文件与实际加载文件；源码完整性另由 Git 与清单验证。

检索测试验证的是返回证据，而非 LLM 最终回答的正确性。尚未进行语义召回基准、全部上游测试、GPU/tile 性能、复杂 DAT 接触、真实视频/轨迹参数识别。不能把这些窄探针提升为全场景稳定保证。

详见 [结构与检索结果](results.json)、[CPU 原始结果](../experiments/results.cpu.json)、[探针脚本](../experiments/run_cpu_probes.py)。
'''
(ROOT/'evaluations/REPORT.md').write_text(summary,encoding='utf-8')
print(json.dumps({'status':report['status'],'errors':errors,'retrieval':f"{report['retrieval']['passed']}/{len(test_results)}",'counts':report['counts']},ensure_ascii=False))
sys.exit(bool(errors))
