"""Build offline FTS5 retrieval over curated records, not the unbounded full repository."""
from pathlib import Path
import json, re, sqlite3
ROOT=Path(__file__).resolve().parents[1]

def tokens(text):
    out=re.findall(r'[a-zA-Z_][a-zA-Z_0-9:.]*|\d+(?:\.\d+)*',text.lower())
    for word in re.findall(r'[\u4e00-\u9fff]+',text):
        out += [word[i:i+2] for i in range(len(word)-1)] if len(word)>1 else [word]
    return list(dict.fromkeys(out))

def load(rel): return json.loads((ROOT/rel).read_text(encoding='utf-8'))

def records():
    rows=[]
    def add(id,kind,title,text,record,path):
        rows.append((id,kind,'1.7.0',title,text,json.dumps(record,ensure_ascii=False),path,' '.join(tokens(title+' '+text))))
    for r in load('solvers/vbd/parameters.json')['records']:
        add(r['id'],'parameter',r['name'],r['summary_zh']+' '+r['category']+' '+str(r['resolved_default']),r,'solvers/vbd/parameters.json')
    for r in load('solvers/vbd/claims.json'):
        add(r['id'],'claim',r['id'],r['statement_zh']+' '+r['scope']+' '+' '.join(r['parameter_ids']),r,'solvers/vbd/claims.json')
    for r in load('solvers/vbd/model-inputs.json'):
        add(r['id'],'model_input',r['field'],r['description_zh']+' '+r['units'],r,'solvers/vbd/model-inputs.json')
    for r in load('solvers/vbd/diagnostics.json'):
        add(r['id'],'diagnostic',r['symptom'],' '.join(r['plan'])+' '+r['caution'],r,'solvers/vbd/diagnostics.json')
    for r in load('solvers/vbd/paper-code-map.json'):
        add(r['id'],'mapping',r['title_zh'],str(r['paper_id'])+' '+r['id']+' '+r['paper_locator']+' '+r['correspondence']+' '+' '.join(r['parameter_ids'])+' '+' '.join(s['name'] for s in r['symbols']),r,'solvers/vbd/paper-code-map.json')
    r=load('solvers/vbd/capabilities.json')
    add('capabilities:VBD:1.7.0','capabilities','VBD 支持与不支持的功能',json.dumps(r,ensure_ascii=False),r,'solvers/vbd/capabilities.json')
    for r in load('manifests/papers.json'):
        add(r['id'],'paper',r['title'],r['role']+' '+r['doi'],r,'manifests/papers.json')
    for path in sorted((ROOT/'solvers/vbd').glob('*.md')):
        if path.name in ('parameters.md','diagnostics.md','model-inputs.md','paper-code-map.md'): continue
        for i,section in enumerate(re.split(r'(?m)^## ',path.read_text(encoding='utf-8'))):
            if not section.strip():continue
            title=section.splitlines()[0].lstrip('# ')
            add(f'doc:{path.stem}:{i}','document',title,section,{'path':path.relative_to(ROOT).as_posix(),'section':title},path.relative_to(ROOT).as_posix())
    if (ROOT/'experiments/results.cpu.json').exists():
        report=load('experiments/results.cpu.json')
        for r in report['tests']:
            add(r['id'],'experiment',r['id'],json.dumps(r,ensure_ascii=False),{'result':r,'environment':{k:v for k,v in report.items() if k!='tests'}},'experiments/results.cpu.json')
    for solver in ('mujoco','kamino'):
        path=ROOT/'solvers'/solver/'catalog.json'
        if not path.exists():continue
        cat=json.loads(path.read_text(encoding='utf-8'))
        for key,kind in [('parameters','parameter'),('model_inputs','model_input'),('claims','claim'),('mappings','mapping'),('diagnostics','diagnostic'),('papers','paper')]:
            for r in cat[key]:
                title=r.get('name',r.get('field',r.get('title_zh',r.get('symptom',r.get('title',r['id'])))))
                add(r['id'],kind,title,solver+' '+json.dumps(r,ensure_ascii=False),r,f'solvers/{solver}/catalog.json')
    return rows

def main():
    con=sqlite3.connect(ROOT/'indexes/knowledge.sqlite')
    con.executescript('DROP TABLE IF EXISTS search; DROP TABLE IF EXISTS records; CREATE TABLE records(id TEXT PRIMARY KEY, kind TEXT, version TEXT, title TEXT, text TEXT, record TEXT, file TEXT, tokens TEXT); CREATE VIRTUAL TABLE search USING fts5(id UNINDEXED,tokens);')
    rows=records()
    con.executemany('INSERT INTO records VALUES (?,?,?,?,?,?,?,?)',rows)
    con.executemany('INSERT INTO search VALUES (?,?)',[(r[0],r[-1]) for r in rows])
    con.commit();con.close()
    print(json.dumps({'indexed_records':len(rows),'engine':'SQLite FTS5 + identifier matching + Chinese character bigrams'}))
if __name__=='__main__':main()
