"""Offline metadata tests: no provider calls or credentials are used."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from genesis.models import default_route
from genesis.store import Store
from genesis.teams import TeamManager

ROLES = {'coo': ('COO', 'Coordinate'), 'engineering': ('Engineering', 'Build'),
         'strategy': ('Strategy', 'Research'), 'qa': ('QA', 'Review'),
         'growth': ('Growth', 'Grow'), 'finance': ('Finance', 'Count'),
         'operations': ('Operations', 'Organize')}


class TeamManagementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'state.sqlite3'
        self.store = Store(self.path)
        for role, (name, description) in ROLES.items():
            self.store.put('agents', dict(default_route(role), id=role, role=role, name=name,
                description=description, input_cost_per_million=10, output_cost_per_million=30, fallbacks=[]))
        for project in ('a', 'b', 'c'):
            self.store.put('ventures', dict(id=project, name=project))
        self.teams = TeamManager(self.store)
        self.teams.setup(ROLES)

    def agent(self, **fields):
        return self.teams.create_agent(dict(template_id='engineering', name='Engineer', project_ids=['a'], **fields))

    def test_unlimited_instances_repeated_role_and_custom_template(self):
        agents = [self.agent() for _ in range(12)]
        self.assertEqual(len({a['id'] for a in agents}), 12)
        self.assertTrue(all(a['role'] == 'engineering' for a in agents))
        template = self.teams.create_template(dict(name='Legal researcher', system_instructions='Cite evidence'))
        custom = self.teams.create_agent(dict(template_id=template['id'], name='Researcher', project_ids=['b']))
        self.assertEqual(custom['role'], template['id'])
        before = self.store.get('agents', custom['id'])
        self.teams.update_template(template['id'], dict(system_instructions='Updated'))
        self.assertEqual(self.store.get('agents', custom['id']), before)
        self.assertEqual(len(self.store.all('agents')), 20)

    def test_project_overrides_isolated_and_legacy_compatibility(self):
        agent = self.agent()
        self.teams.assign('b', agent['id'], dict(responsibilities='Inspect', overrides=dict(model='gpt-4.1', reasoning_effort=None)))
        self.assertEqual(self.teams.effective_agent(agent['id'], 'b')['model'], 'gpt-4.1')
        self.assertEqual(self.teams.effective_agent(agent['id'], 'a')['model'], 'gpt-6.1-sol')
        self.assertEqual(self.store.get('agents', agent['id'])['model'], 'gpt-6.1-sol')
        with self.assertRaises(ValueError):
            self.teams.effective_agent(agent['id'], 'c')
        self.assertEqual(self.teams.resolve_agent(role='engineering', venture_id='c')['id'], 'engineering')
        self.teams.update_membership('b', agent['id'], dict(enabled=False))
        with self.assertRaises(ValueError):
            self.teams.effective_agent(agent['id'], 'b')
        self.teams.update_agent(agent['id'], dict(enabled=False))
        with self.assertRaises(ValueError):
            self.teams.effective_agent(agent['id'], 'a')

    def test_remove_reassign_and_duplicate_preserve_history_and_cost(self):
        agent = self.agent()
        self.store.put('tasks', dict(id='old', agent_id=agent['id'], role='engineering', venture_id='a', status='completed', cost_usd=2))
        self.store.update('agents', agent['id'], spent_usd=2, reserved_usd=.2)
        self.teams.update_membership('a', agent['id'], dict(action='remove'))
        with self.assertRaises(ValueError):
            self.teams.effective_agent(agent['id'], 'a')
        self.teams.assign('a', agent['id'])
        duplicate = self.teams.duplicate_agent(agent['id'], dict(name='Copy', project_ids=['b']))
        self.assertNotEqual(agent['id'], duplicate['id'])
        self.assertEqual(duplicate['spent_usd'], 0)
        self.assertEqual(duplicate['reserved_usd'], 0)
        self.teams.update_agent(agent['id'], dict(budget_usd=4, project_ids=['b']))
        original = self.store.get('agents', agent['id'])
        self.assertEqual((original['spent_usd'], original['reserved_usd']), (2, .2))
        states = {a['id']: a for a in self.teams.state()['agents']}
        self.assertEqual(states[agent['id']]['task_count'], 1)
        self.assertEqual(states[duplicate['id']]['task_count'], 0)
        self.assertEqual(states[agent['id']]['project_ids'], ['b'])
        self.assertIsNotNone(self.store.get('tasks', 'old'))

    def test_persistence_and_project_ledger_preservation(self):
        agent = self.agent()
        self.teams.assign('b', agent['id'], dict(responsibilities='Tests'))
        self.store.update('ventures', 'b', spent_usd=1.2, reserved_usd=.3)
        self.teams.update_project('b', dict(budget_usd=5))
        restarted = TeamManager(Store(self.path))
        restarted.setup(ROLES)
        self.assertEqual(restarted.effective_agent(agent['id'], 'b')['responsibilities'], 'Tests')
        project = self.store.get('ventures', 'b')
        self.assertEqual((project['spent_usd'], project['reserved_usd']), (1.2, .3))
        self.assertEqual(project['budget_usd'], 5)

    def test_migration_preserves_legacy_configs_and_initializes_cost_once(self):
        store = Store(Path(self.temp.name) / 'legacy.sqlite3')
        config = dict(id='engineering', role='engineering', name='Legacy named', provider='openai', model='gpt-4.1',
                      input_cost_per_million=17, output_cost_per_million=42, fallbacks=[dict(provider='gemini', model='gemini-2.5-flash')])
        store.put('agents', config)
        store.put('ventures', dict(id='legacy', name='Legacy'))
        store.put('tasks', dict(id='old', role='engineering', venture_id='legacy', cost_usd=.7, status='completed'))
        teams = TeamManager(store)
        teams.setup(ROLES)
        migrated = store.get('agents', 'engineering')
        for key, value in config.items():
            self.assertEqual(migrated[key], value)
        self.assertTrue(migrated['legacy_default'])
        self.assertEqual(migrated['spent_usd'], .7)
        self.assertEqual(store.get('tasks', 'old')['agent_id'], 'engineering')
        self.assertEqual(store.get('ventures', 'legacy')['spent_usd'], .7)
        store.update('tasks', 'old', cost_usd=20)
        store.update('agents', 'engineering', spent_usd=3, reserved_usd=.2)
        teams.setup(ROLES)
        self.assertEqual(store.get('agents', 'engineering')['spent_usd'], 3)
        self.assertEqual(store.get('agents', 'engineering')['reserved_usd'], .2)
        self.assertEqual(store.get('ventures', 'legacy')['spent_usd'], .7)

    def test_concurrent_creation_has_unique_ids_and_atomic_membership(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            agents = list(pool.map(lambda _: self.agent(), range(30)))
        self.assertEqual(len({a['id'] for a in agents}), 30)
        self.assertEqual(len(self.store.all('team_memberships')), 30)
        self.assertTrue(all(self.teams.effective_agent(a['id'], 'a')['id'] == a['id'] for a in agents))

    def test_route_reset_guard_bounds_and_rejected_membership_are_atomic(self):
        agent = self.agent()
        self.teams.update_agent(agent['id'], dict(reasoning_effort='high'))
        unchanged = self.teams.update_agent(agent['id'], dict(model='gpt-6.1-sol'))
        self.assertEqual(unchanged['reasoning_effort'], 'high')
        updated = self.teams.update_agent(agent['id'], dict(model='gpt-4.1'))
        self.assertIsNone(updated.get('reasoning_effort'))
        self.teams.assign('b', agent['id'], dict(overrides=dict(model='gpt-4.1')))
        for fields in (dict(input_cost_per_million=0), dict(output_cost_per_million=100001),
                       dict(fallbacks=[dict(provider='openai')]),
                       dict(fallbacks=[dict(provider='openai', model='gpt-4.1', input_cost_per_million=10)])):
            before = self.teams.state()
            with self.assertRaises(ValueError):
                self.teams.assign('c', agent['id'], dict(overrides=fields))
            self.assertEqual(self.teams.state(), before)
        before = self.store.get('ventures', 'a')
        with self.assertRaises(ValueError):
            self.teams.update_project('a', dict(budget_usd=True))
        self.assertEqual(self.store.get('ventures', 'a'), before)

    def test_standalone_agent_and_stable_activity_identity(self):
        agent = self.teams.create_agent(dict(template_id='engineering', name='Standalone'))
        self.assertEqual(self.teams.resolve_agent(agent_id=agent['id'])['id'], agent['id'])
        self.teams.assign('a', agent['id'])
        with self.assertRaises(ValueError):
            self.teams.resolve_agent(agent_id=agent['id'])
        self.store.put('tasks', dict(id='queued', agent_id=agent['id'], role='engineering', status='queued'))
        state = {a['id']: a for a in self.teams.state()['agents']}
        self.assertEqual(state[agent['id']]['activity_status'], 'active')
        self.assertEqual(state['engineering']['activity_status'], 'idle')
        self.store.update('tasks', 'queued', agent_history=[agent['id'], 'engineering'])
        historical = {a['id']: a for a in self.teams.state()['agents']}
        self.assertEqual(historical['engineering']['task_count'], 1)
        self.assertEqual(historical['engineering']['activity_status'], 'idle')
        self.teams.update_agent(agent['id'], dict(name='Renamed', enabled=False))
        state = {a['id']: a for a in self.teams.state()['agents']}
        self.assertEqual(state[agent['id']]['activity_status'], 'disabled')
        self.assertEqual(state[agent['id']]['task_count'], 1)

    def test_invalid_configuration_has_no_partial_writes(self):
        bad_values = [True, -1, float('nan'), float('inf'), 1000001, '5']
        agent = self.agent()
        for bad in bad_values:
            with self.subTest(budget=bad):
                before = self.teams.state()
                with self.assertRaises(ValueError):
                    self.teams.update_agent(agent['id'], dict(budget_usd=bad, name='Changed', project_ids=['b']))
                self.assertEqual(self.teams.state(), before)
        invalid = [dict(project_ids=['missing']), dict(project_ids=['a', 'a']), dict(enabled='yes'),
                   dict(api_key='secret'), dict(astra_authorized=True), dict(spent_usd=0),
                   dict(model=''), dict(model=None), dict(provider={}), dict(provider=[]),
                   dict(fallbacks=[{}, {}, {}]), dict(fallbacks=[dict(api_key='secret')]),
                   dict(model='gpt-6.1-sol', reasoning_effort='invalid')]
        for fields in invalid:
            with self.subTest(fields=fields):
                before = deepcopy(self.teams.state())
                body = dict(template_id='engineering', name='Invalid')
                body.update(fields)
                with self.assertRaises(ValueError):
                    self.teams.create_agent(body)
                self.assertEqual(self.teams.state(), before)
        self.teams.update_agent(agent['id'], dict(model='gpt-6-astra', reasoning_effort='low'))
        selected = self.store.get('agents', agent['id'])
        self.assertNotIn('astra_authorized', selected)
        self.teams.update_agent(agent['id'], dict(budget_usd=None, enabled=False))


if __name__ == '__main__':
    unittest.main()
