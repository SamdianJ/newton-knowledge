"""Synthetic behavioral tests; no actual Newton import or physical claims."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import newton_version_audit as audit


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='newton-version-audit-')
        self.root = Path(self.temp.name)
        self.kb = self.root / 'knowledge repo'
        self.source = self.kb / 'sources/newton-v1.7.0'
        files = {'newton/__init__.py': 'raise RuntimeError("Newton must never be imported during collection")\n',
                 'newton/_version.py': '__version__ = "1.7.0"\n',
                 'newton/_src/solver.py': 'class Solver:\n    def __init__(self, damping=0.1):\n        self.damping = damping\n    def step(self):\n        return 1\n',
                 'pyproject.toml': '[project]\nname="newton"\nversion="1.7.0"\n', 'README.md': 'Synthetic test fixture\n'}
        for name, body in files.items():
            p = self.source / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body, encoding='utf-8')
        lock = {'version': '1.7.0', 'commit': 'fixture-commit', 'files': {p: audit.sha(self.source / p) for p in files}}
        self.save(self.kb / 'manifests/source-lock.json', lock)
        (self.kb / 'manifests/runtime-lock.txt').write_text('warp-lang==1.18.0\n', encoding='utf-8')
        build = self.kb / 'knowledge/builds/fixture'
        self.save(build / 'records.json', {'param': {'id': 'param', 'kind': 'parameter', 'owner_solver': 'mujoco',
                  'source_refs': [{'path': 'newton/_src/solver.py'}]}, 'paper': {'id': 'paper', 'kind': 'mapping', 'source_refs': []}})
        self.save(build / 'graph.json', {'edges': [{'source': 'param', 'target': 'paper'}]})
        self.save(build / 'manifest.json', {'build_id': 'fixture', 'version': '1.7.0', 'commit': 'fixture-commit',
                  'source_lock_sha256': audit.sha(self.kb / 'manifests/source-lock.json'),
                  'files': {n: audit.sha(build / n) for n in ('records.json', 'graph.json')}, 'programs': {}})
        self.save(self.kb / 'knowledge/current.json', {'build_id': 'fixture', 'path': 'knowledge/builds/fixture', 'manifest_sha256': audit.sha(build / 'manifest.json')})
        self.target = self.root / 'other computer source'
        shutil.copytree(self.source, self.target)

    def tearDown(self):
        self.temp.cleanup()

    def save(self, path, obj):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj), encoding='utf-8')

    def evidence(self, source=None):
        return audit.collect(source or self.target)[0]

    def test_exact_source_without_runtime_claim(self):
        r = audit.compare(self.kb, self.evidence())
        self.assertEqual(r['status'], 'source_equivalent_in_observed_scope')
        self.assertEqual(r['runtime_compatibility'], 'unverified')
        self.assertFalse(r['physical_evidence_inherited'])

    def test_same_version_default_change_impacts_parameter_and_paper(self):
        p = self.target / 'newton/_src/solver.py'
        p.write_text(p.read_text().replace('damping=0.1', 'damping=0.7'))
        r = audit.compare(self.kb, self.evidence())
        self.assertEqual(r['status'], 'review_required')
        self.assertIn('newton/_src/solver.py::Solver.__init__', r['declaration_changes']['changed'])
        self.assertEqual({x['id'] for x in r['affected_records']}, {'param', 'paper'})

    def test_body_change_without_signature_change(self):
        p = self.target / 'newton/_src/solver.py'
        p.write_text(p.read_text().replace('return 1', 'return 2'))
        r = audit.compare(self.kb, self.evidence())
        self.assertEqual(r['status'], 'review_required')
        self.assertEqual(r['counts']['changed_or_added_or_removed_declarations'], 0)

    def test_crlf_only_is_not_an_api_change(self):
        p = self.target / 'newton/_src/solver.py'
        original = p.read_bytes()
        p.write_bytes(original.replace(b'\r\n', b'\n') if b'\r\n' in original else original.replace(b'\n', b'\r\n'))
        r = audit.compare(self.kb, self.evidence())
        self.assertIn('newton/_src/solver.py', r['text_only_python_changes'])
        self.assertEqual(r['counts']['changed_or_added_or_removed_declarations'], 0)

    def test_package_scope_does_not_delete_repository_docs(self):
        r = audit.compare(self.kb, self.evidence(self.target / 'newton'))
        self.assertEqual(r['status'], 'source_equivalent_in_observed_scope')
        self.assertEqual(r['file_changes']['removed'], {})
        self.assertIn('README.md', r['unobserved_baseline_files'])

    def test_parse_failure_does_not_invent_removed_declarations(self):
        (self.target / 'newton/_src/solver.py').write_text('class Broken(:\n')
        r = audit.compare(self.kb, self.evidence())
        self.assertEqual(r['status'], 'evidence_incomplete')
        self.assertEqual(r['declaration_changes']['removed'], {})

    def test_added_feature_without_record_is_detected(self):
        (self.target / 'newton/_src/new_feature.py').write_text('def new_feature(x=2):\n    return x\n')
        r = audit.compare(self.kb, self.evidence())
        self.assertEqual(r['status'], 'review_required')
        self.assertIn('newton/_src/new_feature.py', r['file_changes']['added'])

    def test_removed_feature_is_detected(self):
        (self.target / 'newton/_src/solver.py').unlink()
        r = audit.compare(self.kb, self.evidence())
        self.assertIn('newton/_src/solver.py::Solver', r['declaration_changes']['removed'])

    def test_version_only_is_incomplete(self):
        self.assertEqual(audit.compare(self.kb, claimed_version='1.4.0')['status'], 'evidence_incomplete')

    def test_mismatched_metadata_and_dependency_drift(self):
        e = self.evidence()
        e['environment'] = {'packages': {'warp-lang': 'different'}}
        e['fingerprint'] = audit.digest({k: v for k, v in e.items() if k != 'fingerprint'})
        r = audit.compare(self.kb, e)
        self.assertEqual(r['status'], 'review_required')
        self.assertIn('warp-lang', r['environment_differences'])
        e['version_sources']['distribution_version'] = '1.4.0'
        e['fingerprint'] = audit.digest({k: v for k, v in e.items() if k != 'fingerprint'})
        self.assertEqual(audit.compare(self.kb, e)['status'], 'evidence_incomplete')

    def test_corrupt_transfer_and_unsafe_paths_rejected(self):
        e = self.evidence()
        e['files']['newton/__init__.py'] = '0' * 64
        with self.assertRaises(ValueError):
            audit.validate_evidence(e)
        e = self.evidence()
        e['files']['../outside'] = '0' * 64
        e['fingerprint'] = audit.digest({k: v for k, v in e.items() if k != 'fingerprint'})
        with self.assertRaises(ValueError):
            audit.validate_evidence(e)

    def test_modified_baseline_rejected(self):
        (self.source / 'newton/_src/solver.py').write_text('# tampered\n')
        with self.assertRaisesRegex(ValueError, 'Invalid locked source'):
            audit.compare(self.kb, self.evidence())

    def test_installed_collection_does_not_execute_newton(self):
        output = self.root / 'transfer.json'
        env = dict(os.environ, PYTHONPATH=str(self.target), PYTHONDONTWRITEBYTECODE='1')
        p = subprocess.run([sys.executable, '-B', str(Path(audit.__file__)), 'collect', '--installed', '--out', str(output)],
                           cwd=self.root, env=env, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        result = audit.load(output)
        self.assertFalse(result['environment']['newton_imported'])
        self.assertEqual(result['scope'], 'package')
        self.assertNotIn(str(self.target), output.read_text())

    def test_existing_output_preserved(self):
        p = self.root / 'existing.json'
        p.write_text('keep me')
        with self.assertRaises(FileExistsError):
            audit.write_new(p, {})
        self.assertEqual(p.read_text(), 'keep me')

    @unittest.skipUnless(shutil.which('git'), 'Git unavailable')
    def test_editable_package_git_identity_and_dirty_patch(self):
        def git(*args):
            return subprocess.check_output(['git', '-C', str(self.target), *args], stderr=subprocess.DEVNULL).decode().strip()
        git('init', '--quiet')
        git('add', '.')
        git('-c', 'user.name=Audit Fixture', '-c', 'user.email=audit@example.invalid', 'commit', '--quiet', '-m', 'synthetic fixture')
        expected = git('rev-parse', 'HEAD')
        e = self.evidence(self.target / 'newton')
        self.assertEqual(e['git'], {'commit': expected, 'dirty': False})
        (self.target / 'newton/_src/solver.py').write_text('# local change\n')
        self.assertTrue(self.evidence(self.target / 'newton')['git']['dirty'])

    @unittest.skipUnless(shutil.which('git'), 'Git unavailable')
    def test_enclosing_unrelated_git_repo_is_not_newton_identity(self):
        subprocess.run(['git', '-C', str(self.root), 'init', '--quiet'], check=True)
        self.assertIsNone(self.evidence()['git']['commit'])
        self.assertIsNone(self.evidence(self.target / 'newton')['git']['commit'])


if __name__ == '__main__':
    unittest.main()
