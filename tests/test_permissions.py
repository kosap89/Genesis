"""Approval integrity: a decision applies to the exact workspace reviewed."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from genesis.engine import Engine
from genesis.providers import ProviderResult


class Router:
    def generate(self, messages, tools, config):
        if any(m['role']=='tool' for m in messages):
            return ProviderResult('Verified.',[],10,10,'openai','test')
        return ProviderResult('',[{'id':'run','name':'terminal','arguments':{'command':['python','-c','print(42)']}}],10,10,'openai','test')


class PermissionTests(unittest.TestCase):
    def test_modified_candidate_invalidates_execution_approval(self):
        with tempfile.TemporaryDirectory() as folder:
            engine=Engine(Path(folder)/'state',Path(folder),Router())
            task=engine.create_task('Test invocation integrity')
            file=engine.workspace(task)/'candidate.py'
            file.write_text('print(1)',encoding='utf-8')
            engine.run(task['id'])
            approval=engine.store.all('approvals')[0]
            self.assertEqual(approval['details']['workspace_files'],1)
            engine.decide(approval['id'],'approved')
            file.write_text('print(2)',encoding='utf-8')
            with patch('genesis.toolbox.subprocess.Popen',side_effect=AssertionError('Unreviewed candidate executed')):
                engine.run(task['id'])
            self.assertEqual(engine.store.get('tasks',task['id'])['status'],'waiting_approval')
            self.assertEqual(engine.store.get('approvals',approval['id'])['status'],'expired')
            pending=[a for a in engine.store.all('approvals') if a['status']=='pending']
            self.assertEqual(len(pending),1)
            self.assertNotEqual(pending[0]['details']['workspace_digest'],approval['details']['workspace_digest'])
            engine.decide(pending[0]['id'],'approved')
            engine.run(task['id'])
            self.assertEqual(engine.store.get('tasks',task['id'])['status'],'completed')
            result=[m for m in engine.store.messages(task['id']) if m['role']=='tool'][0]
            self.assertIn('42',json.loads(result['content'])['output'])
            engine.close()
