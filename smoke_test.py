"""Real stdio relocation smoke test; does not execute physics or require the website."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import traceback
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from manage import DATA, ROOT, runtime_python, sha, verify

TOOLS = {'search_knowledge', 'get_parameter', 'get_experiment', 'get_document', 'get_source', 'get_relations'}


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def inspect_artifacts(value):
    found = []
    if isinstance(value, dict):
        if all(k in value for k in ('path', 'local_path', 'file_uri')):
            path = Path(value['local_path'])
            assert path.is_file(), 'Missing distributed artifact: ' + str(path)
            assert path.resolve().is_relative_to(ROOT.resolve()), 'Artifact points outside the relocated package'
            assert path.resolve() == (DATA / value['path']).resolve(), 'Local artifact was not resolved from the new knowledge root'
            assert path.as_uri() == value['file_uri'], 'Incorrect file URI'
            found.append(value['path'])
        for child in value.values():
            found.extend(inspect_artifacts(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(inspect_artifacts(child))
    return found


async def main():
    out = ROOT / '.validation'
    out.mkdir(exist_ok=True)
    # Keep earlier attempts instead of rewriting evidence of a failed test.
    for name in ('smoke.json', 'smoke-stderr.log'):
        path = out / name
        if path.exists():
            archive = out / 'history' / (path.stem + '-' + sha(path)[:16] + path.suffix)
            archive.parent.mkdir(exist_ok=True)
            if not archive.exists():
                archive.write_bytes(path.read_bytes())
    checks, trace = [], []
    def check(value, description):
        checks.append({'check': description, 'passed': bool(value)})
        if not value:
            raise AssertionError(description)
    result = {'status': 'failed', 'root': str(ROOT), 'checks': checks, 'calls': trace}
    try:
        verified = verify()
        manifest = load(ROOT / 'package-manifest.json')
        pointer = load(DATA / 'knowledge/current.json')
        catalog = load(DATA / pointer['path'] / 'catalog.json')
        programs = load(DATA / 'manifests/experiment-programs.json')['files']
        build = pointer['build_id']
        result['build_id'] = build
        check(verified['build_id'] == build == manifest['build_id'], 'bundle and runtime build match')
        with tempfile.TemporaryDirectory(prefix='newton-mcp-unrelated-') as cwd, (out / 'smoke-stderr.log').open('w', encoding='utf-8') as err:
            check(not Path(cwd).resolve().is_relative_to(ROOT), 'client and server launch from an unrelated working directory')
            params = StdioServerParameters(command=str(runtime_python()), args=['-B', '-X', 'utf8', str(DATA / 'mcp_service/server.py')], env={**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONDONTWRITEBYTECODE': '1', 'NEWTON_KB_SITE_URL': 'http://127.0.0.1:1'}, cwd=cwd)
            async with stdio_client(params, errlog=err) as (read, write):
                async with ClientSession(read, write, read_timeout_seconds=30) as session:
                    init = await session.initialize()
                    result['negotiated_protocol'] = init.protocol_version
                    check(init.server_info.name == 'newton_knowledge', 'real stdio handshake identifies the packaged server')
                    listed = await session.list_tools()
                    check({t.name for t in listed.tools} == TOOLS, 'exactly the six read-only tools are discoverable')
                    for t in listed.tools:
                        ann = t.annotations.model_dump(by_alias=True)
                        check(ann.get('readOnlyHint') and not ann.get('destructiveHint'), 'read-only tool annotations: ' + t.name)
                    async def call(name, arguments, error=False):
                        raw = (await session.call_tool(name, arguments)).model_dump(by_alias=True, exclude_none=True)
                        data = raw.get('structuredContent', {})
                        logical_chars = len(json.dumps(data, ensure_ascii=False, separators=(',', ':')))
                        trace.append({'tool': name, 'arguments': arguments, 'status': data.get('status'), 'is_error': raw.get('isError', False), 'build_id': data.get('build_id'), 'logical_json_chars': logical_chars})
                        check(logical_chars <= 32000, 'response respects 32000 logical JSON character budget: ' + name)
                        check(bool(raw.get('isError')) == error, 'expected error state: ' + name)
                        if not error:
                            check(data.get('build_id') == build and data.get('read_only') is True, 'stable build and read-only envelope: ' + name)
                        return data
                    search = await call('search_knowledge', {'query': '摩擦', 'solver': 'mujoco', 'limit': 4})
                    check(0 < len(search['hits']) <= 4, 'bounded Chinese retrieval works without a running website')
                    experiment_counts = {}
                    for solver, cat in catalog['solvers'].items():
                        if cat['parameters']:
                            parameter = cat['parameters'][0]
                            data = await call('get_parameter', {'record_id': parameter['id'], 'solver': solver})
                            check(data['parameters'][0]['id'] == parameter['id'], 'exact parameter read: ' + solver)
                        experiment_counts[solver] = 0
                        if not cat['experiments']:
                            continue
                        for experiment in cat['experiments']:
                            label = solver + '/' + experiment['id']
                            data = await call('get_experiment', {'experiment_id': experiment['id'], 'solver': solver, 'detail': 'summary'})
                            check(data['record']['owner_solver'] == solver and data['experiment']['id'] == experiment['id'], 'saved experiment remains solver-scoped: ' + label)
                            files = inspect_artifacts(data)
                            check(bool(files), 'raw/curve/runner paths resolve beneath the relocated bundle: ' + label)
                            for variant in data['experiment']['variants']:
                                relative = ('experiments/vbd_parameter_lab/' if solver == 'vbd' else '') + variant['raw_file']
                                check(sha(DATA / relative) == variant['raw_sha256'], 'original physical-array hash: ' + label + '/' + variant['variant'])
                            experiment_counts[solver] += 1
                        ref = data['source_refs'][0]
                        source = await call('get_source', {'path': ref['path'], 'start_line': ref['line'], 'max_lines': 8})
                        check(source['sha256'] == ref['sha256'], 'fixed source excerpt hash: ' + solver)
                        relations = await call('get_relations', {'node_id': data['record']['id'], 'limit': 5})
                        check(bool(relations.get('edges')), 'graph associations remain readable: ' + solver)
                        program = data.get('program_source_call')
                        if program:
                            content = await call(program['tool'], program['arguments'])
                            check(bool(content.get('sha256')), 'archived runner can be read: ' + solver)
                    result['experiments_verified'] = experiment_counts
                    for path, expected_sha in programs.items():
                        content = await call('get_source', {'scope': 'experiment', 'path': path, 'max_lines': 2})
                        check(content.get('sha256') == expected_sha, 'locked experiment program excerpt hash: ' + path)
                    result['programs_verified'] = len(programs)
                    doc = await call('get_document', {'path': 'solvers/mujoco/experiments.md', 'max_lines': 20})
                    expected = (DATA / 'solvers/mujoco/experiments.md').read_text(encoding='utf-8').splitlines()[:20]
                    check(doc['text'] == '\n'.join(expected), 'published document text matches the distributed source')
                    wrong = await call('get_experiment', {'experiment_id': catalog['solvers']['mujoco']['experiments'][0]['id'], 'solver': 'kamino'})
                    check(wrong['status'] == 'no_measured_evidence' and 'experiment' not in wrong, 'wrong-solver query never borrows another solver evidence')
                    bad = await call('get_source', {'path': '../manage.py'}, error=True)
                    check(bad['error']['code'] == 'INVALID_PATH', 'path traversal is rejected')
                    empty = await call('search_knowledge', {'query': 'zzzz_nonexistent_938472', 'limit': 2})
                    check(not empty['hits'], 'unknown searches return no fabricated records')
        check(verify()['build_id'] == build, 'all distributed files unchanged after the full client session')
        result.update(status='passed', passed=len(checks), failed=0, tool_calls=len(trace), scope='Real six-tool stdio test from unrelated cwd; artifact paths resolved to this package; no physics or website needed.')
    except Exception as exc:
        result.update(error=str(exc), traceback=traceback.format_exc(), passed=sum(x['passed'] for x in checks), failed=sum(not x['passed'] for x in checks) or 1, tool_calls=len(trace))
    (out / 'smoke.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in ('checks', 'calls', 'traceback')}, ensure_ascii=False))
    if result['status'] != 'passed':
        raise SystemExit(1)


if __name__ == '__main__':
    asyncio.run(main())
