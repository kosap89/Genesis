"""Offline persistence and permission tests; no providers are involved."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest

from genesis.documents import VentureDocuments
from genesis.store import Store


class VentureDocumentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'state.sqlite3'
        self.store = Store(self.path)
        for venture in ('a', 'b'):
            self.store.put('ventures', dict(id=venture, name=venture))
        self.documents = VentureDocuments(self.store, self.root)

    def create(self, **fields):
        return self.documents.create('a', dict(name='RULES.md', content='Original rules', **fields))

    def test_reference_survives_restart_without_file_writes(self):
        protected = self.root / 'RULES.md'
        protected.write_text('Existing host file', encoding='utf-8')
        doc = self.create()
        self.assertTrue(doc['read_only'])
        restarted = VentureDocuments(Store(self.path), self.root)
        self.assertEqual(restarted.get('a', doc['id']), doc)
        self.assertEqual(protected.read_text(encoding='utf-8'), 'Existing host file')
        self.assertFalse((self.root / 'workspaces').exists())

    def test_ceo_revision_preserves_original_and_author(self):
        original = self.create()
        revised = self.documents.update('a', original['id'],
            dict(expected_revision=1, content='Revised rules'))
        self.assertEqual(revised['version'], 2)
        self.assertEqual(revised['revision'], 2)
        history = self.documents.revisions('a', original['id'])
        self.assertEqual([r['version'] for r in history], [1, 2])
        self.assertEqual(history[0]['document'], original)
        self.assertEqual(history[1]['actor'], 'ceo')
        self.assertEqual(history[1]['document']['content'], 'Revised rules')
        self.assertEqual(len(self.store.events()), 2)

    def test_strict_venture_isolation_and_missing_venture(self):
        doc = self.create()
        self.assertEqual(self.documents.list('b'), [])
        for operation in (
            lambda: self.documents.get('b', doc['id']),
            lambda: self.documents.revisions('b', doc['id']),
            lambda: self.documents.update('b', doc['id'], dict(expected_revision=1, content='leak')),
            lambda: self.documents.list('missing'),
            lambda: self.documents.create('missing', dict(name='x.md', content='x')),
        ):
            with self.assertRaises(ValueError):
                operation()
        # The same logical basename in another venture is independent.
        other = self.documents.create('b', dict(name='RULES.md', content='Other rules'))
        self.assertNotEqual(doc['id'], other['id'])

    def test_agents_cannot_revise_reference_or_decisions(self):
        reference = self.create()
        decision = self.documents.create('a', dict(name='DECISIONS.md', kind='decisions',
                                                   content='Approved by CEO', read_only=False))
        for document in (reference, decision):
            for fields in ({'content': 'Changed'}, {'kind': 'proposal'}, {'read_only': False}):
                with self.assertRaises(PermissionError):
                    self.documents.update('a', document['id'], dict(expected_revision=1, **fields),
                                          actor='agent:designer')
            self.assertEqual(len(self.documents.revisions('a', document['id'])), 1)
        with self.assertRaises(PermissionError):
            self.documents.create('a', dict(name='D.md', kind='decisions', content='self-approved'),
                                  actor='agent:designer')

    def test_agent_proposals_and_ceo_lock(self):
        doc = self.documents.create('a', dict(name='PROPOSAL.md', kind='proposal', content='Idea'),
                                    actor='agent:designer')
        doc = self.documents.update('a', doc['id'], dict(expected_revision=1, content='Improved'),
                                    actor='agent:reviewer')
        self.assertEqual(doc['updated_by'], 'agent:reviewer')
        with self.assertRaises(PermissionError):
            self.documents.update('a', doc['id'], dict(expected_revision=2, kind='decisions'),
                                  actor='agent:reviewer')
        doc = self.documents.update('a', doc['id'], dict(expected_revision=2, read_only=True))
        self.assertTrue(doc['read_only'])
        with self.assertRaises(PermissionError):
            self.documents.update('a', doc['id'], dict(expected_revision=3, content='overwrite'),
                                  actor='agent:designer')

    def test_stale_or_missing_revision_rejected(self):
        doc = self.create()
        for revision in (None, 0, -1, True, '1', 2):
            with self.assertRaises(ValueError):
                self.documents.update('a', doc['id'], dict(expected_revision=revision, content='x'))
        with self.assertRaises(ValueError):
            self.documents.update('a', doc['id'], dict(content='x'))
        self.assertEqual(self.documents.get('a', doc['id'])['version'], 1)

    def test_concurrent_updates_one_wins(self):
        doc = self.create()
        def revise(content):
            try:
                return self.documents.update('a', doc['id'], dict(expected_revision=1, content=content))
            except ValueError:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(revise, ['First', 'Second']))
        self.assertEqual(sum(result is not None for result in results), 1)
        self.assertEqual(len(self.documents.revisions('a', doc['id'])), 2)

    def test_safe_names_duplicate_and_metadata_validation(self):
        for name in ('../x.md', 'a/x.md', 'a\\x.md', 'C:x.md', '/x.md', 'x.exe',
                     'NUL.md', 'CON.txt', 'x.md ', 'x\x00.md', ''):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.documents.create('a', dict(name=name, content='x'))
        doc = self.create()
        with self.assertRaises(ValueError):
            self.documents.create('a', dict(name='rules.MD', content='Duplicate'))
        for fields in ({'api_key': 'do-not-store'}, {'id': 'chosen'}, {'version': 99},
                       {'content': 'x' * 200001}, {'kind': []}, {'read_only': 1}):
            with self.assertRaises(ValueError):
                self.documents.update('a', doc['id'], dict(expected_revision=1, **fields))
        self.assertEqual(self.documents.get('a', doc['id'])['version'], 1)

    def test_creation_and_revision_are_one_transaction(self):
        original_batch = self.store.batch
        def fail_batch(records, events=()):
            # An unserializable event aborts the same SQLite transaction.
            original_batch(records, [dict(unserializable=object())])
        self.store.batch = fail_batch
        with self.assertRaises(TypeError):
            self.create()
        self.store.batch = original_batch
        self.assertEqual(self.documents.list('a'), [])
        self.assertEqual(self.store.all('venture_document_revisions'), [])


if __name__ == '__main__':
    unittest.main()
