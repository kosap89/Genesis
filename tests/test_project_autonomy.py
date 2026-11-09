"""Project-scoped tool authorization. Offline fixtures; no paid or public requests."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from genesis.engine import Engine
from genesis.toolbox import Toolbox
from tests.test_engine import ScriptedRouter, response, call
from tests import test_server as server_fixture


class ProjectAutonomyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.router = ScriptedRouter()
        self.engine = Engine(self.root / 'state', self.root, self.router)
        self.addCleanup(self.engine.close)
        self.project = self.engine.store.put('ventures', {'name': 'Autonomous design', 'budget_usd': 5})
        self.other = self.engine.store.put('ventures', {'name': 'Manual project', 'budget_usd': 5})
        self.a = self.engine.teams.create_agent({'template_id': 'engineering', 'name': 'Lead',
            'project_ids': [self.project['id'], self.other['id']]})
        self.b = self.engine.teams.create_agent({'template_id': 'engineering', 'name': 'Designer',
            'project_ids': [self.project['id']]})

    def policy(self, **values):
        return self.engine.teams.update_project(self.project['id'], {'autonomy': values})

    def task(self, project=None, **extra):
        return self.engine.create_task('Bounded offline design', (project or self.project)['id'],
            agent_id=self.a['id'], work_mode='collaborative', **extra)

    def invoke(self, task, name, args, call_id='one'):
        self.engine.store.message(task['id'], {'role': 'assistant', 'content': '',
            'tool_calls': [{'id': call_id, 'name': name, 'arguments': args}]})
        self.engine.store.update('tasks', task['id'], status='running')
        return self.engine._pending_tools(self.engine.store.get('tasks', task['id']))

    def outputs(self, task):
        return [json.loads(m['content']) for m in self.engine.store.messages(task['id']) if m['role'] == 'tool']

    def test_autonomous_delegation_has_real_child_and_policy_audit(self):
        self.policy(delegation=True)
        task = self.task()
        self.assertTrue(self.invoke(task, 'delegate_task', {'objective': 'Design one rule', 'agent_id': self.b['id']}))
        children = [t for t in self.engine.store.all('tasks') if t.get('parent_id') == task['id']]
        self.assertEqual(len(children), 1)
        self.assertEqual(children[0]['agent_id'], self.b['id'])
        self.assertEqual(self.engine.store.all('approvals'), [])
        audit = [e for e in self.engine.store.events(task['id']) if e['action'] == 'tool_policy_authorized']
        self.assertEqual(len(audit), 1)
        self.assertEqual(audit[0]['capability'], 'delegation')
        self.assertEqual(audit[0]['authorization'], 'project_autonomy')
        self.assertFalse(self.engine.settings()['allow_network'])
        self.assertEqual(self.router.requests, [])

    def test_autonomy_does_not_transfer_to_another_project(self):
        self.policy(delegation=True, research=True)
        task = self.task(self.other)
        self.assertFalse(self.invoke(task, 'delegate_task', {'objective': 'Manual child', 'agent_id': 'qa'}))
        self.assertEqual(self.engine.store.get('tasks', task['id'])['status'], 'waiting_approval')
        self.assertEqual(self.engine.store.all('approvals')[0]['status'], 'pending')
        self.assertEqual(len(self.engine.store.all('tasks')), 1)

    def test_default_project_research_still_needs_approval(self):
        task = self.task()
        with patch('genesis.toolbox._fetch_public') as fetch:
            self.assertFalse(self.invoke(task, 'research_fetch_url', {'url': 'https://example.com/rules'}))
        fetch.assert_not_called()
        self.assertEqual(self.engine.store.all('approvals')[0]['action'], 'network')

    def test_public_research_uses_existing_transport_and_records_policy(self):
        self.policy(research=True)
        task = self.task()
        fixture = {'url': 'https://example.com/rules', 'status': 200, 'text': 'OFFLINE RULES FIXTURE'}
        with patch('genesis.toolbox._fetch_public', return_value=fixture) as fetch:
            self.assertTrue(self.invoke(task, 'research_fetch_url', {'url': fixture['url']}))
        fetch.assert_called_once_with(fixture['url'])
        self.assertEqual(self.outputs(task), [fixture])
        self.assertEqual(self.engine.store.all('approvals'), [])
        audit = [e for e in self.engine.store.events(task['id']) if e['action'] == 'tool_policy_authorized']
        self.assertEqual(audit[0]['capability'], 'research')

    def test_explicit_denial_wins_over_later_project_authorization(self):
        task = self.task()
        args = {'url': 'https://example.com/rules'}
        self.assertFalse(self.invoke(task, 'research_fetch_url', args))
        approval = self.engine.store.all('approvals')[0]
        self.engine.decide(approval['id'], 'denied')
        self.policy(research=True)
        self.engine.store.update('tasks', task['id'], status='running')
        with patch('genesis.toolbox._fetch_public') as fetch:
            self.assertTrue(self.engine._pending_tools(self.engine.store.get('tasks', task['id'])))
        fetch.assert_not_called()
        self.assertIn('denied', self.outputs(task)[0]['error'])

    def test_old_pending_request_is_not_left_actionable_after_policy_execution(self):
        task = self.task()
        args = {'url': 'https://example.com/rules'}
        self.assertFalse(self.invoke(task, 'research_fetch_url', args))
        approval = self.engine.store.all('approvals')[0]
        self.policy(research=True)
        self.engine.store.update('tasks', task['id'], status='running')
        fixture = {'url': args['url'], 'status': 200, 'text': 'OFFLINE FIXTURE'}
        with patch('genesis.toolbox._fetch_public', return_value=fixture) as fetch:
            self.assertTrue(self.engine._pending_tools(self.engine.store.get('tasks', task['id'])))
        fetch.assert_called_once()
        self.assertNotEqual(self.engine.store.get('approvals', approval['id'])['status'], 'pending')
        self.assertEqual(self.outputs(task), [fixture])

    def test_autonomous_delegation_cannot_select_unassigned_legacy_agent(self):
        self.policy(delegation=True)
        task = self.task()
        self.invoke(task, 'delegate_task', {'objective': 'Outside team', 'agent_id': 'qa'})
        self.assertFalse(any(t.get('parent_id') == task['id'] for t in self.engine.store.all('tasks')))
        self.assertFalse(any(e['action'] == 'tool_policy_authorized' for e in self.engine.store.events(task['id'])))

    def test_disabled_target_cannot_be_delegated_automatically(self):
        self.policy(delegation=True)
        self.engine.teams.update_membership(self.project['id'], self.b['id'], {'enabled': False})
        task = self.task()
        self.invoke(task, 'delegate_task', {'objective': 'Disabled child', 'agent_id': self.b['id']})
        self.assertFalse(any(t.get('parent_id') == task['id'] for t in self.engine.store.all('tasks')))

    def test_terminal_stays_manual_with_full_project_autonomy(self):
        self.policy(delegation=True, research=True)
        task = self.task()
        with patch('genesis.toolbox.subprocess.Popen') as process:
            self.assertFalse(self.invoke(task, 'terminal', {'command': ['python', '--version']}))
        process.assert_not_called()
        self.assertEqual(self.engine.store.all('approvals')[0]['action'], 'terminal')

    def test_policy_revoked_during_tool_preflight_prevents_fetch(self):
        self.policy(research=True)
        task = self.task()
        original = Toolbox.__init__
        def revoke(box, context):
            original(box, context)
            self.policy(research=False)
        with patch.object(Toolbox, '__init__', revoke), patch('genesis.toolbox._fetch_public') as fetch:
            self.assertFalse(self.invoke(task, 'research_fetch_url', {'url': 'https://example.com/rules'}))
        fetch.assert_not_called()
        self.assertEqual(self.engine.store.all('approvals')[0]['status'], 'pending')

    def test_unknown_prior_invocation_is_never_replayed_by_autonomy(self):
        self.policy(research=True)
        task = self.task()
        self.engine.store.event('tool_started', task['id'], tool='research_fetch_url', tool_call_id='one')
        with patch('genesis.toolbox._fetch_public') as fetch:
            self.assertTrue(self.invoke(task, 'research_fetch_url', {'url': 'https://example.com/rules'}))
        fetch.assert_not_called()
        self.assertIn('unknown outcome', self.outputs(task)[0]['error'])

    def test_autonomy_does_not_bypass_delegation_limit_or_protected_document(self):
        self.policy(delegation=True, research=True)
        self.engine.teams.update_project(self.project['id'], {'execution_limits': {'max_delegated_tasks': 1}})
        task = self.task()
        args = {'objective': 'One child', 'agent_id': self.b['id']}
        self.assertTrue(self.invoke(task, 'delegate_task', args, 'first'))
        self.assertTrue(self.invoke(task, 'delegate_task', args, 'second'))
        self.assertEqual(len([t for t in self.engine.store.all('tasks') if t.get('parent_id') == task['id']]), 1)
        self.assertIn('task count', self.outputs(task)[-1]['error'])
        doc = self.engine.documents.create(self.project['id'], {'name': 'CONCEPT.md', 'content': 'Protected', 'kind': 'reference'})
        self.invoke(task, 'venture_document_update', {'document_name': 'CONCEPT.md', 'content': 'Changed', 'expected_revision': 1}, 'write')
        self.assertEqual(self.engine.documents.get(self.project['id'], doc['id'])['content'], 'Protected')
        self.assertIn('CEO', self.outputs(task)[-1]['error'])

    def test_budget_still_blocks_before_provider_double_dispatch(self):
        self.policy(delegation=True, research=True)
        self.engine.store.update('settings', 'global', budget_usd=0)
        self.router.script.append(response('Must not dispatch'))
        task = self.task()
        self.engine.run(task['id'])
        self.assertEqual(self.engine.store.get('tasks', task['id'])['status'], 'blocked_budget')
        self.assertEqual(self.router.requests, [])
        self.assertEqual(self.engine.settings()['reserved_usd'], 0)

    def test_disabled_budget_enforcement_tracks_all_scopes_and_can_be_reenabled(self):
        self.assertIs(self.engine.settings()['budget_enforcement_enabled'], True)
        self.engine.store.update('settings', 'global', budget_usd=0,
            budget_enforcement_enabled=False, spent_usd=0.15)
        self.engine.store.update('ventures', self.project['id'], budget_usd=0, spent_usd=0.1)
        self.engine.store.update('agents', self.a['id'], budget_usd=0, spent_usd=0.05)
        task = self.task()
        self.assertTrue(self.engine._reserve(task, 0.3))
        self.assertAlmostEqual(self.engine.settings()['reserved_usd'], 0.3)
        self.assertAlmostEqual(self.engine.store.get('ventures', self.project['id'])['reserved_usd'], 0.3)
        self.assertAlmostEqual(self.engine.store.get('agents', self.a['id'])['reserved_usd'], 0.3)
        self.engine._settle(task['id'], 0.3, 0.2)
        self.assertAlmostEqual(self.engine.settings()['spent_usd'], 0.35)
        self.assertAlmostEqual(self.engine.store.get('ventures', self.project['id'])['spent_usd'], 0.3)
        self.assertAlmostEqual(self.engine.store.get('agents', self.a['id'])['spent_usd'], 0.25)
        self.assertEqual(self.engine.settings()['reserved_usd'], 0)
        self.engine.store.update('settings', 'global', budget_enforcement_enabled=True)
        self.assertFalse(self.engine._reserve(task, 0.01))
        self.assertAlmostEqual(self.engine.settings()['spent_usd'], 0.35)

    def test_disabling_budget_enforcement_does_not_grant_tool_permissions(self):
        self.engine.store.update('settings', 'global', budget_enforcement_enabled=False)
        task = self.task()
        with patch('genesis.toolbox._fetch_public') as fetch:
            self.assertFalse(self.invoke(task, 'research_fetch_url', {'url': 'https://example.com/rules'}))
        fetch.assert_not_called()
        self.assertEqual(self.engine.store.all('approvals')[0]['action'], 'network')
        self.assertFalse(self.engine.settings()['allow_terminal'])


class ProjectAutonomyAPITests(unittest.TestCase):
    setUp = server_fixture.ServerTests.setUp
    stop_server = server_fixture.ServerTests.stop_server
    request = server_fixture.ServerTests.request
    post = server_fixture.ServerTests.post

    def test_scoped_configuration_validation_merge_and_no_dispatch(self):
        project = self.post('/api/ventures', {'name': 'Autonomous API project'}, 201)
        path = '/api/projects/' + project['id']
        for value in [True, None, {'terminal': True}, {'delegation': 1}, {'research': 'true'}]:
            with self.subTest(value=value):
                self.post(path, {'autonomy': value}, 400)
        self.post(path, {'autonomy': {'delegation': True}})
        result = self.post(path, {'autonomy': {'research': True}})
        self.assertEqual(result['autonomy'], {'delegation': True, 'research': True})
        result = self.post(path, {'autonomy': {'delegation': False}})
        self.assertEqual(result['autonomy'], {'delegation': False, 'research': True})
        self.assertEqual(self.engine.store.all('tasks'), [])
        self.assertFalse(self.engine.settings()['allow_network'])
        self.assertFalse(self.engine.settings()['allow_terminal'])

    def test_budget_enforcement_flag_requires_boolean_and_preserves_accounting(self):
        before = self.engine.settings()
        for value in [None, 0, 1, 'false', [], {}]:
            with self.subTest(value=value):
                self.post('/api/settings', {'budget_enforcement_enabled': value}, 400)
        off = self.post('/api/settings', {'budget_enforcement_enabled': False})
        self.assertIs(off['budget_enforcement_enabled'], False)
        for field in ['spent_usd', 'reserved_usd', 'budget_usd', 'allow_network', 'allow_terminal']:
            self.assertEqual(off[field], before[field])
        on = self.post('/api/settings', {'budget_enforcement_enabled': True})
        self.assertIs(on['budget_enforcement_enabled'], True)
        self.assertEqual(self.engine.store.all('tasks'), [])


if __name__ == '__main__':
    unittest.main()
