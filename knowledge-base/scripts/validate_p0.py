"""Audit the actual P0 deliverables against PRD scope and pinned source inventory."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC,datetime
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[1]


def read(path):
    return json.loads((ROOT/path).read_text(encoding='utf-8'))


def main():
    checks=[]
    def check(condition,label):
        checks.append({'check':label,'passed':bool(condition)})
        if not condition:print('FAILED:',label)
    registry=read('knowledge/registry.json');lock=read('manifests/source-lock.json')
    check(registry['counts']=={'api':12,'concept':14,'solver':8,'topic':8,'stage':7,'recipe':6},'coverage denominators and all required topic/workflow/recipe targets are frozen')
    entries=registry['entries'];ids={e['id'] for e in entries}
    check(len(ids)==len(entries),'stable planned IDs are unique')
    aliases=[a for e in entries for a in e['aliases']]
    check(len(aliases)==len(set(aliases)),'aliases have no conflicting owners')
    check(all(e['source_refs'] and e['owner_module'] and e['canonical_path'] and e['target_depth'] and 'observed_depth' in e and e['deferred'] for e in entries),'every scope entry has source, target, current state, owner and deferred boundary')
    for entry in entries:
        ref=entry['source_refs'][0]
        check(hashlib.sha256((ROOT/'sources/newton-v1.7.0'/ref['path']).read_bytes()).hexdigest()==ref['sha256']==lock['files'][ref['path']],'source verified: '+entry['id'])
    check(registry['prd_sha256']==hashlib.sha256((ROOT/'planning/PRD.md').read_bytes()).hexdigest(),'frozen scope points to the actual PRD revision')
    baseline=read('planning/p0/migration-baseline.json')
    check(len(baseline['documents'])==31 and len(baseline['parameter_ids'])==169 and len(baseline['experiments'])==17,'baseline preserves all existing documents, parameter IDs and A/B cases')
    check(len(baseline['search_records'])==367 and len(set(r['id'] for r in baseline['search_records']))==367,'all legacy search identities/routes frozen')
    migration=read('planning/p0/migration-map.json')
    check({r['id'] for r in migration['records']}=={r['id'] for r in baseline['search_records']},'every existing search ID has an explicit migration target')
    check(all(r['new_route'] and r['authoring_source'] and 'generators' in r and r['generated_artifact'] and r['index'] for r in migration['records']),'migration inventory covers authoring, generator, generated output, index and route')
    known=ids|set(baseline['graph_ids'])|set(baseline['parameter_ids'])|{r['id'] for r in baseline['search_records']}
    paths=read('planning/p0/required-paths.json')['paths'];tasks=read('planning/p0/acceptance-tasks.json')['tasks']
    check([p['id'] for p in paths]==[f'R{i:02d}' for i in range(1,7)],'all six required evidence paths are frozen')
    check(all(all(x in known for x in p['required_records']) for p in paths),'required path endpoints resolve to planned or existing identities')
    check([t['id'] for t in tasks]==[f'T{i:02d}' for i in range(1,13)],'all twelve acceptance tasks are frozen')
    check(all(all(x in known for x in t['required_record_ids']) and t['forbidden_conclusions'] and t['check'] and t['answer_points'] for t in tasks),'task evidence targets, answer points and forbidden conclusions are explicit')
    check(all(not t['needs_preknown_internal_path'] for t in tasks),'no acceptance task is given an internal source path')
    contract=read('planning/p0/mcp-contract.json')
    expected={'search_knowledge','get_parameter','get_experiment','get_relations','get_document','get_source'}
    check(set(contract['tools'])==expected,'exactly six read-only tools are specified')
    for name,tool in contract['tools'].items():
        Draft202012Validator.check_schema(tool['inputSchema'])
        Draft202012Validator.check_schema(tool['outputSchema'])
        check(tool['inputSchema']['additionalProperties'] is False and tool['annotations']['readOnlyHint'],'strict arguments and read-only contract: '+name)
    Draft202012Validator.check_schema(read('planning/p0/record.schema.json'))
    check(set(contract['tools']['search_knowledge']['inputSchema']['properties'])>={'domain','stage','solver','include_shared','cursor'},'first-release filtering, shared scope and pagination specified')
    check('record_id' in contract['tools']['get_document']['inputSchema']['properties'],'all record types have a precise-read path')
    public_exports=read('planning/p0/public-exports.json')
    check(set(public_exports)=={'newton' if e['id']=='module:newton' else 'newton.'+e['id'].split(':')[1] for e in entries if e['family']=='api'},'public export inventory covers all twelve API entries')
    check(set(public_exports['newton'])>={'ModelBuilder','Model','State','Control','Contacts','CollisionPipeline','actuators','controllers','solvers'},'incremental public __all__ includes core objects and submodules')
    check(read('planning/notifications/config.json')['chat_id']=='oc_ad77e9fd76e3c8e9d0a3c569da812f7e','phase reports target the exact user-authorized conversation')
    result={'status':'passed' if all(c['passed'] for c in checks) else 'failed','phase':'P0','tested_at':datetime.now(UTC).isoformat(),
            'passed':sum(c['passed'] for c in checks),'failed':sum(not c['passed'] for c in checks),'checks':checks}
    out=ROOT/'evaluations/p0-validation.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='checks'}))
    if result['failed']:raise SystemExit(1)


if __name__=='__main__':main()
