"""Read-only Newton evidence collection and compatibility triage; standard library only."""
from __future__ import annotations
import argparse
import ast
import hashlib
import importlib.metadata as metadata
import importlib.util
import json
import os
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

SCHEMA = 'newton-version-evidence-v1'
SKIP = {'.git', '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', 'node_modules', 'build', 'dist'}
DEPENDENCIES = ('newton', 'warp-lang', 'mujoco', 'mujoco-warp', 'numpy', 'scipy')


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest()


def safe_relative(name):
    if not isinstance(name, str) or not name or '\\' in name or ':' in name or '\x00' in name:
        raise ValueError('Invalid relative evidence path')
    if PurePosixPath(name).is_absolute() or any(p in ('', '.', '..') for p in name.split('/')):
        raise ValueError('Unsafe evidence path: ' + name)
    return name


def inside(root, relative):
    p = root / safe_relative(relative)
    if not p.resolve().is_relative_to(root.resolve()):
        raise ValueError('Evidence path escapes root: ' + relative)
    return p


def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def declarations(tree, relative):
    found = {}
    def visit(nodes, prefix=''):
        for node in nodes:
            key = relative + '::' + prefix
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                found[key + node.name] = {'kind': 'callable', 'signature': ast.unparse(node.args),
                    'returns': ast.unparse(node.returns) if node.returns else None,
                    'decorators': [ast.unparse(d) for d in node.decorator_list]}
            elif isinstance(node, ast.ClassDef):
                found[key + node.name] = {'kind': 'class', 'bases': [ast.unparse(b) for b in node.bases]}
                visit(node.body, prefix + node.name + '.')
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Name):
                        found[key + target.id] = {'kind': 'declaration', 'value': ast.unparse(node.value) if node.value else None,
                            'annotation': ast.unparse(node.annotation) if isinstance(node, ast.AnnAssign) else None}
            elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
                found[key + node.target.id + '::augmentation'] = {'kind': 'augmentation', 'value': ast.unparse(node)}
    visit(tree.body)
    found[relative + '::<module-imports>'] = {'kind': 'imports', 'statements': [ast.unparse(n) for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]}
    return found


def source_version(root, package):
    values = {}
    version_file = package / '_version.py'
    if version_file.is_file():
        try:
            for node in ast.parse(version_file.read_text(encoding='utf-8-sig')).body:
                targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
                if any(isinstance(t, ast.Name) and t.id == '__version__' for t in targets):
                    value = ast.literal_eval(node.value)
                    if isinstance(value, str):
                        values['source_version'] = value
        except (ValueError, SyntaxError, UnicodeError):
            pass
    project = root / 'pyproject.toml'
    if root != package and project.is_file():
        text = project.read_text(encoding='utf-8-sig')
        section = re.search(r'(?ms)^\[project\]\s*$(.*?)(?=^\[|\Z)', text)
        match = re.search(r'''(?m)^version\s*=\s*["']([^"']+)["']''', section.group(1)) if section else None
        if match:
            values['project_version'] = match.group(1)
    return values


def git_identity(root):
    try:
        def git(*args):
            p = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=15)
            return p.stdout.strip() if p.returncode == 0 else None
        top = git('rev-parse', '--show-toplevel')
        if top and Path(top).resolve() == root.resolve():
            status = git('status', '--porcelain', '--untracked-files=all')
            return {'commit': git('rev-parse', 'HEAD'), 'dirty': bool(status) if status is not None else None}
    except (OSError, subprocess.TimeoutExpired):
        pass
    return {'commit': None, 'dirty': None}


