"""Real candidate repair, test execution, and patch delivery with a test-only model."""
import copy
import http.client
import io
import json
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path

from genesis.engine import Engine
from genesis.providers import ProviderResult
from genesis.server import GenesisServer


BROKEN = 'def average(values):\n    return sum(values) // len(values)\n'
FIXED = 'def average(values):\n    return sum(values) / len(values)\n'
REGRESSION = ('import unittest\nfrom arithmetic import average\n'
              'class AverageTests(unittest.TestCase):\n'
              '    def test_fractional_average(self):\n'
              '        self.assertEqual(average([3, 4]), 3.5)\n')


def tool(name, arguments, identifier):
    return {'name': name, 'arguments': arguments, 'id': identifier}


def response(text='', calls=None):
    return ProviderResult(text, calls or [], 30, 15, 'openai', 'test-only-improvement-router')


class ImprovementRouterDouble:
    """Asserts observed tool evidence before scripting the next test-only response."""
    def __init__(self, case):
        self.case = case
        self.turn = 0
        self.requests = []

    def generate(self, messages, tools, config):
        self.requests.append(copy.deepcopy(messages))
        self.turn += 1
        outputs = {m['tool_call_id']: json.loads(m['content']) for m in messages if m['role'] == 'tool'}
        if self.turn == 1:
            return response(calls=[tool('self_improvement_snapshot', {}, 'snapshot')])
        if self.turn == 2:
            self.case.assertEqual(outputs['snapshot']['files'], 2)
            self.case.assertFalse(outputs['snapshot']['source_modified'])
            return response(calls=[tool('workspace_read', {'path': 'source/arithmetic.py'}, 'read-code'),
                                   tool('workspace_read', {'path': 'source/test_arithmetic.py'}, 'read-regression')])
        if self.turn == 3:
            self.case.assertEqual(outputs['read-code']['content'], BROKEN)
            self.case.assertEqual(outputs['read-regression']['content'], REGRESSION)
            return response(calls=[tool('run_python_tests', {'path': 'source'}, 'baseline-tests')])
        if self.turn == 4:
            self.case.assertNotEqual(outputs['baseline-tests']['returncode'], 0)
            self.case.assertIn('3.5', outputs['baseline-tests']['output'])
            self.case.assertIn('FAILED', outputs['baseline-tests']['output'])
            return response(calls=[tool('workspace_write', {'path': 'source/arithmetic.py', 'content': FIXED}, 'repair')])
        if self.turn == 5:
            self.case.assertEqual(outputs['repair']['bytes'], len(FIXED.encode()))
            return response(calls=[tool('run_python_tests', {'path': 'source'}, 'candidate-tests')])
        if self.turn == 6:
            self.case.assertEqual(outputs['candidate-tests']['returncode'], 0)
            self.case.assertIn('Ran 1 test', outputs['candidate-tests']['output'])
            self.case.assertIn('OK', outputs['candidate-tests']['output'])
            return response(calls=[tool('self_improvement_diff', {}, 'candidate-diff')])
        if self.turn == 7:
            patch = outputs['candidate-diff']
            self.case.assertEqual(patch['changed'], ['arithmetic.py'])
            self.case.assertFalse(patch['source_modified'])
            self.case.assertIn('-    return sum(values) // len(values)', patch['patch'])
            self.case.assertIn('+    return sum(values) / len(values)', patch['patch'])
            return response('Candidate fixes fractional averages. The regression failed before the edit and passed afterward. Review artifacts/self-improvement.patch; live source has not been changed.')
        raise AssertionError('Unexpected extra request in self-improvement integration test')


