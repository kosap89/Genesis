"""Loopback dynamic-team integration; no worker or provider transport."""
import unittest
import test_server


class TeamApiTests(unittest.TestCase):
    setUp = test_server.ServerTests.setUp
    stop_server = test_server.ServerTests.stop_server
    request = test_server.ServerTests.request
    post = test_server.ServerTests.post

    def project(self, name):
        return self.post('/api/ventures', {'name': name, 'budget_usd': 2}, 201)

    def agent(self, project, name='Backend'):
        return self.post('/api/agents', {'template_id': 'engineering', 'name': name,
            'project_ids': [project['id']], 'budget_usd': 1}, 201)

    def test_instances_project_overrides_snapshots_and_history(self):
        a, b = self.project('A'), self.project('B')
        first = self.agent(a)
        second = self.post('/api/agents/' + first['id'] + '/duplicate',
            {'name': 'Frontend', 'project_ids': [a['id']]}, 201)
        self.assertNotEqual(first['id'], second['id'])
        self.assertEqual(first['role'], second['role'])
        member = '/api/projects/' + a['id'] + '/team/' + second['id']
        self.post(member, {'responsibilities': 'Build UI', 'overrides': {'model': 'gpt-6.1-sol', 'reasoning_effort': 'high'}})
        task = self.post('/api/tasks', {'objective': 'Build the frontend', 'venture_id': a['id'],
            'agent_id': second['id']}, 201)
        self.assertEqual(task['agent_id'], second['id'])
        self.assertEqual(task['model'], 'gpt-6.1-sol')
        self.assertEqual(task['reasoning_effort'], 'high')
        self.post('/api/agents/' + second['id'], {'name': 'Renamed', 'model': 'gpt-6-luna', 'reasoning_effort': 'low'})
        self.assertEqual(self.engine.store.get('tasks', task['id'])['model'], 'gpt-6.1-sol')
        self.post(member, {'action': 'remove'})
        self.post('/api/tasks', {'objective': 'Cannot use removed agent', 'venture_id': a['id'], 'agent_id': second['id']}, 400)
        self.post('/api/tasks', {'objective': 'Cannot cross projects', 'venture_id': b['id'], 'agent_id': first['id']}, 400)
        self.assertIsNotNone(self.engine.store.get('tasks', task['id']))
        self.post('/api/projects/' + b['id'] + '/team', {'agent_id': second['id']})
        estimate = self.post('/api/tasks/estimate', {'objective': 'Preview only', 'venture_id': b['id'], 'agent_id': second['id']})
        self.assertEqual(len(self.engine.store.all('tasks')), 1)
        self.assertIsInstance(estimate, dict)

    def test_custom_template_and_configuration_create_no_work(self):
        project = self.project('One engineer')
        template = self.post('/api/role-templates', {'name': 'Accessibility reviewer',
            'system_instructions': 'Review accessibility evidence.', 'model': 'gpt-6.1-terra',
            'provider': 'openai', 'reasoning_effort': 'medium'}, 201)
        agent = self.post('/api/agents', {'template_id': template['id'], 'name': 'Reviewer',
            'project_ids': [project['id']]}, 201)
        self.post('/api/role-templates/' + template['id'], {'name': 'Updated template'})
        self.assertEqual(self.engine.store.get('agents', agent['id'])['name'], 'Reviewer')
        self.post('/api/projects/' + project['id'], {'budget_usd': .5})
        settings = self.post('/api/settings', {'max_concurrency': 3, 'max_delegation_depth': 0, 'max_delegated_tasks': 4})
        self.assertEqual(settings['max_concurrency'], 3)
        state = self.request('GET', '/api/state')[1]
        self.assertEqual(len(state['agents']), 8)
        self.assertEqual(len(state['role_templates']), 8)
        self.assertEqual(len(state['team_memberships']), 1)
        self.assertEqual(state['tasks'], [])
        self.assertEqual(state['settings']['reserved_usd'], 0)

    def test_reject_untrusted_fields_and_invalid_execution_limits(self):
        project = self.project('Safe')
        agent = self.agent(project)
        for body in ({'api_key': 'forbidden'}, {'spent_usd': 0}, {'reserved_usd': 0}, {'budget_usd': True}):
            self.post('/api/agents/' + agent['id'], body, 400)
        for body in ({'max_concurrency': 0}, {'max_concurrency': 17}, {'max_concurrency': True},
                     {'max_delegation_depth': -1}, {'max_delegated_tasks': 0}):
            self.post('/api/settings', body, 400)
        self.post('/api/projects/' + project['id'], {'budget_usd': -1}, 400)
        self.assertEqual(self.request('POST', '/api/agents', {'template_id': 'engineering'}, {'X-Genesis-CSRF': 'wrong'})[0], 403)