def collect(source=None, installed=False):
    env, versions = None, {}
    if installed:
        old_path = sys.path[:]
        try:
            script_dir = Path(__file__).resolve().parent
            sys.path[:] = [str(Path.cwd())] + [p for p in old_path if Path(p or '.').resolve() != script_dir]
            spec = importlib.util.find_spec('newton')
        finally:
            sys.path[:] = old_path
        if not spec or not spec.origin or not spec.submodule_search_locations:
            raise ValueError('This interpreter does not resolve a Newton package; provide its actual source path instead.')
        source = Path(spec.origin).resolve().parent
        packages = {}
        for name in DEPENDENCIES:
            try:
                packages[name] = metadata.version(name)
            except metadata.PackageNotFoundError:
                packages[name] = None
        if packages['newton']:
            versions['distribution_version'] = packages['newton']
        env = {'python': platform.python_version(), 'system': platform.system(), 'machine': platform.machine(), 'packages': packages,
               'gpu_driver_and_device': 'not_probed', 'newton_imported': False}
    root = Path(source).resolve()
    package = root / 'newton' if (root / 'newton/__init__.py').is_file() else root
    if not (package / '__init__.py').is_file() or not (package / '_src').is_dir():
        raise ValueError('Expected a Newton repository/package containing __init__.py and _src/.')
    scope = 'package' if root == package else 'repository'
    versions.update(source_version(root, package))
    identity = git_identity(root)
    if scope == 'package' and root.name == 'newton' and identity['commit'] is None:
        # Editable installs can point at checkout/newton. Never borrow an outer
        # knowledge repository's commit: git_identity requires this exact parent.
        identity = git_identity(root.parent)
    info = {'schema': SCHEMA, 'collected_at': datetime.now(timezone.utc).isoformat(), 'mode': 'installed' if installed else 'source',
            'scope': scope, 'version_sources': versions, 'git': identity, 'environment': env,
            'files': {}, 'ast_hashes': {}, 'declarations': {}, 'gaps': []}
    def walk_error(exc):
        info['gaps'].append({'reason': 'directory_scan_failed', 'error_type': type(exc).__name__})
    for folder, dirs, names in os.walk(root, followlinks=False, onerror=walk_error):
        here, kept = Path(folder), []
        for name in dirs:
            path = here / name
            if name in SKIP or name.startswith(('.venv', '.env')):
                continue
            if path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
                info['gaps'].append({'path': path.relative_to(root).as_posix(), 'reason': 'linked_directory_not_followed'})
            else:
                kept.append(name)
        dirs[:] = kept
        for name in sorted(names):
            path = here / name
            rel = path.relative_to(root).as_posix()
            rel = 'newton/' + rel if scope == 'package' else rel
            if path.suffix in ('.pyc', '.pyo') or name.startswith('.env') or name == '.DS_Store':
                continue
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                info['gaps'].append({'path': rel, 'reason': 'linked_file_not_read'})
                continue
            try:
                info['files'][rel] = sha(path)
                if rel.startswith('newton/') and path.suffix == '.py':
                    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
                    info['ast_hashes'][rel] = hashlib.sha256(ast.dump(tree, include_attributes=False).encode()).hexdigest()
                    info['declarations'].update(declarations(tree, rel))
            except (OSError, UnicodeError, SyntaxError) as exc:
                info['gaps'].append({'path': rel, 'reason': type(exc).__name__})
    info['fingerprint'] = digest(info)
    return info, root


def validate_evidence(value):
    if value.get('schema') != SCHEMA or value.get('scope') not in ('repository', 'package'):
        raise ValueError('Unsupported target evidence schema or scope')
    if value.get('fingerprint') != digest({k: v for k, v in value.items() if k != 'fingerprint'}):
        raise ValueError('Target evidence checksum mismatch; collect again rather than editing it.')
    for field in ('files', 'ast_hashes', 'declarations'):
        if not isinstance(value.get(field), dict):
            raise ValueError('Invalid evidence map: ' + field)
    for path, checksum in value['files'].items():
        safe_relative(path)
        if not isinstance(checksum, str) or not re.fullmatch('[0-9a-f]{64}', checksum):
            raise ValueError('Invalid file checksum in evidence')
        if value['scope'] == 'package' and not path.startswith('newton/'):
            raise ValueError('File outside declared package scope')
    for path in value['ast_hashes']:
        if path not in value['files']:
            raise ValueError('AST evidence without corresponding file')
    for key in value['declarations']:
        if key.split('::', 1)[0] not in value['ast_hashes']:
            raise ValueError('Declaration without parsed source evidence')
    if not isinstance(value.get('version_sources'), dict) or not isinstance(value.get('gaps'), list) or not isinstance(value.get('git'), dict):
        raise ValueError('Invalid version identity or gaps')


