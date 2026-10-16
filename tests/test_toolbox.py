import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from genesis.toolbox import PermissionRequired, ToolContext, Toolbox, _fetch_public, _public_addresses


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


if __name__ == '__main__':
    unittest.main()
