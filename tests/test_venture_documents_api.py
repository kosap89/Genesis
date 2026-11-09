"""Real loopback venture documentation API; workers and providers are never run."""
import unittest
import test_server


class VentureDocumentApiTests(unittest.TestCase):
    setUp = test_server.ServerTests.setUp
    stop_server = test_server.ServerTests.stop_server
    request = test_server.ServerTests.request
    post = test_server.ServerTests.post

    def project(self, name):
        return self.post('/api/ventures', {'name': name}, 201)

    def test_documents_are_revisioned_downloadable_and_project_scoped(self):
        a, b = self.project('A'), self.project('B')
        root = '/api/projects/' + a['id'] + '/documents'
        text = '# Original concept\n\nIncomplete source. <script>literal only</script>\n'
        doc = self.post(root, {'name': 'CONCEPT.md', 'kind': 'reference', 'read_only': True, 'content': text}, 201)
        detail = root + '/' + doc['id']
        self.assertEqual(self.request('GET', root)[1]['documents'][0]['content'], text)
        self.assertEqual(self.request('GET', detail)[1]['read_only'], True)
        code, raw, headers = self.request('GET', detail + '/download')
        self.assertEqual(code, 200)
        self.assertEqual(raw.decode('utf-8'), text)
        self.assertIn('attachment', headers['Content-Disposition'])
        self.assertIn('CONCEPT.md', headers['Content-Disposition'])
        self.post(detail, {'content': text + 'CEO clarification.\n', 'expected_revision': doc['version']})
        versions = self.request('GET', detail + '/revisions')[1]['revisions']
        self.assertEqual(len(versions), 2)
        self.assertTrue(any(v['document']['content'] == text for v in versions))
        self.post(detail, {'content': 'Stale overwrite', 'expected_revision': doc['version']}, 400)
        other = '/api/projects/' + b['id'] + '/documents/' + doc['id']
        self.assertEqual(self.request('GET', other)[0], 404)
        self.assertEqual(self.request('GET', other + '/download')[0], 404)
        self.post(other, {'content': 'Cross project', 'expected_revision': 2}, 400)
        self.assertEqual(self.engine.store.all('tasks'), [])
        self.assertEqual(self.engine.settings()['spent_usd'], 0)

    def test_project_instructions_do_not_change_global_agents_or_other_projects(self):
        a, b = self.project('A'), self.project('B')
        original = self.engine.store.get('agents', 'strategy')
        self.post('/api/projects/' + a['id'], {'operating_policy': 'Mechanics only. Human creative authority.'})
        self.post('/api/projects/' + a['id'] + '/team', {'agent_id': 'strategy',
            'system_instructions': 'Explore provisional combat alternatives.',
            'specialization': 'Game designer', 'responsibilities': 'Mechanics review',
            'overrides': {'provider': 'openai', 'model': 'gpt-6.1-sol', 'reasoning_effort': 'high', 'fallbacks': []}})
        config = self.engine.teams.effective_agent('strategy', a['id'])
        self.assertEqual(config['system_instructions'], 'Explore provisional combat alternatives.')
        self.assertEqual(config['reasoning_effort'], 'high')
        self.assertEqual(self.engine.store.get('agents', 'strategy'), original)
        self.assertEqual(self.engine.teams.effective_agent('strategy', b['id']), original)
        self.post('/api/projects/' + a['id'], {'allow_terminal': True}, 400)
        self.assertFalse(self.engine.settings()['allow_terminal'])

    def test_document_mutations_keep_http_guards_and_reject_fake_authorship(self):
        p = self.project('Guarded')
        root = '/api/projects/' + p['id'] + '/documents'
        body = {'name': 'DECISIONS.md', 'kind': 'decisions', 'content': 'No decisions approved.'}
        self.assertEqual(self.request('POST', root, body, {'X-Genesis-CSRF': 'wrong'})[0], 403)
        self.post(root, {**body, 'actor': 'ceo'}, 400)
        self.post(root, {**body, 'name': '../DECISIONS.md'}, 400)
        self.post(root, body, 201)
        self.post(root, body, 400)
        self.assertEqual(len(self.engine.documents.list(p['id'])), 1)
