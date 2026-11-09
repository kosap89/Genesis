"""Project controls verified offline; provider doubles never reach a paid API."""
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from genesis.engine import Engine
from tests.test_engine import ScriptedRouter, response, call


class ProjectExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.router = ScriptedRouter()
        self.engine = Engine(self.root / 'state', self.root, self.router)
        self.addCleanup(self.engine.close)
        self.project = self.engine.store.put('ventures', {'name': 'Prepared project', 'budget_usd': 5,
            'spent_usd': .2, 'reserved_usd': 0})
        self.agent = self.engine.teams.create_agent({'template_id': 'coo', 'name': 'Lead',
            'project_ids': [self.project['id']]})

    def task(self, **kwargs):
        return self.engine.create_task('Offline task', self.project['id'], agent_id=self.agent['id'], **kwargs)

    def limits(self, **kwargs):
        return self.engine.teams.update_project(self.project['id'], {'execution_limits': kwargs})

    def test_draft_is_metadata_only_and_validates_before_atomic_save(self):
        draft = {'objective': ' Design rules ', 'agent_id': self.agent['id'], 'work_mode': 'collaborative'}
        result = self.engine.teams.update_project(self.project['id'], {'mission_draft': draft,
            'execution_limits': {'max_concurrency': 3, 'max_steps': 24}})
        self.assertEqual(result['mission_draft']['objective'], 'Design rules')
        self.assertEqual(self.engine.store.all('tasks'), [])
        self.assertEqual(self.router.requests, [])
        self.assertEqual(result['spent_usd'], .2)
        before = self.engine.store.get('ventures', self.project['id'])
        for body in ({'execution_limits': {'max_steps': True}}, {'execution_limits': {'allow_network': True}},
                     {'execution_limits': {'max_output_tokens': 32769}}, {'execution_limits': None},
                     {'spent_usd': 0}, {'mission_draft': {**draft, 'api_key': 'not-allowed'}},
                     {'mission_draft': {**draft, 'agent_id': 'engineering'}},
                     {'mission_draft': {**draft, 'work_mode': 'wrong'}}):
            with self.subTest(body=body), self.assertRaises(ValueError):
                self.engine.teams.update_project(self.project['id'], body)
            self.assertEqual(before, self.engine.store.get('ventures', self.project['id']))
        self.engine.teams.update_project(self.project['id'], {'mission_draft': None, 'execution_limits': {}})
        self.assertEqual(self.engine.execution_settings(self.project['id'])['max_steps'], 16)

    def test_project_values_live_apply_to_estimates_and_actual_requests(self):
        self.limits(max_steps=2, max_output_tokens=512, max_concurrency=3)
        preview = self.engine.estimate_task('Offline task', self.project['id'], agent_id=self.agent['id'])
        self.assertEqual(preview['max_steps'], 2)
        self.assertEqual(preview['max_output_tokens'], 512)
        self.assertEqual(preview['max_concurrency'], 1)
        task = self.task()
        self.limits(max_steps=1, max_output_tokens=256)
        self.router.script.append(response(calls=[call('memory_write', {'content': 'offline note'})]))
        self.engine.run(task['id'])
        self.assertEqual(self.router.requests[0]['config']['max_output_tokens'], 256)
        self.assertEqual(self.engine.store.get('tasks', task['id'])['status'], 'paused_limit')
        self.assertEqual(self.engine.settings()['max_output_tokens'], 4096)
        with self.assertRaises(ValueError):
            self.engine.estimate_task('Offline task', self.project['id'], agent_id=self.agent['id'], work_mode='wrong')

    def test_reduction_during_preflight_is_honored_before_reservation(self):
        self.limits(max_output_tokens=1000)
        original = self.engine.core_schemas
        def reduce(task):
            self.limits(max_output_tokens=100)
            return original(task)
        self.router.script.append(response('Done.'))
        task = self.task()
        with patch.object(self.engine, 'core_schemas', reduce):
            self.engine.run(task['id'])
        self.assertEqual(self.router.requests[0]['config']['max_output_tokens'], 100)

    def test_project_root_delegation_limits_override_global(self):
        self.engine.store.update('settings', 'global', max_delegation_depth=0, max_delegated_tasks=1)
        self.limits(max_delegation_depth=1, max_delegated_tasks=2)
        parent = self.task(work_mode='collaborative')
        self.engine.store.update('tasks', parent['id'], status='running')
        for _ in range(2):
            child = self.engine.create_task('Approved offline child', self.project['id'], agent_id=self.agent['id'],
                parent_id=parent['id'], delegation_authorized=True, work_mode='collaborative')
        with self.assertRaisesRegex(ValueError, 'count'):
            self.engine.create_task('Third child', self.project['id'], agent_id=self.agent['id'],
                parent_id=parent['id'], delegation_authorized=True)
        self.engine.store.update('tasks', child['id'], status='running')
        with self.assertRaisesRegex(ValueError, 'depth'):
            self.engine.create_task('Too deep', self.project['id'], agent_id=self.agent['id'],
                parent_id=child['id'], delegation_authorized=True)

    def test_direct_run_enforces_project_three_and_global_capacity(self):
        self.engine.store.update('settings', 'global', max_concurrency=3)
        self.limits(max_concurrency=3)
        tasks = [self.task() for _ in range(4)]
        condition = threading.Condition()
        release = threading.Event()
        started = []
        def generate(*args):
            with condition:
                started.append(1)
                condition.notify_all()
            self.assertTrue(release.wait(5))
            return response('Done.')
        self.router.generate = generate
        workers = [threading.Thread(target=self.engine.run, args=(t['id'],)) for t in tasks[:3]]
        for worker in workers: worker.start()
        try:
            with condition:
                self.assertTrue(condition.wait_for(lambda: len(started) == 3, timeout=5))
            self.engine.run(tasks[3]['id'])
            self.assertEqual(len(started), 3)
            self.assertEqual(self.engine.store.get('tasks', tasks[3]['id'])['status'], 'queued')
        finally:
            release.set()
            for worker in workers: worker.join(5)
        self.assertEqual(len(self.engine.active_requests), 0)

    def test_scheduler_skips_capped_project_and_dispatches_other_project(self):
        self.engine.store.update('settings', 'global', max_concurrency=3)
        self.limits(max_concurrency=1)
        tasks = [self.task() for _ in range(3)]
        other = self.engine.store.put('ventures', {'name': 'Other project', 'budget_usd': 5})
        last = self.engine.create_task('Other offline task', other['id'])
        release = threading.Event()
        condition = threading.Condition()
        started = []
        def generate(messages, tools, config):
            with condition:
                started.append(messages[-1]['content'])
                condition.notify_all()
            self.assertTrue(release.wait(5))
            return response('Done.')
        self.router.generate = generate
        self.engine.start()
        try:
            with condition:
                self.assertTrue(condition.wait_for(lambda: len(started) >= 2, timeout=5))
            self.assertEqual(len(started), 2)
            self.assertIn('Other offline task', started)
            self.assertEqual(sum(self.engine.store.get('tasks', t['id'])['status'] == 'running' for t in tasks), 1)
        finally:
            self.engine.stop_event.set()
            release.set()
            self.engine.close()


if __name__ == '__main__':
    unittest.main()