def baseline(root):
    root = Path(root).resolve()
    data = root / 'knowledge-base' if (root / 'knowledge-base/knowledge/current.json').is_file() else root
    release = root / 'package-manifest.json'
    if release.is_file():
        for name, expected in load(release)['files'].items():
            if sha(inside(root, name)) != expected:
                raise ValueError('Invalid baseline release file: ' + name)
    pointer = load(data / 'knowledge/current.json')
    build = inside(data, pointer['path'])
    if sha(build / 'manifest.json') != pointer['manifest_sha256']:
        raise ValueError('Invalid baseline build manifest')
    manifest = load(build / 'manifest.json')
    if manifest['build_id'] != pointer['build_id']:
        raise ValueError('Baseline pointer/build identity mismatch')
    for name, expected in manifest['files'].items():
        if sha(inside(build, name)) != expected:
            raise ValueError('Invalid baseline build file: ' + name)
    for name, expected in manifest.get('programs', {}).items():
        if sha(inside(data, name)) != expected:
            raise ValueError('Invalid baseline program: ' + name)
    lock_path = data / 'manifests/source-lock.json'
    if sha(lock_path) != manifest['source_lock_sha256']:
        raise ValueError('Invalid baseline source lock')
    lock = load(lock_path)
    if (lock['version'], lock['commit']) != (manifest['version'], manifest['commit']):
        raise ValueError('Baseline version/commit mismatch')
    source = inside(data, 'sources/newton-v' + lock['version'])
    for name, expected in lock['files'].items():
        if sha(inside(source, name)) != expected:
            raise ValueError('Invalid locked source: ' + name)
    evidence, _ = collect(source)
    if set(evidence['files']) != set(lock['files']) or evidence['gaps']:
        raise ValueError('Baseline source scan is incomplete, has additions, or contains unparsed files')
    runtime_lock = data / 'manifests/runtime-lock.txt'
    runtime_reference = None
    if runtime_lock.is_file():
        pins = dict(re.findall(r'(?m)^([A-Za-z0-9_.-]+)==([^\s;]+)', runtime_lock.read_text(encoding='utf-8')))
        runtime_reference = {'path': 'manifests/runtime-lock.txt', 'sha256': sha(runtime_lock), 'pins': pins,
                             'scope': 'Recorded development CPU environment; not universal Newton requirements or all solver-specific protocols.'}
    return pointer, lock, evidence, load(build / 'records.json'), load(build / 'graph.json'), runtime_reference


def diff_map(before, after):
    return {'added': {k: after[k] for k in sorted(after.keys() - before.keys())},
            'removed': {k: before[k] for k in sorted(before.keys() - after.keys())},
            'changed': {k: {'before': before[k], 'after': after[k]} for k in sorted(before.keys() & after.keys()) if before[k] != after[k]}}


def source_paths(value):
    result = set()
    if isinstance(value, dict):
        if isinstance(value.get('path'), str) and value['path'].startswith('newton/'):
            result.add(value['path'])
        for key, child in value.items():
            if key not in ('body', 'text'):
                result.update(source_paths(child))
    elif isinstance(value, list):
        for child in value:
            result.update(source_paths(child))
    return result


