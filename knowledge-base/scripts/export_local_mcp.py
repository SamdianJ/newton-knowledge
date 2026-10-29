"""Export a relocatable, byte-preserving MCP release; never mutate the knowledge build."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

from knowledge_store import snapshot

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / 'packaging/local-mcp'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def select_files(include_papers=False):
    store = snapshot()  # Fail before export if the published runtime is inconsistent.
    selected = set()

    def add(path):
        path = Path(path)
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT) or not path.is_file():
            raise ValueError('Not a regular workspace file: ' + str(path))
        selected.add(path)

    def tree(directory):
        for path in (ROOT / directory).rglob('*'):
            parts = path.relative_to(ROOT).parts
            if any(x.startswith('.venv') or x in {'.git', '__pycache__', '.cache', 'node_modules'} for x in parts):
                continue
            if path.is_file() and path.suffix not in {'.pyc', '.pyo'}:
                add(path)

    # Keep the current generation only; previous generations are not startup dependencies.
    add(ROOT / 'knowledge/current.json')
    for path in store.path.iterdir():
        if path.is_file():
            add(path)
    for path in (ROOT / 'knowledge').rglob('*'):
        if path.is_file() and not {'builds', 'staging', '__pycache__'}.intersection(path.relative_to(ROOT / 'knowledge').parts):
            add(path)
    for directory in ('experiments', 'solvers', 'manifests', 'graph', 'indexes', 'agent', 'experience'):
        tree(directory)
    for path in (ROOT / 'scripts').glob('*.py'):
        add(path)
    for path in (ROOT / 'planning').rglob('*'):
        if path.is_file() and 'history' not in path.relative_to(ROOT / 'planning').parts:
            add(path)
    tree('site/dist')
    for name in ('site/server.py', 'site/README.md', 'mcp_service/server.py', 'mcp_service/README.md', 'README.md'):
        add(ROOT / name)
    # All locked sources, including upstream license and dotfiles, remain byte-identical.
    for name in store.source_lock['files']:
        add(ROOT / 'sources/newton-v1.7.0' / name)
    for name in store.manifest['programs']:
        add(ROOT / name)
    for name in store.documents:
        add(ROOT / name)

    # Include published validation receipts and current delivery reports, not old traces/screenshots.
    receipts = load(ROOT / 'knowledge/validation-receipts.json')
    for item in receipts['records'].values():
        add(ROOT / item['report'])
    for path in (ROOT / 'evaluations').glob('*.json'):
        if 'trace' not in path.name:
            add(path)
    for directory in ('kamino-mechanisms-2026-10-29', 'kamino-pd-2026-10-29', 'mujoco-joint-contact-2026-10-29', 'solid-replays-2026-10-29'):
        folder = ROOT / 'evaluations' / directory
        for path in folder.glob('*'):
            if path.is_file() and (path.suffix == '.md' or path.name.startswith(('review-', 'design-')) and path.suffix in {'.json', '.py'}):
                add(path)
    # Protocols and reports can point to an additional pre-run design/analysis file.
    # Follow explicit file references, without traversing arbitrary directory names.
    for _ in range(4):
        before = len(selected)
        for path in list(selected):
            if path.suffix not in {'.json', '.md'} or path.stat().st_size > 15000000:
                continue
            text = path.read_text(encoding='utf-8-sig')
            refs = re.findall(r'(?:evaluations|planning)/[A-Za-z0-9_./-]+\.(?:json|md|py)', text)
            for ref in refs:
                target = ROOT / ref
                if target.is_file() and 'trace' not in target.name:
                    add(target)
        if len(selected) == before:
            break
    omitted = []
    for path in sorted((ROOT / 'sources/papers').rglob('*')):
        if path.is_file():
            if include_papers:
                add(path)
            else:
                omitted.append(dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path), bytes=path.stat().st_size, reason='Optional original paper asset; metadata, source links and citations remain included.'))
    return store, selected, omitted


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, help='New export directory; existing directories are never replaced.')
    ap.add_argument('--include-paper-assets', action='store_true', help='Also copy locally held original papers; their existing author/publisher rights remain unchanged.')
    ap.add_argument('--no-zip', action='store_true')
    args = ap.parse_args()
    store, selected, omitted = select_files(args.include_paper_assets)
    output = (args.output or ROOT / 'dist' / ('newton-mcp-' + store.build_id[:8])).resolve()
    if output.exists() or output.with_suffix('.zip').exists():
        raise ValueError('Output already exists; choose a new --output directory.')
    # Require all templates up front to avoid producing a misleading partial release.
    required = ('manage.py', 'smoke_test.py', 'requirements.lock.txt', 'README.md', 'THIRD_PARTY_NOTICES.md', '.gitignore', '.gitattributes')
    for name in required:
        if not (TEMPLATES / name).is_file():
            raise ValueError('Missing release template: ' + name)
    output.mkdir(parents=True)
    data = output / 'knowledge-base'
    for path in sorted(selected):
        dest = data / path.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    for path in sorted(TEMPLATES.iterdir()):
        if path.is_file():
            shutil.copyfile(path, output / path.name)
    files = {p.relative_to(output).as_posix(): sha(p) for p in sorted(output.rglob('*')) if p.is_file()}
    manifest = dict(schema_version=1, build_id=store.build_id, data_root='knowledge-base', newton_version='1.7.0', source_commit=store.source_lock['commit'], files=files, omitted_resources=omitted, exporter_sha256=sha(__file__), source_pointer_sha256=sha(ROOT / 'knowledge/current.json'), capabilities=dict(stdio_mcp=True, local_website=True, physics_execution=False, paper_originals=args.include_paper_assets))
    (output / 'package-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    archive = None
    if not args.no_zip:
        archive = output.with_suffix('.zip')
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for path in sorted(output.rglob('*')):
                if path.is_file():
                    info = zipfile.ZipInfo(output.name + '/' + path.relative_to(output).as_posix(), date_time=(2026, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o100644 << 16
                    z.writestr(info, path.read_bytes())
        archive.with_suffix('.zip.sha256').write_text(sha(archive) + '  ' + archive.name + '\n', encoding='utf-8')
    print(json.dumps(dict(output=str(output), build_id=store.build_id, files=len(files), unpacked_bytes=sum(p.stat().st_size for p in output.rglob('*') if p.is_file()), zip=str(archive) if archive else None, zip_bytes=archive.stat().st_size if archive else None, optional_paper_files_omitted=len(omitted)), ensure_ascii=False))


if __name__ == '__main__':
    main()
