"""Artifact handoff tests: real files and execution; model replies are test doubles."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from genesis.engine import Engine
from genesis.providers import ProviderResult


def reply(text='', calls=None):
    return ProviderResult(text, calls or [], 10, 10, 'openai', 'test-double')


def invocation(name, arguments, identifier):
    return {'name': name, 'arguments': arguments, 'id': identifier}


class HandoffRouterDouble:
    def __init__(self):
        self.script = []

    def generate(self, *args):
        if not self.script:
            raise AssertionError('Unexpected model request in artifact handoff test')
        return self.script.pop(0)


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        self.router = HandoffRouterDouble()
        self.engine = Engine(self.root / 'state', self.source, self.router)
        self.addCleanup(self.engine.close)
        self.venture = self.engine.store.put('ventures', {'name': 'Shared venture'})
        self.engineering = self.engine.create_task('Build candidate', self.venture['id'], role='engineering')
        self.qa = self.engine.create_task('Verify candidate', self.venture['id'], role='qa')

    def artifact(self, task, path, data):
        target = self.engine.workspace(task) / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        self.engine.register_artifacts(task)
        return next(a for a in self.engine.store.all('artifacts') if a['task_id'] == task['id'] and a['path'] == path)

    def test_engineering_artifacts_imported_and_tests_execute_after_approval(self):
        module = 'def total(values):\n    return sum(values)\n'
        check = 'import unittest\nfrom candidate import total\nclass Verify(unittest.TestCase):\n    def test_total(self):\n        self.assertEqual(total([4, 7]), 11)\n'
        self.router.script.extend([
            reply(calls=[invocation('workspace_write', {'path': 'candidate.py', 'content': module}, 'build-module'),
                         invocation('workspace_write', {'path': 'test_candidate.py', 'content': check}, 'build-test')]),
            reply('Candidate created; tests await independent QA.')])
        self.engine.run(self.engineering['id'])
        self.assertEqual(self.engine.store.get('tasks', self.engineering['id'])['status'], 'completed')
        listing = self.engine._core_tool(self.qa, 'artifact_list', {'task_id': self.engineering['id']})['artifacts']
        by_path = {a['path']: a for a in listing}
        self.assertIn('candidate.py', by_path)
        self.assertIn('test_candidate.py', by_path)
        self.router.script.extend([
            reply(calls=[invocation('artifact_import', {'artifact_id': by_path['candidate.py']['id']}, 'import-module'),
                         invocation('artifact_import', {'artifact_id': by_path['test_candidate.py']['id']}, 'import-test'),
                         invocation('run_python_tests', {}, 'qa-execute')]),
            reply('Independent QA executed and verified the imported test.')])
        self.engine.run(self.qa['id'])
        self.assertEqual(self.engine.store.get('tasks', self.qa['id'])['status'], 'waiting_approval')
        self.assertEqual((self.engine.workspace(self.qa) / 'candidate.py').read_text(), module)
        messages = self.engine.store.messages(self.qa['id'])
        self.assertFalse(any(m.get('tool_call_id') == 'qa-execute' for m in messages))
        approval = next(a for a in self.engine.store.all('approvals') if a['task_id'] == self.qa['id'])
        self.assertEqual(approval['action'], 'terminal')
        self.engine.decide(approval['id'], 'approved')
        self.engine.run(self.qa['id'])
        self.assertEqual(self.engine.store.get('tasks', self.qa['id'])['status'], 'completed')
        output = next(m for m in self.engine.store.messages(self.qa['id']) if m.get('tool_call_id') == 'qa-execute')
        result = json.loads(output['content'])
        self.assertEqual(result['returncode'], 0)
        self.assertIn('Ran 1 test', result['output'])
        self.assertIn('OK', result['output'])
        imports = [e for e in self.engine.store.events(self.qa['id']) if e['action'] == 'artifact_imported']
        self.assertEqual(len(imports), 2)

    def test_binary_import_hash_and_metadata_match_actual_bytes(self):
        data = bytes(range(256)) * 8
        artifact = self.artifact(self.engineering, 'nested/payload.bin', data)
        result = self.engine._core_tool(self.qa, 'artifact_import', {'artifact_id': artifact['id'], 'path': 'review/payload.bin'})
        self.assertEqual(result['path'], 'review/payload.bin')
        self.assertEqual(result['bytes'], len(data))
        self.assertEqual(result['sha256'], hashlib.sha256(data).hexdigest())
        self.assertEqual(result['source_task_id'], self.engineering['id'])
        self.assertEqual((self.engine.workspace(self.qa) / result['path']).read_bytes(), data)
        self.assertTrue(any(a['task_id'] == self.qa['id'] and a['path'] == result['path'] for a in self.engine.store.all('artifacts')))
        self.assertTrue(any(e['action'] == 'artifact_imported' for e in self.engine.store.events(self.qa['id'])))

    def test_different_venture_artifacts_hidden_and_import_denied(self):
        foreign_venture = self.engine.store.put('ventures', {'name': 'Private venture'})
        foreign = self.engine.create_task('Private work', foreign_venture['id'], role='engineering')
        secret = self.artifact(foreign, 'private.txt', b'private data')
        visible = self.engine._core_tool(self.qa, 'artifact_list', {})['artifacts']
        self.assertNotIn(secret['id'], {a['id'] for a in visible})
        with self.assertRaises(ValueError):
            self.engine._core_tool(self.qa, 'artifact_import', {'artifact_id': secret['id']})
        self.assertFalse((self.engine.workspace(self.qa) / 'private.txt').exists())

    def test_destination_traversal_cannot_escape_qa_workspace(self):
        artifact = self.artifact(self.engineering, 'safe.txt', b'safe data')
        outside = self.root / 'escaped.txt'
        for path in ('../escaped.txt', str(outside)):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.engine._core_tool(self.qa, 'artifact_import', {'artifact_id': artifact['id'], 'path': path})
        self.assertFalse(outside.exists())
        self.assertFalse((self.engine.workspace(self.qa).parent / 'escaped.txt').exists())

    def test_source_metadata_traversal_cannot_read_outside_workspace(self):
        outside = self.engine.workspace(self.engineering).parent / 'outside.txt'
        outside.write_bytes(b'outside data')
        artifact = self.engine.store.put('artifacts', {'task_id': self.engineering['id'], 'name': 'outside.txt', 'path': '../outside.txt', 'size': 12})
        with self.assertRaises(ValueError):
            self.engine._core_tool(self.qa, 'artifact_import', {'artifact_id': artifact['id'], 'path': 'copied.txt'})
        self.assertFalse((self.engine.workspace(self.qa) / 'copied.txt').exists())

    def test_files_over_100kb_rejected_without_destination(self):
        artifact = self.artifact(self.engineering, 'large.bin', b'x' * 100001)
        with self.assertRaises(ValueError):
            self.engine._core_tool(self.qa, 'artifact_import', {'artifact_id': artifact['id']})
        self.assertFalse((self.engine.workspace(self.qa) / 'large.bin').exists())


if __name__ == '__main__':
    unittest.main()
