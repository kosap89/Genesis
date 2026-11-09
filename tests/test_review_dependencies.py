"""Review targets are evidence, not implicit successful prerequisites; offline only."""
import tempfile
import unittest
from pathlib import Path

from genesis.engine import Engine
from tests.test_engine import ScriptedRouter, response


class ReviewDependencyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.router = ScriptedRouter()
        self.engine = Engine(root / 'data', root, self.router)
        self.addCleanup(self.engine.close)
        self.project = self.engine.store.put('ventures', {'name': 'Review source semantics'})
        self.other = self.engine.store.put('ventures', {'name': 'Other project'})
        self.author = self.engine.teams.create_agent({'template_id': 'engineering', 'name': 'Author',
            'project_ids': [self.project['id'], self.other['id']]})
        self.reviewer = self.engine.teams.create_agent({'template_id': 'qa', 'name': 'Independent reviewer',
            'project_ids': [self.project['id']]})

    def task(self, agent=None, project=None, **options):
        return self.engine.create_task('Inspect actual saved evidence',
            venture_id=(project or self.project)['id'], agent_id=(agent or self.author)['id'], **options)

    def saved_failed_author(self):
        task = self.task()
        document = self.engine.documents.create(self.project['id'],
            {'name': 'GAME_DESIGN.md', 'content': 'Actual saved partial rules', 'kind': 'proposal'},
            actor='agent:' + self.author['id'])
        (self.engine.workspace(task) / 'partial.md').write_text('Actual saved partial rules', encoding='utf-8')
        self.engine.register_artifacts(task)
        self.engine.store.update('tasks', task['id'], status='failed', error='Confirmed provider timeout')
        return task, document

    def current(self, task):
        return self.engine.store.get('tasks', task['id'])

    def test_failed_partial_author_can_be_reviewed_without_marking_it_successful(self):
        author, document = self.saved_failed_author()
        review = self.task(self.reviewer, review_of=[author['id']])
        self.assertEqual(review['depends_on'], [])
        self.assertTrue(self.engine._dependencies_ready(review))
        prompt = self.engine.system_prompt(review)
        self.assertIn(author['id'], prompt)
        self.assertIn('Confirmed provider timeout', prompt)
        self.assertIn('failed', prompt)
        artifact = self.engine.store.all('artifacts')[0]
        self.assertIn(artifact['id'], prompt)
        self.router.script.append(response('Independent critique of actual partial rules only.'))
        self.engine.run(review['id'])
        self.assertEqual(self.current(review)['status'], 'completed')
        self.assertEqual(self.current(author)['status'], 'failed')
        self.assertEqual(self.engine.documents.get(self.project['id'], document['id'])['content'],
                         'Actual saved partial rules')
        self.assertEqual(len(self.router.requests), 1)

    def test_actual_case_completed_continuation_and_failed_original_author(self):
        author, _ = self.saved_failed_author()
        continuation = self.task()
        self.engine.store.update('tasks', continuation['id'], status='completed', result='Saved remaining sections')
        review = self.task(self.reviewer, depends_on=[continuation['id']],
                           review_of=[author['id'], continuation['id']])
        self.assertEqual(review['depends_on'], [continuation['id']])
        self.assertEqual(review['review_of'], [author['id'], continuation['id']])
        self.assertTrue(self.engine._dependencies_ready(review))
        self.router.script.append(response('Both actual contributors independently assessed.'))
        self.engine.run(review['id'])
        self.assertEqual(self.current(review)['status'], 'completed')
        self.assertEqual(self.current(author)['status'], 'failed')

    def test_nonterminal_review_source_waits_without_provider_call(self):
        author = self.task()
        self.engine.store.update('tasks', author['id'], status='running')
        review = self.task(self.reviewer, review_of=[author['id']])
        self.engine.run(review['id'])
        self.assertEqual(self.router.requests, [])
        self.assertNotEqual(self.current(review)['status'], 'completed')
        self.engine.store.update('tasks', author['id'], status='failed', error='Stopped after partial save')
        self.assertTrue(self.engine._dependencies_ready(self.current(review)))

    def test_explicit_failed_success_dependency_still_blocks_even_when_reviewed(self):
        author, _ = self.saved_failed_author()
        review = self.task(self.reviewer, depends_on=[author['id']], review_of=[author['id']])
        self.assertFalse(self.engine._dependencies_ready(review))
        self.assertEqual(self.current(review)['status'], 'blocked_dependencies')
        self.engine.run(review['id'])
        self.assertEqual(self.router.requests, [])

    def test_cancelled_source_can_be_inspected_without_replaying_it(self):
        author, document = self.saved_failed_author()
        self.engine.store.update('tasks', author['id'], status='cancelled')
        review = self.task(self.reviewer, review_of=[author['id']])
        self.assertTrue(self.engine._dependencies_ready(review))
        self.router.script.append(response('Only retained evidence was inspected; cancelled work not replayed.'))
        self.engine.run(review['id'])
        self.assertEqual(self.current(author)['status'], 'cancelled')
        self.assertEqual(self.engine.documents.get(self.project['id'], document['id'])['version'], 1)
        self.assertEqual(len(self.router.requests), 1)

    def test_self_review_and_foreign_targets_remain_invalid(self):
        author, _ = self.saved_failed_author()
        with self.assertRaisesRegex(ValueError, 'different agent'):
            self.task(review_of=[author['id']])
        foreign = self.task(project=self.other)
        with self.assertRaisesRegex(ValueError, 'same project'):
            self.task(self.reviewer, review_of=[foreign['id']])

    def test_missing_or_foreign_review_source_is_blocked_at_dispatch(self):
        author, _ = self.saved_failed_author()
        foreign = self.task(project=self.other)
        for source in ['missing-source', foreign['id']]:
            with self.subTest(source=source):
                review = self.task(self.reviewer, review_of=[author['id']])
                self.engine.store.update('tasks', review['id'], review_of=[source])
                self.assertFalse(self.engine._dependencies_ready(self.current(review)))
                self.assertEqual(self.current(review)['status'], 'blocked_dependencies')
        self.assertEqual(self.router.requests, [])

    def test_ancestor_cycles_follow_review_sources_as_well_as_dependencies(self):
        parent = self.task(work_mode='collaborative')
        transitively_waiting = self.task(self.reviewer, review_of=[parent['id']])
        self.engine.store.update('tasks', parent['id'], status='running')
        for options in [{'review_of': [parent['id']]}, {'depends_on': [transitively_waiting['id']]}]:
            with self.subTest(options=options), self.assertRaisesRegex(ValueError, 'ancestor'):
                self.engine._core_tool(parent, 'delegate_task',
                    {'objective': 'Reject deadlock', 'agent_id': self.reviewer['id'], **options},
                    delegation_authorized=True)
        self.assertEqual(len(self.engine.store.all('tasks')), 2)


if __name__ == '__main__':
    unittest.main()
