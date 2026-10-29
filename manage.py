"""Portable, stdlib-only management for a published Newton knowledge bundle."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import sqlite3
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'knowledge-base'
sys.dont_write_bytecode = True


def runtime_python():
    return ROOT / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def require_python():
    if sys.version_info < (3, 12):
        raise RuntimeError('Python 3.12 or newer is required. Install Python, then rerun this command.')


def safe_path(relative):
    if not isinstance(relative, str) or not relative or any(c in relative for c in ('\\', ':', '\x00')):
        raise ValueError('Invalid manifest path: ' + repr(relative))
    p = Path(relative)
    if p.is_absolute() or any(part in ('.', '..') for part in p.parts):
        raise ValueError('Unsafe manifest path: ' + relative)
    result = ROOT / p
    cursor = ROOT
    for part in p.parts:
        cursor = cursor / part
        if cursor.is_symlink() or getattr(cursor, 'is_junction', lambda: False)():
            raise ValueError('Linked files/directories are forbidden in the bundle: ' + relative)
    if not result.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError('Manifest path escapes the bundle: ' + relative)
    return result


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def verify():
    manifest_path = ROOT / 'package-manifest.json'
    if manifest_path.is_symlink():
        raise ValueError('The package manifest must be a regular file.')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('schema_version') != 1 or not isinstance(manifest.get('files'), dict) or not manifest['files']:
        raise ValueError('Unsupported or empty package manifest.')
    failures = []
    for name, expected in manifest['files'].items():
        p = safe_path(name)
        if not p.is_file() or sha(p) != expected:
            failures.append(name)
    if failures:
        raise RuntimeError('Bundle files are missing or changed: ' + ', '.join(failures[:12]) + '. Restore the release bytes; Git must preserve line endings (see .gitattributes). Fetch Git LFS objects if used.')
    if manifest.get('data_root') != 'knowledge-base':
        raise ValueError('Unsupported package data root.')
    pointer = json.loads((DATA / 'knowledge/current.json').read_text(encoding='utf-8'))
    if pointer['build_id'] != manifest['build_id']:
        raise RuntimeError('Bundle and current knowledge build disagree.')
    sys.path.insert(0, str(DATA / 'scripts'))
    from knowledge_store import snapshot
    store = snapshot()
    if store.build_id != manifest['build_id']:
        raise RuntimeError('Runtime loaded an unexpected knowledge build.')
    return {'status': 'passed', 'build_id': store.build_id, 'verified_files': len(manifest['files'])}


def in_runtime():
    # sys.executable.resolve() follows POSIX venv symlinks, so compare prefixes.
    return Path(sys.prefix).resolve() == (ROOT / '.venv').resolve()


def require_runtime():
    exe = runtime_python()
    if not exe.is_file():
        raise RuntimeError('Runtime is not installed. Run: python manage.py install')
    return exe


def reexec_runtime(arguments):
    exe = require_runtime()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8')
    command = [str(exe), '-B', '-X', 'utf8', *map(str, arguments)]
    if os.name == 'nt':
        # Windows CRT execve does not quote argv containing spaces and exits the
        # launcher before the replacement's result is observable. Popen quotes
        # arguments correctly; inherit the protocol streams without printing.
        completed = subprocess.run(command, env=env, stdin=sys.stdin,
                                   stdout=sys.stdout, stderr=sys.stderr)
        raise SystemExit(completed.returncode)
    os.execve(str(exe), command, env)


def config(fmt, site_url=None):
    exe = require_runtime()
    command = str(exe)
    args = ['-B', '-X', 'utf8', str(DATA / 'mcp_service/server.py')]
    env = {'PYTHONIOENCODING': 'utf-8', 'PYTHONDONTWRITEBYTECODE': '1'}
    if site_url:
        env['NEWTON_KB_SITE_URL'] = site_url
    if fmt == 'json':
        print(json.dumps({'mcpServers': {'newton_knowledge': {'command': command, 'args': args, 'env': env}}}, ensure_ascii=False, indent=2))
    else:
        # JSON string quoting is compatible with TOML basic strings for these values.
        q = lambda value: json.dumps(value, ensure_ascii=False)
        print('[mcp_servers.newton_knowledge]')
        print('command = ' + q(command))
        print('args = [' + ', '.join(q(a) for a in args) + ']')
        print('[mcp_servers.newton_knowledge.env]')
        for k, value in env.items():
            print(k + ' = ' + q(value))


def main():
    require_python()
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    install = sub.add_parser('install', help='Create a fresh local virtual environment and install locked runtime dependencies.')
    install.add_argument('--wheelhouse', type=Path, help='Install offline from a directory of pre-downloaded wheels.')
    sub.add_parser('verify', help='Verify all immutable distributed bytes and the current snapshot.')
    sub.add_parser('doctor', help='Check the installed runtime, SQLite FTS5 and bundle integrity.')
    cfg = sub.add_parser('config', help='Print client configuration for this directory; does not edit global settings.')
    cfg.add_argument('--format', choices=['json', 'toml'], default='json')
    cfg.add_argument('--site-url', help='Optional website base URL included in the client environment, e.g. http://127.0.0.1:18449.')
    sub.add_parser('mcp', help='Start the read-only stdio MCP server. Stdout is protocol only.')
    site = sub.add_parser('site', help='Run the optional loopback-only knowledge website in this terminal.')
    site.add_argument('--port', type=int, default=18448)
    sub.add_parser('smoke', help='Exercise the real six-tool stdio server from an unrelated working directory.')
    args = ap.parse_args()
    if args.command == 'install':
        result = verify()
        print(json.dumps(result, ensure_ascii=False))
        venv.EnvBuilder(with_pip=True).create(ROOT / '.venv')
        command = [str(runtime_python()), '-m', 'pip', 'install', '--disable-pip-version-check', '-r', str(ROOT / 'requirements.lock.txt')]
        if args.wheelhouse:
            if not args.wheelhouse.is_dir():
                raise ValueError('The wheelhouse directory does not exist.')
            command += ['--no-index', '--find-links', str(args.wheelhouse.resolve())]
        subprocess.run(command, check=True)
        print('Installed. Next: python manage.py doctor; python manage.py smoke; python manage.py config')
    elif args.command == 'verify':
        print(json.dumps(verify(), ensure_ascii=False, indent=2))
    elif args.command == 'doctor':
        if not in_runtime():
            reexec_runtime([ROOT / 'manage.py', 'doctor'])
        result = verify()
        with sqlite3.connect(':memory:') as con:
            con.execute('CREATE VIRTUAL TABLE probe USING fts5(text)')
            con.execute("INSERT INTO probe VALUES ('Newton')")
            assert con.execute("SELECT count(*) FROM probe WHERE probe MATCH 'Newton'").fetchone()[0] == 1
        installed = {name: importlib.metadata.version(name) for name in ('mcp', 'jsonschema', 'Markdown', 'tzdata')}
        if installed['mcp'] != '2.3.0':
            raise RuntimeError('Unexpected MCP SDK version; reinstall locked dependencies.')
        result.update(python=sys.version.split()[0], executable=sys.executable, sqlite_fts5=True, packages=installed)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == 'config':
        config(args.format, args.site_url)
    elif args.command == 'mcp':
        # Never print bootstrap/status messages on the protocol stream.
        reexec_runtime([DATA / 'mcp_service/server.py'])
    elif args.command == 'site':
        if not 1 <= args.port <= 65535:
            raise ValueError('Port must be between 1 and 65535.')
        reexec_runtime([DATA / 'site/server.py', '--port', str(args.port)])
    else:
        reexec_runtime([ROOT / 'smoke_test.py'])


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print('Error: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
