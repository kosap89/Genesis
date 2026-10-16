import json
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from genesis.toolbox import PermissionRequired, ToolContext, Toolbox, _fetch_public, _public_addresses, _unified_patch


class ToolboxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / 'project'
        self.source.mkdir()
        self.tools = Toolbox(ToolContext(self.base / 'workspace', self.source))

    def test_workspace_roundtrip_and_report(self):
        self.tools.execute('workspace_write', {'path': 'nested/code.py', 'content': 'print(1)'})
        self.assertEqual(self.tools.execute('workspace_read', {'path': 'nested/code.py'})['content'], 'print(1)')
        result = self.tools.execute('artifact_report', {'name': 'report.md', 'content': 'Verified result'})
        self.assertEqual(result['artifact'], 'artifacts/report.md')
        json.dumps(self.tools.schemas())

    def test_traversal_absolute_and_stream_paths_rejected(self):
        for path in ('../outside', 'nested/../../outside', str(self.base / 'outside'), 'a:stream', 'CON', 'nul.txt', 'trailing. '):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.tools.execute('workspace_write', {'path': path, 'content': 'x'})
        self.assertFalse((self.base / 'outside').exists())

    def test_symlink_rejected(self):
        link = self.tools.context.root / 'link'
        try:
            link.symlink_to(self.source, target_is_directory=True)
        except OSError:
            self.skipTest('OS does not permit creating symlinks')
        with self.assertRaises(ValueError):
            self.tools.execute('workspace_write', {'path': 'link/escaped', 'content': 'x'})

    def test_execution_and_network_require_permissions(self):
        for name, args, action in [('terminal', {'command': ['python', '-c', 'print(1)']}, 'terminal'),
                                   ('run_python_tests', {}, 'terminal'),
                                   ('research_fetch_url', {'url': 'https://example.com'}, 'network'),
                                   ('research_search', {'query': 'science'}, 'network')]:
            with self.subTest(name=name), self.assertRaises(PermissionRequired) as caught:
                self.tools.execute(name, args)
            self.assertEqual(caught.exception.action, action)

    def test_real_python_tests_and_failure(self):
        self.tools.context.allow_terminal = True
        self.tools.execute('workspace_write', {'path': 'test_example.py', 'content': 'import unittest\nclass TestExample(unittest.TestCase):\n def test_bad(self): self.assertEqual(1, 2)\n'})
        result = self.tools.execute('run_python_tests', {})
        self.assertEqual(result['returncode'], 1)
        self.assertIn('FAILED', result['output'])
        self.tools.execute('workspace_write', {'path': 'test_example.py', 'content': 'import unittest\nclass TestExample(unittest.TestCase):\n def test_ok(self): self.assertEqual(1, 1)\n'})
        self.assertEqual(self.tools.execute('run_python_tests', {})['returncode'], 0)

    def test_restricted_terminal_and_bounded_output(self):
        self.tools.context.allow_terminal = True
        with self.assertRaises(ValueError):
            self.tools.execute('terminal', {'command': ['powershell', 'Remove-Item']})
        result = self.tools.execute('terminal', {'command': ['python', '-c', 'print("x" * 50000)']})
        self.assertTrue(result['truncated'])
        self.assertLessEqual(len(result['output']), 32000)

    def test_timeout(self):
        self.tools.context.allow_terminal = True
        result = self.tools.execute('terminal', {'command': ['python', '-c', 'import time; time.sleep(10)'], 'timeout': 1})
        self.assertTrue(result['timed_out'])

    def test_subprocess_does_not_inherit_provider_or_arbitrary_secrets(self):
        self.tools.context.allow_terminal = True
        secrets = {'GENESIS_OPENAI_API_KEY': 'test-only-provider-secret',
                   'OPENAI_API_KEY': 'test-only-alternate-secret',
                   'COMPANY_PRIVATE_TOKEN': 'test-only-company-secret'}
        with patch.dict('os.environ', secrets):
            result = self.tools.execute('terminal', {'command': ['python', '-c',
                'import json, os; print(json.dumps(dict(os.environ)))']})
        self.assertEqual(result['returncode'], 0)
        child_environment = json.loads(result['output'])
        for name, secret in secrets.items():
            self.assertNotIn(name, child_environment)
            self.assertNotIn(secret, result['output'])

    def test_private_dns_is_rejected(self):
        for address in ('127.0.0.1', '10.0.0.1', '169.254.169.254', '::1', 'fd00::1'):
            with self.subTest(address=address), patch('genesis.toolbox.socket.getaddrinfo', return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, '', (address, 443))]):
                with self.assertRaises(ValueError):
                    _public_addresses('example.com', 443)

    def test_https_credentials_and_ports(self):
        for url in ('http://example.com', 'https://user:pass@example.com', 'https://example.com:8080'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                _fetch_public(url)

    def test_redirect_revalidates_target(self):
        response = unittest.mock.Mock(status=302)
        response.getheader.return_value = 'https://127.0.0.1/private'
        connection = unittest.mock.Mock()
        connection.getresponse.return_value = response
        with patch('genesis.toolbox._public_addresses', side_effect=[[(2, 1, 6, '', ('93.184.216.34', 443))], ValueError('private')]) as resolve, patch('genesis.toolbox._PinnedHTTPS', return_value=connection):
            with self.assertRaises(ValueError):
                _fetch_public('https://example.com')
            self.assertEqual(resolve.call_count, 2)

    def test_snapshot_excludes_secrets_and_does_not_modify_source(self):
        (self.source / 'main.py').write_text('original', encoding='utf-8')
        (self.source / '.env').write_text('secret', encoding='utf-8')
        (self.source / 'credentials.json').write_text('secret', encoding='utf-8')
        (self.source / 'data').mkdir()
        (self.source / 'data' / 'company.json').write_text('private', encoding='utf-8')
        result = self.tools.execute('self_improvement_snapshot', {})
        self.assertEqual(result['files'], 1)
        self.tools.execute('workspace_write', {'path': 'source/main.py', 'content': 'candidate'})
        self.assertEqual((self.source / 'main.py').read_text(encoding='utf-8'), 'original')
        self.assertFalse((self.tools.context.root / 'source' / '.env').exists())

    def test_actual_candidate_diff_tracks_add_change_delete_and_persistent_baseline(self):
        (self.source / 'changed.py').write_text('value = 1\n', encoding='utf-8')
        (self.source / 'deleted.py').write_text('removed = True\n', encoding='utf-8')
        (self.source / 'stable.py').write_text('stable = True\n', encoding='utf-8')
        self.tools.execute('self_improvement_snapshot', {})
        self.tools.execute('workspace_write', {'path': 'source/changed.py', 'content': 'value = 2\n'})
        self.tools.execute('workspace_write', {'path': 'source/added.py', 'content': 'added = True\n'})
        (self.tools.context.root / 'source' / 'deleted.py').unlink()
        # A new toolbox instance must use the persisted original, even if live code evolved.
        (self.source / 'changed.py').write_text('value = 99\n', encoding='utf-8')
        reopened = Toolbox(self.tools.context)
        result = reopened.execute('self_improvement_diff', {})
        self.assertEqual(result['changed'], ['changed.py'])
        self.assertEqual(result['added'], ['added.py'])
        self.assertEqual(result['deleted'], ['deleted.py'])
        self.assertEqual(result['live_source_changed'], ['changed.py'])
        self.assertEqual(result['comparison'], 'original_snapshot_baseline')
        self.assertIn('-value = 1\n+value = 2\n', result['patch'].replace('\r\n', '\n'))
        self.assertIn('--- /dev/null\n+++ b/added.py\n', result['patch'])
        self.assertIn('--- a/deleted.py\n+++ /dev/null\n', result['patch'])
        self.assertEqual((self.source / 'changed.py').read_text(encoding='utf-8'), 'value = 99\n')
        self.assertTrue((self.source / 'deleted.py').exists())
        self.assertEqual((self.tools.context.root / result['artifact']).read_bytes(), result['patch'].encode('utf-8'))
        self.assertFalse(result['truncated'])

    def test_diff_requires_snapshot_and_protects_baseline(self):
        with self.assertRaises(ValueError):
            self.tools.execute('self_improvement_diff', {})
        (self.source / 'main.py').write_text('before\n', encoding='utf-8')
        self.tools.execute('self_improvement_snapshot', {})
        for path in ('.genesis-snapshot.json', '.genesis-baseline/main.py'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.tools.execute('workspace_write', {'path': path, 'content': 'corrupt'})
        entries = self.tools.execute('workspace_list', {})['entries']
        self.assertFalse(any(entry['name'].startswith('.genesis-') for entry in entries))
        # Approved Python has host access; integrity checks still detect changed original bytes.
        (self.tools.context.root / '.genesis-baseline' / 'main.py').write_text('corrupt', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'integrity'):
            self.tools.execute('self_improvement_diff', {})

    def test_diff_omits_secrets_binary_and_oversized_patches_explicitly(self):
        (self.source / 'large.txt').write_text('a' * 60000 + '\n', encoding='utf-8')
        self.tools.execute('self_improvement_snapshot', {})
        self.tools.execute('workspace_write', {'path': 'source/large.txt', 'content': 'b' * 60000 + '\n'})
        self.tools.execute('workspace_write', {'path': 'source/.env', 'content': 'PRIVATE=secret-value'})
        self.tools.execute('workspace_write', {'path': 'source/credentials.json', 'content': 'private-value'})
        self.tools.execute('workspace_write', {'path': 'source/new.py', 'content': 'new = True\n'})
        (self.tools.context.root / 'source' / 'binary.bin').write_bytes(b'\x00\xff')
        result = self.tools.execute('self_improvement_diff', {})
        self.assertEqual(result['binary'], ['binary.bin'])
        self.assertIn('large.txt', result['omitted_patch_files'])
        self.assertTrue(result['truncated'])
        self.assertLessEqual(result['patch_bytes'], 100000)
        self.assertIn('+++ b/new.py', result['patch'])
        self.assertNotIn('credentials.json', result['added'])
        self.assertNotIn('.env', result['added'])
        self.assertNotIn('secret-value', result['patch'])

    def test_diff_preserves_missing_final_newline_marker(self):
        (self.source / 'text.txt').write_text('old', encoding='utf-8')
        self.tools.execute('self_improvement_snapshot', {})
        self.tools.execute('workspace_write', {'path': 'source/text.txt', 'content': 'new'})
        result = self.tools.execute('self_improvement_diff', {})
        self.assertIn('-old\n\\ No newline at end of file\n+new\n\\ No newline at end of file\n', result['patch'])

    def test_oversized_candidate_is_not_misrepresented_as_deletion(self):
        (self.source / 'large.txt').write_text('small\n', encoding='utf-8')
        self.tools.execute('self_improvement_snapshot', {})
        (self.tools.context.root / 'source' / 'large.txt').write_bytes(b'x' * 1000001)
        result = self.tools.execute('self_improvement_diff', {})
        self.assertEqual(result['deleted'], [])
        self.assertEqual(result['skipped_candidate_files'], ['large.txt'])
        self.assertEqual(result['patch'], '')

    def test_generated_patch_applies_exact_bytes_with_git(self):
        git = shutil.which('git')
        if not git:
            self.skipTest('Git is needed for independent unified patch verification')
        fixtures = {
            'lf.txt': (b'old\nlast\n', b'new\nlast\n'),
            'crlf.txt': (b'old\r\nlast\r\n', b'new\r\nlast\r\n'),
            'no-newline.txt': (b'old', b'new'),
            'newline-added.txt': (b'last', b'last\n'),
            'newline-removed.txt': (b'last\n', b'last'),
            'unicode.txt': ('old\u2028value\x0cend\n'.encode(), 'new\u2028value\x0cend\n'.encode()),
            'added space.txt': (None, b'added without newline'),
            'deleted.txt': (b'deleted\r\n', None),
        }
        application = self.base / 'patch-application'
        application.mkdir()
        chunks = []
        for name, (before, after) in fixtures.items():
            if before is not None:
                (application / name).write_bytes(before)
            chunks.append(_unified_patch(name, before, after))
        patchfile = self.base / 'review.patch'
        patchfile.write_bytes(''.join(chunks).encode('utf-8'))
        result = subprocess.run([git, 'apply', '--check', str(patchfile)], cwd=application,
                                capture_output=True, timeout=15, check=False)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        result = subprocess.run([git, 'apply', str(patchfile)], cwd=application,
                                capture_output=True, timeout=15, check=False)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        for name, (_, after) in fixtures.items():
            with self.subTest(name=name):
                if after is None:
                    self.assertFalse((application / name).exists())
                else:
                    self.assertEqual((application / name).read_bytes(), after)

    def test_snapshot_excludes_nested_internal_metadata(self):
        (self.source / 'module').mkdir()
        (self.source / 'module' / '.genesis-baseline').mkdir()
        (self.source / 'module' / '.genesis-baseline' / 'hidden.py').write_bytes(b'hidden')
        (self.source / '.genesis-snapshot.json').write_bytes(b'private metadata')
        (self.source / 'module' / 'real.py').write_bytes(b'real\n')
        snapshot = self.tools.execute('self_improvement_snapshot', {})
        self.assertEqual(snapshot['files'], 1)
        candidate = self.tools.context.root / 'source'
        self.assertFalse((candidate / '.genesis-snapshot.json').exists())
        self.assertFalse((candidate / 'module' / '.genesis-baseline').exists())
        self.assertEqual(self.tools.execute('self_improvement_diff', {})['patch'], '')


if __name__ == '__main__':
    unittest.main()