class ImprovementIntegrationTests(unittest.TestCase):
    def test_observed_bug_repaired_tested_and_delivered_as_review_patch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'live-source'
            source.mkdir()
            (source / 'arithmetic.py').write_bytes(BROKEN.encode())
            (source / 'test_arithmetic.py').write_bytes(REGRESSION.encode())
            originals = {p.name: p.read_bytes() for p in source.iterdir()}
            router = ImprovementRouterDouble(self)
            engine = Engine(root / 'state', source, router)
            try:
                task = engine.create_task('Repair fractional-average bug in a candidate and produce a tested review patch.', role='engineering')
                workspace = engine.workspace(task)
                engine.run(task['id'])
                self.assertEqual(engine.store.get('tasks', task['id'])['status'], 'waiting_approval')
                self.assertEqual(router.turn, 3)
                self.assertFalse(any(m.get('tool_call_id') == 'baseline-tests' for m in engine.store.messages(task['id'])))
                first = next(a for a in engine.store.all('approvals') if a['task_id'] == task['id'] and a['status'] == 'pending')
                self.assertEqual(first['action'], 'terminal')
                engine.decide(first['id'], 'approved')
                engine.run(task['id'])

                # Changed candidate code needs a separate invocation approval.
                self.assertEqual(engine.store.get('tasks', task['id'])['status'], 'waiting_approval')
                self.assertEqual(router.turn, 5)
                self.assertEqual((workspace / 'source/arithmetic.py').read_text(), FIXED)
                second = next(a for a in engine.store.all('approvals') if a['task_id'] == task['id'] and a['status'] == 'pending')
                self.assertNotEqual(second['id'], first['id'])
                engine.decide(second['id'], 'approved')
                engine.run(task['id'])

                final = engine.store.get('tasks', task['id'])
                self.assertEqual(final['status'], 'completed', final['error'])
                self.assertEqual(router.turn, 7)
                self.assertIn('regression failed', final['result'])
                self.assertEqual({p.name: p.read_bytes() for p in source.iterdir()}, originals)
                self.assertEqual((workspace / '.genesis-baseline/arithmetic.py').read_bytes(), BROKEN.encode())
                patch_bytes = (workspace / 'artifacts/self-improvement.patch').read_bytes()
                self.assertTrue(patch_bytes.startswith(b'--- a/arithmetic.py\n+++ b/arithmetic.py\n@@'))
                self.assertIn(b'-    return sum(values) // len(values)', patch_bytes)
                self.assertIn(b'+    return sum(values) / len(values)', patch_bytes)
                artifacts = [a for a in engine.store.all('artifacts') if a['task_id'] == task['id']]
                self.assertTrue(any(a['path'] == 'artifacts/self-improvement.patch' for a in artifacts))
                self.assertFalse(any(any(p.startswith('.genesis-') for p in Path(a['path']).parts) for a in artifacts))
                self.assert_bundle_excludes_baseline(engine, task, source, patch_bytes)
            finally:
                engine.close()

    def assert_bundle_excludes_baseline(self, engine, task, source, patch_bytes):
        server = GenesisServer(('127.0.0.1', 0), engine, source)
        thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
        thread.start()
        connection = http.client.HTTPConnection('127.0.0.1', server.server_address[1], timeout=5)
        try:
            connection.request('GET', '/api/tasks/' + task['id'] + '/bundle')
            result = connection.getresponse()
            raw = result.read()
            self.assertEqual(result.status, 200)
            with zipfile.ZipFile(io.BytesIO(raw)) as bundle:
                self.assertIn('source/arithmetic.py', bundle.namelist())
                self.assertIn('GENESIS_RESULT.md', bundle.namelist())
                self.assertFalse(any(any(p.startswith('.genesis-') for p in Path(name).parts) for name in bundle.namelist()))
                self.assertEqual(bundle.read('source/arithmetic.py'), (engine.workspace(task) / 'source/arithmetic.py').read_bytes())
                self.assertEqual(bundle.read('source/arithmetic.py').decode().replace('\r\n', '\n'), FIXED)
                self.assertEqual(bundle.read('artifacts/self-improvement.patch'), patch_bytes)
        finally:
            connection.close()
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == '__main__':
    unittest.main()