def compare(root, target=None, claimed_version=None):
    pointer, lock, before, records, graph, runtime_reference = baseline(root)
    report = {'schema': 'newton-version-audit-v1', 'baseline': {'build_id': pointer['build_id'], 'version': lock['version'], 'commit': lock['commit']},
              'runtime_compatibility': 'unverified', 'physical_evidence_inherited': False, 'may_publish': False,
              'baseline_environment_reference': runtime_reference,
              'default_semantics': 'Static AST expressions, not resolved backend defaults.',
              'impact_semantics': 'Source-reference and one-hop graph triage, not complete dependency or semantic analysis.'}
    if target is None:
        report.update(status='evidence_incomplete', target={'claimed_version': claimed_version}, gaps=['Only a version label was supplied; collect the actual source/environment.'])
        return report
    validate_evidence(target)
    old_files = {k: v for k, v in before['files'].items() if target['scope'] == 'repository' or k.startswith('newton/')}
    changes = diff_map(old_files, target['files'])
    touched = set(changes['added']) | set(changes['removed']) | set(changes['changed'])
    parsed_both = set(before['ast_hashes']) & set(target['ast_hashes'])
    excluded = {p for p in before['files'].keys() & target['files'].keys() if p.endswith('.py') and p.startswith('newton/') and p not in parsed_both}
    decl_before = {k: v for k, v in before['declarations'].items() if k.split('::', 1)[0] not in excluded}
    decl_after = {k: v for k, v in target['declarations'].items() if k.split('::', 1)[0] not in excluded}
    decl_changes = diff_map(decl_before, decl_after)
    direct = {}
    for key, value in records.items():
        changed = source_paths(value) & touched
        if changed:
            direct[key] = sorted(changed)
    neighbors = set()
    for edge in graph.get('edges', []):
        a, b = edge.get('source'), edge.get('target')
        if a in direct and b in records:
            neighbors.add(b)
        if b in direct and a in records:
            neighbors.add(a)
    impacted = []
    for key in sorted(set(direct) | neighbors):
        record = records[key]
        impacted.append({'id': key, 'kind': record.get('kind'), 'solver': record.get('owner_solver'), 'title': record.get('title'),
                         'document_path': record.get('document_path'), 'basis': 'changed_source_reference' if key in direct else 'graph_neighbor',
                         'source_paths': direct.get(key, []), 'action': 'review_target_source; do_not_inherit_measurements'})
    versions = set(target['version_sources'].values())
    gaps = list(target['gaps'])
    if not versions:
        gaps.append({'reason': 'target_version_not_resolved'})
    if len(versions) > 1:
        gaps.append({'reason': 'distribution_and_source_version_disagree', 'versions': sorted(versions)})
    environment_gaps = ['No target interpreter/dependency evidence; source checkout only.'] if target.get('environment') is None else ['GPU/driver, effective backend configuration and numerical behavior have not been tested.']
    if target['scope'] == 'package':
        environment_gaps.append('Repository documentation, dependency declarations and non-package files are outside observed scope.')
    environment_differences = {}
    if runtime_reference and target.get('environment'):
        observed = target['environment'].get('packages', {})
        for name, expected in runtime_reference['pins'].items():
            if name in observed and observed[name] != expected:
                environment_differences[name] = {'recorded_cpu_version': expected, 'target_version': observed[name]}
    metadata_drift = bool(versions and versions != {lock['version']}) or bool(target['git'].get('commit') and target['git']['commit'] != lock['commit']) or target['git'].get('dirty') is True
    status = 'evidence_incomplete' if gaps else 'review_required' if touched or metadata_drift or environment_differences else 'source_equivalent_in_observed_scope'
    report.update(status=status, target={k: target.get(k) for k in ('mode', 'scope', 'version_sources', 'git', 'environment', 'fingerprint')},
                  gaps=gaps, environment_gaps=environment_gaps, metadata_drift=metadata_drift,
                  environment_differences=environment_differences,
                  file_changes=changes, declaration_changes=decl_changes, excluded_unparsed_files=sorted(excluded),
                  text_only_python_changes=sorted(p for p in changes['changed'] if p in parsed_both and before['ast_hashes'][p] == target['ast_hashes'][p]),
                  unobserved_baseline_files=sorted(set(before['files']) - set(old_files)), affected_records=impacted,
                  counts={'compared_baseline_files': len(old_files), 'target_files': len(target['files']), 'changed_or_added_or_removed_files': len(touched),
                          'changed_or_added_or_removed_declarations': sum(map(len, decl_changes.values())), 'direct_records': len(direct), 'related_records': len(neighbors - set(direct))},
                  next_actions=['Inspect changed implementation and backend-effective defaults before deciding adaptations.',
                                'Review affected concepts, parameter guidance and paper mappings; consider new concepts without existing references.',
                                'Freeze target scene/device/dependencies/metrics and acceptance criteria before physical reruns.',
                                'Keep existing snapshot/evidence pinned; this report does not authorize publication.'])
    return report


