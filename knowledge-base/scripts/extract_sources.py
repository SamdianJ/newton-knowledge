"""Rebuild the VBD 1.7.0 source inventory without importing/executing Newton."""
from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'sources/newton-v1.7.0'
SHA = '7e75abe28b8d69522bc0b34837aaed2c303dff5a'
BASE = f'https://github.com/newton-physics/newton/blob/{SHA}/'

def dump(rel, value):
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def ref(path, line, end=None):
    return {'repository': 'newton-physics/newton', 'commit': SHA, 'path': path,
            'line': line, 'end_line': end or line,
            'url': BASE + path + f'#L{line}' + (f'-L{end}' if end and end != line else '')}

def main():
    head = subprocess.check_output(['git', '-C', str(SRC), 'rev-parse', 'HEAD'], text=True).strip()
    if head != SHA:
        raise SystemExit(f'Wrong source revision: {head}')
    symbols, files, model_uses = [], [], {}
    paths = sorted((SRC / 'newton/_src/solvers/vbd').glob('*.py'))
    paths += [SRC/'newton/_src/geometry/tri_mesh_collision.py', SRC/'newton/_src/solvers/solver.py', SRC/'newton/_src/sim/model.py']
    for p in paths:
        rel = p.relative_to(SRC).as_posix()
        text = p.read_text(encoding='utf-8')
        tree = ast.parse(text)
        files.append({'path': rel, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'lines': len(text.splitlines())})
        def visit(node, owner=''):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    name = owner + '.' + child.name if owner else child.name
                    calls = sorted({ast.unparse(n.func) for n in ast.walk(child) if isinstance(n, ast.Call)}) if not isinstance(child, ast.ClassDef) else []
                    symbols.append({'id': 'code:1.7.0:' + rel + '::' + name + '@L' + str(child.lineno), 'name': name,
                        'kind': type(child).__name__, 'source': ref(rel, child.lineno, child.end_lineno),
                        'docstring': ast.get_docstring(child) or '', 'calls_syntactic': calls})
                    visit(child, name)
                else:
                    visit(child, owner)
        visit(tree)
        if '/vbd/' in rel:
            for n in ast.walk(tree):
                if isinstance(n, ast.Attribute):
                    expr = ast.unparse(n)
                    if expr.startswith(('self.model.', 'model.')):
                        key = expr.removeprefix('self.').removeprefix('model.')
                        if '.' not in key:
                            model_uses.setdefault(key, []).append(ref(rel, n.lineno))
    sp = SRC/'newton/_src/solvers/vbd/solver_vbd.py'
    text = sp.read_text(encoding='utf-8')
    tree = ast.parse(text)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'SolverVBD')
    init = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '__init__')
    docs = ast.get_docstring(init) or ''
    all_args = init.args.args[1:] + init.args.kwonlyargs
    defaults = [None]*(len(init.args.args)-1-len(init.args.defaults)) + list(init.args.defaults) + list(init.args.kw_defaults)
    names = {a.arg for a in all_args}
    paragraphs = {}
    active = None
    for line in docs.splitlines():
        match = re.match(r'^    (\w+):\s*(.*)', line)
        if match and match.group(1) in names:
            active = match.group(1)
            paragraphs[active] = [match.group(2)]
        elif line.strip() and (not line.startswith(' ') or re.match(r'^    [A-Z][^:]+:$', line)):
            active = None
        elif active:
            paragraphs[active].append(line.strip())
    records = []
    for a, default in zip(all_args, defaults):
        name = a.arg
        uses = [ref(sp.relative_to(SRC).as_posix(), i) for i, line in enumerate(text.splitlines(), 1)
                if re.search(r'\b' + re.escape(name) + r'\b', line)]
        records.append({'id': 'newton:1.7.0:SolverVBD:' + name, 'name': name,
            'owner': 'newton.solvers.SolverVBD.__init__', 'type': ast.unparse(a.annotation) if a.annotation else None,
            'required': default is None, 'declared_default_expression': ast.unparse(default) if default is not None else None,
            'documentation': '\n'.join(paragraphs.get(name, [])).strip(),
            'definition': ref(sp.relative_to(SRC).as_posix(), a.lineno),
            'textual_occurrences': uses,
            'evidence_type': 'pinned_source_static',
            'runtime_experiment': 'not_run',
        })
    dump('solvers/vbd/parameters.raw.json', {'version':'1.7.0', 'commit': SHA, 'records':records})
    dump('indexes/source_symbols.json', {'commit':SHA, 'call_edges_are':'syntactic_not_resolved_runtime_callgraph', 'symbols':symbols})
    dump('indexes/model_field_uses.json', {'commit':SHA, 'scope':'direct model.field / self.model.field syntax in VBD modules; aliases are not resolved', 'fields':model_uses})
    extra_paths = ['newton/_src/sim/builder.py','docs/solvers/vbd.rst','docs/concepts/simulation_tuning_vbd.rst','newton/tests/test_solver_vbd.py','newton/tests/test_solver_vbd_contact_force.py','newton/tests/test_vbd_interval_arithmetic.py','newton/examples/multiphysics/example_vbd_dat_rigid_soft.py','newton/examples/multiphysics/example_mujoco_vbd_coupled_solver.py','LICENSE.md']
    for rel in extra_paths:
        p=SRC/rel
        files.append({'path':rel,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'lines':len(p.read_text(encoding='utf-8').splitlines()),'scope':'reference file preserved; not every line manually reviewed'})
    dump('manifests/newton-1.7.0.json', {'repository':'https://github.com/newton-physics/newton',
        'tag':'v1.7.0', 'commit':SHA, 'source_path':'sources/newton-v1.7.0',
        'source_role':'read_only_official_release', 'kb_created_local_date':'2026-10-27',
        'source_license':'Code Apache-2.0; documentation files may be CC-BY-4.0; preserve per-file SPDX and LICENSE.md',
        'inspected_files':files, 'latest_web_docs_authoritative':False})
    print(json.dumps({'parameters_including_model':len(records), 'symbols':len(symbols), 'model_fields':len(model_uses)}, ensure_ascii=False))

if __name__ == '__main__':
    main()
