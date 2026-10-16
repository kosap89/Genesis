"""Deterministic cancellation at preflight boundaries; no live provider calls."""
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from genesis.engine import Engine
from genesis.providers import ProviderResult
from genesis.toolbox import Toolbox


class CountingRouter:
    def __init__(self): self.calls=0
    def generate(self,*args):
        self.calls+=1
        return ProviderResult('Completed.',[],1,1,'openai','test')


class ShutdownTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.router=CountingRouter()
        self.engine=Engine(Path(self.temp.name)/'state',Path(self.temp.name),self.router)
        self.addCleanup(self.engine.close)
        self.task=self.engine.create_task('Control boundary test')

    def test_cancel_during_model_preflight_prevents_paid_request(self):
        original=self.engine.core_schemas
        def cancel_during_schemas(task):
            result=original(task)
            self.engine.cancel(task['id'])
            return result
        with patch.object(self.engine,'core_schemas',cancel_during_schemas):
            self.engine.run(self.task['id'])
        self.assertEqual(self.router.calls,0)
        self.assertEqual(self.engine.settings()['reserved_usd'],0)
        self.assertFalse(any(e['action']=='model_request' for e in self.engine.store.events()))
        self.assertEqual(self.engine.store.get('tasks',self.task['id'])['status'],'cancelled')

    def test_cancel_during_tool_preflight_prevents_invocation(self):
        self.engine.store.message(self.task['id'],dict(role='assistant',content='',tool_calls=[dict(id='pending',name='workspace_write',arguments=dict(path='forbidden.txt',content='no'))]))
        original=Toolbox.__init__
        def cancel_during_init(box,context):
            original(box,context)
            self.engine.cancel(self.task['id'])
        with patch.object(Toolbox,'__init__',cancel_during_init):
            self.engine.run(self.task['id'])
        self.assertFalse((self.engine.workspace(self.task)/'forbidden.txt').exists())
        self.assertFalse(any(e['action']=='tool_started' for e in self.engine.store.events()))
        self.assertEqual(self.router.calls,0)

    def test_cancelled_parent_cannot_create_new_child(self):
        self.engine.cancel(self.task['id'])
        with self.assertRaisesRegex(ValueError,'no longer running'):
            self.engine._core_tool(self.task,'delegate_task',{'objective':'Unexpected child','role':'qa'})
        self.assertEqual(len(self.engine.store.all('tasks')),1)

    def test_close_reports_worker_liveness_until_inflight_job_finishes(self):
        started=threading.Event()
        release=threading.Event()
        def generate(*args):
            started.set()
            if not release.wait(10): raise AssertionError('Test failed to release its request')
            return ProviderResult('Finished in-flight request.',[],1,1,'openai','test')
        self.router.generate=generate
        self.engine.start()
        self.assertTrue(started.wait(5))
        try:
            self.assertFalse(self.engine.close())
            self.assertTrue(self.engine.thread.is_alive())
        finally:
            release.set()
        self.assertTrue(self.engine.close())