def markdown(report):
    b = report['baseline']
    lines = ['# Newton version compatibility audit', '', '**Status:** ' + report['status'], '',
             f"Baseline: Newton {b['version']} / `{b['commit']}` / knowledge build `{b['build_id']}`.", '',
             'Runtime compatibility: **unverified**. Physical measurements are **not inherited**.', '',
             'Target evidence:', '```json', json.dumps(report['target'], ensure_ascii=False, indent=2), '```', '', '## Scope and gaps', '']
    for gap in report.get('gaps', []) + report.get('environment_gaps', []):
        lines.append('- ' + (gap if isinstance(gap, str) else json.dumps(gap, ensure_ascii=False)))
    if report.get('environment_differences'):
        lines += ['', 'Recorded CPU dependency differences (review requirements, not proven incompatibilities):',
                  '```json', json.dumps(report['environment_differences'], indent=2), '```']
    if 'counts' in report:
        lines += ['', '## Static comparison', '', '```json', json.dumps(report['counts'], indent=2), '```', '',
                  'All differences and affected records are in the adjacent JSON. These are review candidates, not confirmed breakages.', '',
                  '| Record | Kind | Evidence |', '| --- | --- | --- |']
        for r in report['affected_records'][:30]:
            lines.append('| ' + ' | '.join(str(x).replace('|', '\\|').replace('\n', ' ') for x in (r['id'], r['kind'], r['basis'])) + ' |')
    lines += ['', '## Next actions', ''] + ['- ' + x for x in report.get('next_actions', ['Collect actual target source/environment evidence.'])]
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    c = commands.add_parser('collect')
    inputs = c.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--source', type=Path)
    inputs.add_argument('--installed', action='store_true')
    c.add_argument('--out', type=Path, required=True)
    c = commands.add_parser('compare')
    c.add_argument('--knowledge-root', type=Path, required=True)
    inputs = c.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--target', type=Path)
    inputs.add_argument('--target-version')
    c.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('Output already exists; choose a new report path.')
    if args.command == 'collect':
        result, source = collect(args.source, args.installed)
        if args.out.resolve().is_relative_to(source):
            raise ValueError('Write evidence outside the audited source directory.')
        write_new(args.out, result)
        summary = {'files': len(result['files']), 'versions': result['version_sources'], 'scope': result['scope'], 'gaps': len(result['gaps'])}
    else:
        if args.out.suffix.lower() != '.json' or args.out.with_suffix('.md').exists():
            raise ValueError('Choose a new .json path with no existing adjacent .md file.')
        result = compare(args.knowledge_root, load(args.target) if args.target else None, args.target_version)
        write_new(args.out, result)
        write_new(args.out.with_suffix('.md'), markdown(result))
        summary = {'status': result['status'], 'counts': result.get('counts'), 'runtime_compatibility': result['runtime_compatibility']}
    print(json.dumps(dict(summary, output=str(args.out)), ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('Audit error: ' + str(exc), file=sys.stderr)
        raise SystemExit(2)
