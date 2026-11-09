"""Dynamic team execution contracts. Provider doubles are explicitly offline only."""
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from genesis.engine import Engine
from genesis.providers import ProviderResult
from tests.test_engine import ScriptedRouter, response, call


class TeamRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.router = ScriptedRouter()
        self.engine = Engine(self.root / 'state', self.root, self.router)
        self.addCleanup(self.engine.close)
        self.project = self.engine.store.put('ventures', {'name': 'Runtime project', 'budget_usd': 5})
        self.a = self.engine.teams.create_agent({'template_id': 'engineering', 'name': 'Backend',
            'system_instructions': 'Inspect backend delivery.', 'project_ids': [self.project['id']]})
        self.b = self.engine.teams.create_agent({'template_id': 'engineering', 'name': 'Reviewer',
            'system_instructions': 'Independently inspect delivery.', 'project_ids': [self.project['id']]})

    def task(self, agent=None, **options):
        return self.engine.create_task('Bounded offline work', self.project['id'],
            agent_id=(agent or self.a)['id'], **options)

    def current(self, task):
        return self.engine.store.get('tasks', task['id'])

    def test_prompt_exposes_pinned_responsibilities_roster_and_explicit_handoffs(self):
        self.engine.store.update('agents', self.a['id'], specialization='Backend APIs')
        self.engine.store.update('team_memberships', self.project['id'] + ':' + self.a['id'], responsibilities='Verify request validation')
        producer = self.task()
        (self.engine.workspace(producer) / 'api.py').write_text('def validate(): pass')
        self.engine.register_artifacts(producer)
        self.engine.store.update('tasks', producer['id'], status='completed', result='Produced API source with validation.')
        review = self.task(self.b, work_mode='collaborative', review_of=[producer['id']])
        prompt = self.engine.system_prompt(review)
        self.assertIn(self.a['id'], prompt)
        self.assertIn('Backend APIs', prompt)
        self.assertIn('Verify request validation', prompt)
        self.assertIn('Produced API source with validation.', prompt)
        artifact = self.engine.store.all('artifacts')[0]
        self.assertIn(artifact['id'], prompt)
        task = self.task()
        self.engine.store.update('team_memberships', self.project['id'] + ':' + self.a['id'], responsibilities='Later unapproved responsibilities')
        prompt = self.engine.system_prompt(task)
        self.assertIn('Verify request validation', prompt)
        self.assertNotIn('Later unapproved responsibilities', prompt)

    def test_identical_roles_keep_distinct_identity_and_pinned_complete_configuration(self):
        self.engine.store.update('agents', self.a['id'], fallbacks=[{'provider': 'anthropic'}])
        first = self.task()
        second = self.task(self.b)
        self.assertEqual(first['role'], second['role'])
        self.assertNotEqual(first['agent_id'], second['agent_id'])
        self.engine.store.update('agents', self.a['id'], model='gpt-6.1-terra', reasoning_effort='high',
            fallbacks=[], system_instructions='New instructions', input_cost_per_million=100)
        self.router.script.append(response('Original configuration used.'))
        self.engine.run(first['id'])
        request = self.router.requests[0]
        self.assertEqual(request['config']['model'], first['model'])
        self.assertEqual(request['config']['fallbacks'], first['config_snapshot']['fallbacks'])
        self.assertEqual(request['config']['input_cost_per_million'], first['config_snapshot']['input_cost_per_million'])
        self.assertIn('Inspect backend delivery.', request['messages'][0]['content'])
        self.assertNotIn('New instructions', request['messages'][0]['content'])
        self.assertEqual(self.current(second)['status'], 'queued')

    def test_project_isolation_and_membership_disable_prevent_dispatch(self):
        other = self.engine.store.put('ventures', {'name': 'Other'})
        with self.assertRaises(ValueError):
            self.engine.create_task('Cross-project', other['id'], agent_id=self.a['id'])
        task = self.task()
        membership = self.engine.store.get('team_memberships', self.project['id'] + ':' + self.a['id'])
        self.engine.store.update('team_memberships', membership['id'], enabled=False)
        self.engine.run(task['id'])
        self.assertEqual(self.current(task)['status'], 'blocked_agent')
        self.assertEqual(self.router.requests, [])

    def test_independent_task_works_without_coordinator_and_cannot_delegate(self):
        task = self.task()
        self.assertNotIn('delegate_task', {tool['name'] for tool in self.engine.core_schemas(task)})
        self.engine.store.update('tasks', task['id'], status='running')
        with self.assertRaisesRegex(ValueError, 'Independent'):
            self.engine._core_tool(task, 'delegate_task', {'objective': 'No child', 'agent_id': self.b['id']})
        self.assertEqual(len(self.engine.store.all('tasks')), 1)

    def test_specific_instance_delegation_waits_for_individual_approval(self):
        self.router.script.extend([response(calls=[call('delegate_task', {
            'objective': 'Review a separate component', 'agent_id': self.b['id']})]),
            response('Child reviewed.'), response('Integrated review.')])
        task = self.task(work_mode='collaborative')
        self.engine.run(task['id'])
        approval = self.engine.store.all('approvals')[0]
        self.assertEqual(approval['action'], 'delegation')
        self.assertEqual(approval['details']['agent_configuration']['id'], self.b['id'])
        self.assertEqual(len(self.engine.store.all('tasks')), 1)
        self.assertEqual(len(self.router.requests), 1)
        self.engine.decide(approval['id'], 'approved')
        self.engine.run(task['id'])
        child = next(t for t in self.engine.store.all('tasks') if t.get('parent_id') == task['id'])
        self.assertEqual(child['agent_id'], self.b['id'])
        self.assertFalse(child['astra_authorized'])
        self.engine.run(child['id'])
        self.engine.tick()
        self.assertEqual(self.current(task)['status'], 'completed')
        self.assertIn(self.b['id'], self.router.requests[-1]['messages'][-1]['content'])

    def test_delegation_configuration_change_invalidates_approval(self):
        self.router.script.append(response(calls=[call('delegate_task', {'objective': 'Review', 'agent_id': self.b['id']})]))
        task = self.task(work_mode='collaborative')
        self.engine.run(task['id'])
        approval = self.engine.store.all('approvals')[0]
        self.engine.decide(approval['id'], 'approved')
        self.engine.store.update('agents', self.b['id'], model='gpt-6.1-sol', reasoning_effort='high')
        self.engine.run(task['id'])
        self.assertEqual(self.current(task)['status'], 'waiting_approval')
        self.assertEqual(self.engine.store.get('approvals', approval['id'])['status'], 'expired')
        self.assertEqual(len(self.engine.store.all('tasks')), 1)
        self.assertEqual(len(self.router.requests), 1)

    def test_delegation_limits_are_root_wide_and_configurable(self):
        task = self.task(work_mode='collaborative')
        self.engine.store.update('tasks', task['id'], status='running')
        self.engine.store.update('settings', 'global', max_delegated_tasks=1, max_delegation_depth=2)
        child = self.engine._core_tool(task, 'delegate_task', {'objective': 'Child', 'agent_id': self.b['id'], 'work_mode':'collaborative'}, delegation_authorized=True)
        child = self.engine.store.get('tasks', child['task_id'])
        self.engine.store.update('tasks', child['id'], status='running')
        with self.assertRaisesRegex(ValueError, 'task count'):
            self.engine._core_tool(child, 'delegate_task', {'objective': 'Recursive', 'agent_id': self.a['id']}, delegation_authorized=True)
        self.engine.store.update('settings', 'global', max_delegated_tasks=3, max_delegation_depth=1)
        with self.assertRaisesRegex(ValueError, 'depth'):
            self.engine._core_tool(child, 'delegate_task', {'objective': 'Recursive', 'agent_id': self.a['id']}, delegation_authorized=True)

    def test_delegated_dependency_and_review_ancestor_cycles_are_rejected(self):
        parent = self.task(work_mode='collaborative')
        transitively_waiting = self.task(self.b, depends_on=[parent['id']])
        self.engine.store.update('tasks', parent['id'], status='running')
        for references in ({'depends_on':[parent['id']]}, {'review_of':[parent['id']]}, {'depends_on':[transitively_waiting['id']]}):
            with self.subTest(references=references), self.assertRaisesRegex(ValueError, 'ancestor'):
                self.engine._core_tool(parent, 'delegate_task', dict(objective='Deadlock', agent_id=self.b['id'], **references), delegation_authorized=True)
        self.assertEqual(len(self.engine.store.all('tasks')), 2)

    def test_report_and_snapshot_mutations_also_honor_project_file_claims(self):
        owner = self.task(work_mode='collaborative', file_claims=['artifacts/report.md', 'source'])
        blocked = self.task(self.b, work_mode='collaborative')
        self.router.script.extend([response(calls=[
            call('artifact_report', {'name':'report.md', 'content':'Conflict'}, 'report'),
            call('self_improvement_snapshot', {}, 'snapshot')]), response('Conflicts reported.')])
        self.engine.run(blocked['id'])
        outputs = [json.loads(m['content']) for m in self.engine.store.messages(blocked['id']) if m['role'] == 'tool']
        self.assertEqual(len(outputs), 2)
        self.assertTrue(all('File conflict' in output['error'] for output in outputs))
        self.assertFalse((self.engine.workspace(blocked) / 'artifacts/report.md').exists())
        self.assertFalse((self.engine.workspace(blocked) / 'source').exists())

    def test_disabling_membership_before_tool_claim_stops_execution(self):
        task = self.task()
        def disable_before_tools(*args):
            self.engine.store.update('team_memberships', self.project['id'] + ':' + self.a['id'], enabled=False)
            return response(calls=[call('workspace_write', {'path':'forbidden.txt', 'content':'No'})])
        self.router.script.append(disable_before_tools)
        self.engine.run(task['id'])
        self.assertEqual(self.current(task)['status'], 'blocked_agent')
        self.assertFalse((self.engine.workspace(task) / 'forbidden.txt').exists())
        self.assertFalse(any(event['action'] == 'tool_started' for event in self.engine.store.events(task['id'])))

    def test_dependencies_and_independent_review_enforce_agent_and_project(self):
        build = self.task()
        review = self.task(self.b, review_of=[build['id']])
        with self.assertRaisesRegex(ValueError, 'different agent'):
            self.task(review_of=[build['id']])
        self.engine.run(review['id'])
        self.assertEqual(self.router.requests, [])
        self.router.script.extend([response('Build complete.'), response('Independent review complete.')])
        self.engine.run(build['id'])
        self.engine.run(review['id'])
        self.assertEqual(self.current(review)['status'], 'completed')
        failure = self.task()
        dependent = self.task(self.b, depends_on=[failure['id']])
        self.engine.cancel(failure['id'])
        self.engine.run(dependent['id'])
        self.assertEqual(self.current(dependent)['status'], 'blocked_dependencies')

    def test_review_cannot_be_rerouted_to_current_or_previous_author(self):
        author = self.task()
        review = self.task(self.b, review_of=[author['id']])
        self.engine.store.update('tasks', review['id'], status='interrupted')
        with self.assertRaisesRegex(ValueError, 'different agent'):
            self.engine.resume(review['id'], agent_id=self.a['id'])
        self.engine.store.update('tasks', author['id'], status='interrupted')
        self.engine.resume(author['id'], agent_id=self.b['id'])
        with self.assertRaisesRegex(ValueError, 'different agent'):
            self.task(self.a, review_of=[author['id']])
        self.assertEqual(set(self.current(author)['agent_history']), {self.a['id'], self.b['id']})

    def test_claims_detect_related_case_insensitive_paths_and_release_on_completion(self):
        first = self.task(work_mode='collaborative', file_claims=['src/backend'])
        with self.assertRaisesRegex(ValueError, 'File conflict'):
            self.task(self.b, work_mode='collaborative', file_claims=['SRC/backend/app.py'])
        independent = self.task(self.b, file_claims=['src/backend/app.py'])
        self.assertEqual(independent['work_mode'], 'independent')
        self.engine.store.update('tasks', first['id'], status='completed')
        later = self.task(self.b, work_mode='collaborative', file_claims=['src/backend/app.py'])
        self.assertEqual(later['file_claims'], ['src/backend/app.py'])

    def test_actual_write_and_import_cannot_bypass_declared_claims(self):
        owner = self.task(work_mode='collaborative', file_claims=['shared.py'])
        blocked = self.task(self.b, work_mode='collaborative')
        self.router.script.extend([response(calls=[call('workspace_write', {'path': 'shared.py', 'content': 'blocked'})]), response('Conflict reported.')])
        self.engine.run(blocked['id'])
        self.assertFalse((self.engine.workspace(blocked) / 'shared.py').exists())
        output = next(m for m in self.engine.store.messages(blocked['id']) if m['role'] == 'tool')
        self.assertIn('File conflict', output['content'])
        independent = self.task(self.b)
        (self.engine.workspace(independent) / 'source.py').write_text('original')
        self.engine.register_artifacts(independent)
        artifact = next(a for a in self.engine.store.all('artifacts') if a['task_id'] == independent['id'])
        another = self.task(self.b, work_mode='collaborative')
        with self.assertRaisesRegex(ValueError, 'File conflict'):
            self.engine._core_tool(another, 'artifact_import', {'artifact_id': artifact['id'], 'path': 'shared.py'})
        self.assertFalse((self.engine.workspace(another) / 'shared.py').exists())

    def test_memory_and_artifact_contributions_identify_agent_instances(self):
        first, second = self.task(), self.task(self.b)
        for task in (first, second):
            saved = self.engine._core_tool(task, 'memory_save', {'title': 'Evidence', 'content': 'Bounded result'})
            self.assertEqual(saved['agent_id'], task['agent_id'])
            (self.engine.workspace(task) / 'contribution.txt').write_text(task['agent_id'])
            self.engine.register_artifacts(task)
        artifacts = self.engine.store.all('artifacts')
        self.assertEqual({artifact['agent_id'] for artifact in artifacts}, {self.a['id'], self.b['id']})
        self.assertIn(self.a['id'], self.engine.system_prompt(second))

    def test_optional_agent_and_project_budget_each_block_without_global_charge(self):
        for kind, key in (('agents', self.a['id']), ('ventures', self.project['id'])):
            with self.subTest(kind=kind):
                self.engine.store.update(kind, key, budget_usd=0)
                task = self.task()
                self.engine.run(task['id'])
                self.assertEqual(self.current(task)['status'], 'blocked_budget')
                self.assertEqual(self.engine.settings()['spent_usd'], 0)
                self.assertEqual(self.engine.settings()['reserved_usd'], 0)
                self.engine.store.update(kind, key, budget_usd=None)
        self.assertEqual(self.router.requests, [])

    def test_scoped_unknown_failure_and_restart_charge_full_reservation_once(self):
        self.router.script.append(RuntimeError('Offline unknown outcome'))
        failed = self.task()
        self.engine.run(failed['id'])
        charge = self.current(failed)['cost_usd']
        self.assertGreater(charge, 0)
        for kind, key in (('settings','global'), ('agents',self.a['id']), ('ventures',self.project['id'])):
            self.assertAlmostEqual(self.engine.store.get(kind,key)['spent_usd'], charge)
            self.assertEqual(self.engine.store.get(kind,key)['reserved_usd'], 0)
        task = self.task()
        self.engine.store.update('tasks', task['id'], status='running')
        self.assertTrue(self.engine._reserve(task, 0.2))
        for _ in range(2):
            restarted = Engine(self.root / 'state', self.root, self.router)
            self.addCleanup(restarted.close)
            for kind, key in (('settings','global'), ('agents',self.a['id']), ('ventures',self.project['id'])):
                self.assertAlmostEqual(restarted.store.get(kind,key)['spent_usd'], charge + 0.2)
                self.assertEqual(restarted.store.get(kind,key)['reserved_usd'], 0)
            self.assertAlmostEqual(restarted.store.get('tasks',task['id'])['cost_usd'], 0.2)

    def test_explicit_resume_to_another_instance_changes_snapshot_only_on_request(self):
        first = self.task()
        self.engine.store.update('tasks', first['id'], status='interrupted')
        self.engine.store.update('agents', self.b['id'], model='gpt-6-luna', reasoning_effort='low')
        self.engine.resume(first['id'], agent_id=self.b['id'])
        updated = self.current(first)
        self.assertEqual(updated['agent_id'], self.b['id'])
        self.assertEqual(updated['model'], 'gpt-6-luna')
        self.assertEqual(updated['config_snapshot']['system_instructions'], 'Independently inspect delivery.')

    def test_concurrent_reservations_do_not_overdraw_global_or_scoped_budgets(self):
        started, release = threading.Event(), threading.Event()
        def generate(*args):
            started.set()
            if not release.wait(10):
                raise AssertionError('Offline test failed to release provider double')
            return response('Settled first request.')
        self.router.generate = generate
        first, second = self.task(), self.task(self.b)
        self.engine.store.update('settings','global',max_concurrency=2)
        worker = threading.Thread(target=self.engine.run, args=(first['id'],))
        worker.start()
        try:
            self.assertTrue(started.wait(5))
            reserve = self.engine.settings()['reserved_usd']
            self.engine.store.update('ventures',self.project['id'],budget_usd=reserve * 1.1)
            self.engine.run(second['id'])
            self.assertEqual(self.current(second)['status'],'blocked_budget')
            self.assertAlmostEqual(self.engine.settings()['reserved_usd'],reserve)
        finally:
            release.set()
            worker.join(10)
        self.assertFalse(worker.is_alive())
        self.assertEqual(self.engine.settings()['reserved_usd'],0)
        self.assertEqual(self.engine.store.get('ventures',self.project['id'])['reserved_usd'],0)

    def test_default_single_request_and_configurable_parallel_scheduler(self):
        for limit in (1, 2):
            with self.subTest(limit=limit):
                started, parallel, release = threading.Event(), threading.Event(), threading.Event()
                lock = threading.Lock()
                calls = []
                def generate(*args):
                    with lock:
                        calls.append(1)
                        started.set()
                        if len(calls) == 2:
                            parallel.set()
                    if not release.wait(10):
                        raise AssertionError('Offline test failed to release provider double')
                    return response('Scheduler fixture complete.')
                engine = Engine(self.root / ('parallel-' + str(limit)), self.root, ScriptedRouter())
                self.addCleanup(engine.close)
                engine.router.generate = generate
                if limit == 2:
                    engine.store.update('settings','global',max_concurrency=2)
                engine.create_task('First fixture')
                engine.create_task('Second fixture')
                engine.start()
                try:
                    self.assertTrue(started.wait(5))
                    self.assertEqual(parallel.wait(0.5 if limit == 1 else 5),limit == 2)
                finally:
                    release.set()
                    engine.close()
                self.assertFalse(engine.thread.is_alive())


if __name__ == '__main__':
    unittest.main()
