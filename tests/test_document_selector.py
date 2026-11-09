"""Exact project-local document selectors; all tests are offline, without inference."""
from pathlib import Path
import tempfile
import unittest

from genesis.engine import Engine


class DocumentSelectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.engine = Engine(root / 'data', root)
        self.addCleanup(self.engine.close)
        self.project = self.engine.store.put('ventures', {'name': 'Cooperation test'})
        self.other = self.engine.store.put('ventures', {'name': 'Private other project'})
        self.task = self.engine.create_task('Append one word offline', self.project['id'], role='operations')
        self.document = self.engine.documents.create(self.project['id'],
            {'name': 'COOP_TEST.md', 'kind': 'proposal', 'content': 'Me teemme'})

    def tool(self, action, **args):
        return self.engine._core_tool(self.task, 'venture_document_' + action, args)

    def test_name_read_then_update_preserves_revision_and_real_author(self):
        read = self.tool('read', document_name='coop_test.MD')
        self.assertEqual(read['id'], self.document['id'])
        self.assertEqual(read['content'], 'Me teemme')
        revised = self.tool('update', document_name=read['name'],
            expected_revision=read['revision'], content=read['content'] + ' together')
        self.assertEqual(revised['content'], 'Me teemme together')
        self.assertEqual(revised['version'], 2)
        self.assertEqual(revised['updated_by'], 'agent:operations')
        history = self.engine.documents.revisions(self.project['id'], self.document['id'])
        self.assertEqual([r['actor'] for r in history], ['ceo', 'agent:operations'])
        self.assertEqual(self.engine.settings()['spent_usd'], 0)

    def test_stale_named_write_cannot_erase_another_contribution(self):
        self.tool('update', document_name='COOP_TEST.md', expected_revision=1,
            content='Me teemme together')
        with self.assertRaises(ValueError):
            self.tool('update', document_name='COOP_TEST.md', expected_revision=1,
                content='Lost contribution')
        current = self.engine.documents.get(self.project['id'], self.document['id'])
        self.assertEqual(current['content'], 'Me teemme together')
        self.assertEqual(current['version'], 2)

    def test_name_lookup_does_not_bypass_reference_or_decision_protection(self):
        for name, kind in [('CONCEPT.md', 'reference'), ('DECISIONS.md', 'decisions')]:
            with self.subTest(name=name):
                protected = self.engine.documents.create(self.project['id'],
                    {'name': name, 'kind': kind, 'content': 'Protected human source'})
                with self.assertRaises(PermissionError):
                    self.tool('update', document_name=name, expected_revision=1,
                        content='Agent replacement')
                self.assertEqual(self.engine.documents.get(self.project['id'], protected['id']), protected)
                self.assertEqual(len(self.engine.documents.revisions(self.project['id'], protected['id'])), 1)

    def test_name_is_scoped_and_foreign_id_cannot_redirect_to_local_name(self):
        foreign = self.engine.documents.create(self.other['id'],
            {'name': 'COOP_TEST.md', 'kind': 'proposal', 'content': 'PRIVATE'})
        self.assertEqual(self.tool('read', document_name='COOP_TEST.md')['id'], self.document['id'])
        for action in ('read', 'update'):
            with self.subTest(action=action), self.assertRaises(ValueError):
                self.tool(action, document_id=foreign['id'], document_name='COOP_TEST.md',
                    expected_revision=1, content='Unauthorized redirect')
        self.assertEqual(self.engine.documents.get(self.other['id'], foreign['id']), foreign)
        self.assertEqual(self.engine.documents.get(self.project['id'], self.document['id']), self.document)

    def test_both_selectors_must_match_and_no_typo_is_silently_corrected(self):
        other_local = self.engine.documents.create(self.project['id'],
            {'name': 'OTHER.md', 'kind': 'proposal', 'content': 'Do not change'})
        selected = self.engine.documents.resolve(self.project['id'],
            document_id=self.document['id'], document_name='coop_test.md')
        self.assertEqual(selected['id'], self.document['id'])
        for selectors in [
                {'document_id': other_local['id'], 'document_name': 'COOP_TEST.md'},
                {'document_id': self.document['id'][:-1] + '?', 'document_name': 'COOP_TEST.md'},
                {'document_name': 'COOP_TSET.md'},
                {}]:
            with self.subTest(selectors=selectors), self.assertRaises(ValueError):
                self.tool('update', **selectors, expected_revision=1, content='Wrong target')
        self.assertEqual(self.engine.documents.get(self.project['id'], self.document['id']), self.document)
        self.assertEqual(self.engine.documents.get(self.project['id'], other_local['id']), other_local)

    def test_missing_lookup_explains_exact_name_recovery(self):
        for selectors in ({'document_id': 'mistyped-id'}, {'document_name': 'MISSING.md'}):
            with self.subTest(selectors=selectors), self.assertRaisesRegex(ValueError, 'venture_document_list'):
                self.tool('read', **selectors)
        self.assertEqual(self.engine.documents.resolve(self.project['id'],
            document_id=self.document['id'])['id'], self.document['id'])

    def test_invalid_selectors_fail_without_document_changes(self):
        for selectors in [
                {'document_id': []}, {'document_name': True},
                {'document_id': ''}, {'document_name': ''},
                {'document_name': 'x' * 201},
                {'document_name': ' COOP_TEST.md'},
                {'document_name': '../COOP_TEST.md'}]:
            with self.subTest(selectors=selectors), self.assertRaises(ValueError):
                self.tool('update', **selectors, expected_revision=1, content='Must not write')
        self.assertEqual(self.engine.documents.get(self.project['id'], self.document['id']), self.document)

    def test_model_tool_contract_allows_name_without_requiring_id(self):
        schemas = {s['name']: s for s in self.engine.core_schemas(self.task)}
        for action in ('read', 'update'):
            with self.subTest(action=action):
                params = schemas['venture_document_' + action]['parameters']
                self.assertIn('document_name', params['properties'])
                self.assertIn('document_id', params['properties'])
                self.assertNotIn('document_id', params['required'])
                self.assertNotIn('document_name', params['required'])
        self.assertTrue({'content', 'expected_revision'}.issubset(
            schemas['venture_document_update']['parameters']['required']))


if __name__ == '__main__':
    unittest.main()
