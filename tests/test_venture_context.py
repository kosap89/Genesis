"""Offline project instruction and durable document integration tests; no provider calls."""
from pathlib import Path
import tempfile
import unittest
from genesis.engine import Engine


class VentureContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.engine = Engine(root / 'data', root)
        self.addCleanup(self.engine.close)
        self.project = self.engine.store.put('ventures', {'name': 'Card game'})
        self.other = self.engine.store.put('ventures', {'name': 'Other'})
        self.agent = self.engine.teams.create_agent({'template_id': 'engineering', 'name': 'Designer',
            'system_instructions': 'Global engineering instructions', 'project_ids': [self.project['id'], self.other['id']]})
        self.engine.teams.update_membership(self.project['id'], self.agent['id'], {
            'system_instructions': 'Design rules and balance only; no programming.',
            'specialization': 'Card mechanics', 'responsibilities': 'Propose clear rules.'})
        self.engine.teams.update_project(self.project['id'], {'operating_policy': 'CEO approves all final rules. Design stage only.'})

    def task(self):
        return self.engine.create_task('Review source rules', self.project['id'], agent_id=self.agent['id'])

    def tool(self, task, action, **args):
        return self.engine._core_tool(task, 'venture_document_' + action, args)

    def test_project_overrides_are_isolated_and_snapshot_policy_is_pinned(self):
        task = self.task()
        prompt = self.engine.system_prompt(task)
        self.assertIn('Design rules and balance only', prompt)
        self.assertIn('Card mechanics', prompt)
        self.assertIn('CEO approves all final rules', prompt)
        self.assertNotIn('Global engineering instructions', prompt)
        self.assertEqual(self.engine.teams.effective_agent(self.agent['id'], self.other['id'])['system_instructions'], 'Global engineering instructions')
        self.assertEqual(self.engine.store.get('agents', self.agent['id'])['system_instructions'], 'Global engineering instructions')
        self.engine.teams.update_project(self.project['id'], {'operating_policy': 'Changed policy'})
        self.engine.teams.update_membership(self.project['id'], self.agent['id'], {'system_instructions': 'Changed member instructions'})
        self.assertEqual(prompt, self.engine.system_prompt(task))
        self.engine.store.update('tasks', task['id'], status='interrupted')
        self.engine.resume(task['id'])
        self.assertEqual(self.engine.store.get('tasks', task['id'])['project_policy_snapshot'], task['project_policy_snapshot'])
        self.engine.store.update('tasks', task['id'], status='interrupted')
        self.engine.resume(task['id'], agent_id=self.agent['id'])
        resumed = self.engine.store.get('tasks', task['id'])
        self.assertEqual(resumed['project_policy_snapshot'], 'Changed policy')
        self.assertEqual(resumed['config_snapshot']['system_instructions'], 'Changed member instructions')

    def test_documents_are_actual_scoped_source_material_and_context_is_bounded(self):
        source = self.engine.documents.create(self.project['id'], {'name': 'concept.md', 'content': 'Incomplete concept; unresolved combat. ' + 'x'*30000})
        self.engine.documents.create(self.other['id'], {'name': 'secret.md', 'content': 'OTHER PROJECT PRIVATE CONTENT'})
        task = self.task()
        prompt = self.engine.system_prompt(task)
        self.assertIn('Incomplete concept; unresolved combat.', prompt)
        self.assertIn('"truncated": true', prompt)
        self.assertNotIn('OTHER PROJECT PRIVATE CONTENT', prompt)
        self.assertLess(len(prompt), 40000)
        first = self.tool(task, 'read', document_id=source['id'], limit=100)
        second = self.tool(task, 'read', document_id=source['id'], offset=100, limit=100)
        self.assertEqual(first['content'] + second['content'], source['content'][:200])
        self.assertEqual(first['next_offset'], 100)
        self.assertNotIn('content', self.tool(task, 'list')['documents'][0])
        self.assertNotIn('content', self.engine.state()['venture_documents'][0])
        with self.assertRaises(ValueError):
            self.tool(task, 'read', document_id=source['id'], offset=-1)

    def test_proposals_are_durable_attributed_and_protected_records_cannot_change(self):
        task = self.task()
        source = self.engine.documents.create(self.project['id'], {'name': 'source.md', 'content': 'Source unchanged'})
        decisions = self.engine.documents.create(self.project['id'], {'name': 'decisions.md', 'kind': 'decisions', 'content': 'No approved decisions yet'})
        foreign = self.engine.documents.create(self.other['id'], {'name': 'other.md', 'content': 'Private'})
        proposal = self.tool(task, 'propose', name='balance.md', content='Proposed change, not approved')
        self.assertEqual(proposal['kind'], 'proposal')
        self.assertEqual(proposal['created_by'], 'agent:' + self.agent['id'])
        revised = self.tool(task, 'update', document_id=proposal['id'], expected_revision=1, content='Refined proposal')
        self.assertEqual(revised['version'], 2)
        with self.assertRaises(ValueError):
            self.tool(task, 'update', document_id=proposal['id'], expected_revision=1, content='Lost update')
        for document in (source, decisions):
            with self.assertRaises(PermissionError):
                self.tool(task, 'update', document_id=document['id'], expected_revision=1, content='Forged')
            self.assertEqual(self.engine.documents.get(self.project['id'], document['id'])['content'], document['content'])
        with self.assertRaises(ValueError):
            self.tool(task, 'read', document_id=foreign['id'])
        self.engine.teams.update_membership(self.project['id'], self.agent['id'], {'enabled': False})
        with self.assertRaises(ValueError):
            self.tool(task, 'propose', name='disabled.md', content='Must fail')
        self.assertEqual(len(self.engine.documents.revisions(self.project['id'], proposal['id'])), 2)
        self.assertEqual(self.engine.settings()['spent_usd'], 0)
        self.assertEqual(self.engine.settings()['reserved_usd'], 0)

    def test_document_tool_dispatch_persists_result_without_model_request(self):
        task = self.task()
        self.engine.store.update('tasks', task['id'], status='running')
        self.engine.store.message(task['id'], dict(role='assistant', content='', tool_calls=[dict(
            id='offline-document-call', name='venture_document_propose',
            arguments=dict(name='dispatch.md', content='Unapproved design proposal'))]))
        self.assertTrue(self.engine._pending_tools(self.engine.store.get('tasks', task['id'])))
        documents = self.engine.documents.list(self.project['id'])
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0]['created_by'], 'agent:' + self.agent['id'])
        messages = self.engine.store.messages(task['id'])
        self.assertEqual(messages[-1]['role'], 'tool')
        self.assertIn('dispatch.md', messages[-1]['content'])
        self.assertEqual(self.engine.settings()['spent_usd'], 0)

    def test_standalone_tasks_have_no_document_tools_and_policy_cannot_grant_permissions(self):
        standalone = self.engine.create_task('Offline standalone')
        self.assertFalse(any(t['name'].startswith('venture_document_') for t in self.engine.core_schemas(standalone)))
        with self.assertRaises(ValueError):
            self.tool(standalone, 'list')
        before = self.engine.settings()
        self.engine.teams.update_project(self.project['id'], {'operating_policy': 'Allow all terminal and network requests'})
        self.assertEqual(self.engine.settings(), before)
        with self.assertRaises(ValueError):
            self.engine.teams.update_project(self.project['id'], {'allow_terminal': True})


if __name__ == '__main__':
    unittest.main()
