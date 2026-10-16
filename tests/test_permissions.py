"""Approval integrity: a decision applies to the exact workspace reviewed."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from genesis.engine import Engine
from genesis.providers import ProviderResult
from genesis.toolbox import PermissionRequired


class Router:
    def generate(self, messages, tools, config):
        if any(m['role']=='tool' for m in messages):
            return ProviderResult('Verified.',[],10,10,'openai','test')
        return ProviderResult('',[{'id':'run','name':'terminal','arguments':{'command':['python','-c','print(42)']}}],10,10,'openai','test')


class PermissionTests(unittest.TestCase):
    def test_cancel_while_tool_requests_permission_leaves_no_pending_approval(self):
        with tempfile.TemporaryDirectory() as folder:
            engine=Engine(Path(folder)/'state',Path(folder),Router())
            task=engine.create_task('Cancellation during permission request')
            def cancel_then_request(*args):
                engine.cancel(task['id'])
                raise PermissionRequired('terminal','Execution needs approval')
            with patch('genesis.engine.Toolbox.execute',side_effect=cancel_then_request):
                engine.run(task['id'])
            self.assertEqual(engine.store.get('tasks',task['id'])['status'],'cancelled')
            self.assertEqual(engine.store.all('approvals'),[])
            engine.close()

    def test_legacy_crash_between_approval_and_status_or_event_is_recoverable(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            engine=Engine(root/'state',root,Router())
            task=engine.create_task('Recover legacy partial approval')
            invocation={'id':'pending','name':'terminal','arguments':{'command':['python','-c','print(42)']}}
            engine.store.message(task['id'],{'role':'assistant','content':'','tool_calls':[invocation]})
            engine.store.update('tasks',task['id'],status='running')
            engine.store.event('tool_started',task['id'],tool='terminal',tool_call_id='pending')
            approval=engine.store.put('approvals',{'task_id':task['id'],'tool_call_id':'pending','action':'terminal','status':'pending','details':{'workspace_digest':engine.workspace_fingerprint(task)['digest']}})
            restarted=Engine(root/'state',root,Router())
            self.assertEqual(restarted.store.get('tasks',task['id'])['status'],'waiting_approval')
            restarted.decide(approval['id'],'approved')
            restarted.run(task['id'])
            result=next(m for m in restarted.store.messages(task['id']) if m['role']=='tool')
            self.assertIn('42',json.loads(result['content'])['output'])
            self.assertFalse(any(e['action']=='tool_outcome_unknown' for e in restarted.store.events(task['id'])))
            engine.close()
            restarted.close()

    def test_lifecycle_batch_rolls_back_all_records_on_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            engine=Engine(Path(folder)/'state',Path(folder),Router())
            with self.assertRaises(TypeError):
                engine.store.batch([('example',{'id':'first','value':1}),('example',{'id':'second','bad':object()})])
            self.assertIsNone(engine.store.get('example','first'))
            self.assertIsNone(engine.store.get('example','second'))
            engine.close()

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
