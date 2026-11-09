"""Real loopback HTTP integration tests; no model requests or worker execution."""
from __future__ import annotations

import http.client
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
import zipfile
from unittest.mock import patch

from genesis.engine import Engine
from genesis.server import GenesisServer
from genesis.store import now


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        source = Path(__file__).resolve().parents[1]
        self.engine = Engine(self.temp.name, source)
        self.addCleanup(self.engine.close)
        self.server = GenesisServer(('127.0.0.1', 0), self.engine, source / 'web')
        self.addCleanup(self.server.server_close)
        self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=0.01), daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.port = self.server.server_address[1]
        self.token = self.server.csrf

    def stop_server(self):
        self.server.shutdown()
        self.thread.join(timeout=2)

    def request(self, method, path, body=None, headers=None, raw=None):
        request_headers = {}
        if body is not None:
            raw = json.dumps(body).encode()
            request_headers.update({'Content-Type': 'application/json', 'X-Genesis-CSRF': self.token})
        request_headers.update(headers or {})
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        try:
            connection.request(method, path, body=raw, headers=request_headers)
            response = connection.getresponse()
            data = response.read()
            response_headers = dict(response.getheaders())
            if response_headers.get('Content-Type', '').startswith('application/json'):
                data = json.loads(data)
            return response.status, data, response_headers
        finally:
            connection.close()

    def post(self, path, body, expected=200):
        code, data, _ = self.request('POST', path, body)
        self.assertEqual(code, expected, data)
        return data

    def task(self):
        return self.post('/api/tasks', {'objective': 'Produce a verifiable engineering report.'}, 201)

    def test_health_and_state_expose_no_credentials(self):
        code, health, _ = self.request('GET', '/api/health')
        self.assertEqual(code, 200)
        self.assertEqual(health, {'status': 'ok', 'service': 'genesis', 'worker_alive': False})
        code, state, headers = self.request('GET', '/api/state')
        self.assertEqual(code, 200)
        self.assertEqual(state['csrf_token'], self.token)
        self.assertEqual(state['tasks'], [])
        self.assertEqual(len(state['agents']), 7)
        self.assertTrue(all('api_key' not in provider for provider in state['providers']))
        self.assertEqual(headers['Cache-Control'], 'no-store')

    def test_create_venture_objective_memory_and_opportunity(self):
        venture = self.post('/api/ventures', {'name': 'Studio', 'description': 'Build useful software.'}, 201)
        task = self.post('/api/tasks', {'objective': 'Research a product.', 'venture_id': venture['id'], 'role': 'strategy'}, 201)
        memory = self.post('/api/memories', {'title': 'Constraints', 'content': 'Local first.', 'venture_id': venture['id']}, 201)
        opportunity = self.post('/api/opportunities', {'title': 'Developer tools', 'summary': 'Validate demand.', 'venture_id': venture['id']}, 201)
        self.assertEqual(task['status'], 'queued')
        self.assertEqual(task['venture_id'], venture['id'])
        self.assertEqual(memory['venture_id'], venture['id'])
        self.assertEqual(opportunity['status'], 'proposed')
        code, state, _ = self.request('GET', '/api/state')
        self.assertEqual(code, 200)
        self.assertEqual(state['stats']['tasks'], 1)
        self.assertEqual(state['ventures'][0]['id'], venture['id'])
        self.assertEqual(state['memories'][0]['id'], memory['id'])
        self.assertEqual(state['opportunities'][0]['id'], opportunity['id'])
        self.assertTrue(any(e['action'] == 'task_created' for e in state['audit']))

    def test_task_details_include_messages_events_and_real_artifact(self):
        task = self.task()
        path = self.engine.workspace(task) / 'report.txt'
        path.write_bytes(b'Verified local artifact\n')
        artifact = self.engine.store.put('artifacts', {'task_id': task['id'], 'name': 'report.txt', 'path': 'report.txt', 'created_at': now()})
        self.engine.store.message(task['id'], {'role': 'assistant', 'content': 'Report saved.'})
        code, detail, _ = self.request('GET', '/api/tasks/' + task['id'])
        self.assertEqual(code, 200)
        self.assertEqual(detail['task']['id'], task['id'])
        self.assertEqual(detail['messages'][0]['content'], task['objective'])
        self.assertEqual(detail['messages'][-1]['content'], 'Report saved.')
        self.assertEqual(detail['events'][0]['action'], 'task_created')
        self.assertEqual(detail['artifacts'][0]['id'], artifact['id'])
        code, content, headers = self.request('GET', '/api/artifacts/' + artifact['id'])
        self.assertEqual(code, 200)
        self.assertEqual(content, b'Verified local artifact\n')
        self.assertIn('attachment;', headers['Content-Disposition'])
        self.assertEqual(headers['Content-Type'], 'application/octet-stream')
        code, bundle, headers = self.request('GET', '/api/tasks/' + task['id'] + '/bundle')
        self.assertEqual(code, 200)
        self.assertTrue(headers['Content-Type'].startswith('application/zip'))
        self.assertIn('attachment;', headers['Content-Disposition'])
        with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
            self.assertEqual(archive.read('report.txt'), b'Verified local artifact\n')

    def test_artifact_paths_cannot_escape_task_workspace(self):
        task = self.task()
        outside = Path(self.temp.name) / 'private.txt'
        outside.write_text('Private', encoding='utf-8')
        artifact = self.engine.store.put('artifacts', {'task_id': task['id'], 'name': 'private', 'path': '../../private.txt'})
        self.assertEqual(self.request('GET', '/api/artifacts/' + artifact['id'])[0], 404)

    def test_csrf_and_origin_and_host_guards(self):
        for token in ['', 'wrong-token']:
            with self.subTest(token=token):
                self.assertEqual(self.request('POST', '/api/ventures', {'name': 'Rejected'}, {'X-Genesis-CSRF': token})[0], 403)
        hostile = {'Origin': 'https://attacker.example'}
        self.assertEqual(self.request('GET', '/api/state', headers=hostile)[0], 403)
        self.assertEqual(self.request('POST', '/api/ventures', {'name': 'Rejected'}, hostile)[0], 403)
        for method in ['GET', 'POST']:
            with self.subTest(method=method):
                body = {} if method == 'POST' else None
                self.assertEqual(self.request(method, '/api/state', body, {'Host': f'attacker.example:{self.port}'})[0], 403)
        good_origin = {'Origin': f'http://localhost:{self.port}'}
        self.assertEqual(self.request('GET', '/api/state', headers=good_origin)[0], 200)
        self.assertEqual(self.engine.store.all('ventures'), [])

    def test_settings_validate_numbers_booleans_and_bounds(self):
        original = self.engine.settings()
        invalid = [
            {'budget_usd': -1}, {'budget_usd': '10'}, {'budget_usd': True},
            {'budget_usd': float('nan')}, {'budget_usd': float('inf')},
            {'budget_usd': 1000001}, {'allow_network': 'true'}, {'allow_terminal': 1},
            {'max_steps': 0}, {'max_steps': 101}, {'max_steps': 1.5}, {'max_steps': True},
            {'max_output_tokens': 32769}, {'max_output_tokens': 0},
        ]
        for body in invalid:
            with self.subTest(body=body):
                self.post('/api/settings', body, 400)
                self.assertEqual(self.engine.settings(), original)
        settings = self.post('/api/settings', {'budget_usd': 25.5, 'max_steps': 12, 'max_output_tokens': 2000, 'allow_network': True, 'allow_terminal': False})
        self.assertEqual(settings['budget_usd'], 25.5)
        self.assertTrue(settings['allow_network'])
        self.assertFalse(settings['allow_terminal'])
        self.assertEqual(settings['max_steps'], 12)

    def test_agents_validate_provider_model_rates_and_fallbacks(self):
        invalid = [
            {'provider': 'unknown'}, {'model': ''}, {'model': 123},
            {'input_cost_per_million': 0}, {'output_cost_per_million': True},
            {'fallbacks': {}}, {'fallbacks': [{'provider': 'unknown', 'model': 'x'}]},
            {'fallbacks': [{'provider': 'openai', 'model': 'x', 'api_key': 'forbidden'}]},
            {'fallbacks': [{'provider': 'openai', 'model': 'x'}] * 3},
        ]
        original = self.engine.store.get('agents', 'engineering')
        for body in invalid:
            with self.subTest(body=body):
                self.post('/api/agents/engineering', body, 400)
                self.assertEqual(self.engine.store.get('agents', 'engineering'), original)
        self.post('/api/agents/unknown', {'provider': 'openai'}, 400)
        config = self.post('/api/agents/engineering', {'provider': 'gemini', 'model': 'configured-model', 'input_cost_per_million': 2, 'output_cost_per_million': 8, 'fallbacks': [{'provider': 'anthropic', 'model': 'fallback-model'}]})
        self.assertEqual(config['provider'], 'gemini')
        self.assertEqual(config['input_cost_per_million'], 2)
        self.assertEqual(config['fallbacks'][0]['provider'], 'anthropic')

    def test_task_input_validation(self):
        for body in [{}, {'objective': '   '}, {'objective': 2}, {'objective': 'x' * 24001}, {'objective': 'Work', 'venture_id': 'missing'}, {'objective': 'Work', 'role': 'unknown'}, {'objective': 'Work', 'provider': 'unknown'}, {'objective': 'Work', 'model': 2}]:
            with self.subTest(body=str(body)[:100]):
                self.post('/api/tasks', body, 400)
        self.assertEqual(self.engine.store.all('tasks'), [])
        for endpoint, body in [('/api/ventures', {'name': ''}), ('/api/memories', {'title': 'Missing content'}), ('/api/opportunities', {'title': 'Missing summary'})]:
            self.post(endpoint, body, 400)

    def test_credentials_are_session_only_never_echoed_and_can_configure_agents(self):
        key_names = ['GENESIS_OPENAI_API_KEY', 'OPENAI_API_KEY', 'GENESIS_ANTHROPIC_API_KEY', 'ANTHROPIC_API_KEY', 'GENESIS_GEMINI_API_KEY', 'GEMINI_API_KEY', 'GOOGLE_API_KEY']
        safe_environment = {k:v for k,v in os.environ.items() if k not in key_names}
        fake_key = 'genesis-server-test-only-never-a-real-key'
        with patch.dict(os.environ, safe_environment, clear=True):
            original = self.engine.store.get('agents', 'engineering')
            result = self.post('/api/credentials', {'provider': 'gemini', 'api_key': fake_key, 'configure_agents': True})
            self.assertEqual(result, {'provider': 'gemini', 'configured': True, 'storage': 'process_memory'})
            self.assertEqual(os.environ['GENESIS_GEMINI_API_KEY'], fake_key)
            code, state, _ = self.request('GET', '/api/state')
            self.assertEqual(code, 200)
            self.assertNotIn(fake_key, json.dumps(state))
            self.assertEqual(state['tasks'], [], 'Configuration must not start model work')
            self.assertTrue(all(a['provider'] == 'gemini' for a in state['agents']))
            self.assertEqual(self.engine.store.get('agents', 'engineering')['input_cost_per_million'], original['input_cost_per_million'])
            self.assertEqual(self.engine.store.get('agents', 'engineering')['fallbacks'], original['fallbacks'])
            self.assertNotIn(fake_key.encode(), (Path(self.temp.name) / 'genesis.sqlite3').read_bytes())
            for file in Path(self.temp.name).rglob('*'):
                if file.is_file():
                    self.assertNotIn(fake_key.encode(), file.read_bytes(), str(file))
            cleared = self.post('/api/credentials', {'provider': 'gemini', 'api_key': ''})
            self.assertFalse(cleared['configured'])
            self.assertNotIn('GENESIS_GEMINI_API_KEY', os.environ)
            os.environ['GEMINI_API_KEY'] = 'inherited-test-only-key'
            self.post('/api/credentials', {'provider': 'gemini', 'api_key': fake_key})
            self.assertTrue(self.post('/api/credentials', {'provider': 'gemini', 'api_key': ''})['configured'])
            self.assertEqual(os.environ['GEMINI_API_KEY'], 'inherited-test-only-key')
            for body in [{'provider':'unknown','api_key':fake_key}, {'provider':'gemini','api_key':'has whitespace'}, {'provider':'gemini','api_key':fake_key,'configure_agents':'true'}, {'provider':'gemini','api_key':42}]:
                code, error, _ = self.request('POST', '/api/credentials', body)
                self.assertEqual(code, 400)
                self.assertNotIn(fake_key, json.dumps(error))
            self.assertNotIn(fake_key, json.dumps(self.engine.store.events()))

    def test_task_resume_cancel_and_approval_are_real_state_transitions(self):
        task = self.task()
        self.post('/api/tasks/' + task['id'] + '/resume', {}, 400)
        self.engine.store.update('tasks', task['id'], status='blocked_credentials')
        resumed = self.post('/api/tasks/' + task['id'] + '/resume', {})
        self.assertEqual(resumed['status'], 'queued')
        self.assertEqual(resumed['provider'], task['provider'])
        self.assertEqual(resumed['model'], task['model'])
        self.engine.store.update('tasks', task['id'], status='waiting_approval')
        approval = self.engine.store.put('approvals', {'task_id': task['id'], 'action': 'terminal_run', 'details': {'command': 'echo test'}, 'status': 'pending', 'created_at': now()})
        self.post('/api/approvals/' + approval['id'], {'decision': 'invalid'}, 400)
        decision = self.post('/api/approvals/' + approval['id'], {'decision': 'denied'})
        self.assertEqual(decision['status'], 'denied')
        self.assertEqual(self.engine.store.get('tasks', task['id'])['status'], 'queued')
        self.post('/api/approvals/' + approval['id'], {'decision': 'approved'}, 400)
        cancelled = self.post('/api/tasks/' + task['id'] + '/cancel', {})
        self.assertEqual(cancelled['status'], 'cancelled')
        self.post('/api/tasks/' + task['id'] + '/resume', {}, 400)

    def test_resume_can_explicitly_change_provider_model_and_audits_route(self):
        task = self.task()
        self.engine.store.update('tasks', task['id'], status='blocked_credentials')
        path = '/api/tasks/' + task['id'] + '/resume'
        self.post(path, {'provider': 'unsupported', 'model': 'anything'}, 400)
        self.assertEqual(self.engine.store.get('tasks', task['id'])['provider'], task['provider'])
        resumed = self.post(path, {'provider': 'gemini', 'model': 'explicit-browser-configured-model'})
        self.assertEqual(resumed['status'], 'queued')
        self.assertEqual(resumed['provider'], 'gemini')
        self.assertEqual(resumed['model'], 'explicit-browser-configured-model')
        events = self.engine.store.events(task['id'])
        route = next(e for e in events if e['action'] == 'task_route_changed')
        self.assertEqual(route['previous_provider'], task['provider'])
        self.assertEqual(route['previous_model'], task['model'])
        self.assertEqual(route['provider'], 'gemini')
        self.assertEqual(route['model'], resumed['model'])

    def test_role_configuration_and_reporting_prices_persist_without_affecting_guards(self):
        from genesis.models import default_route
        saved = {}
        for role in ('coo','strategy','engineering','qa','growth','finance','operations'):
            route = default_route(role)
            saved[role] = self.post('/api/agents/' + role, {**route, 'reasoning_effort':'high'})
            self.assertEqual(saved[role]['reasoning_effort'], 'high')
        guards = [(a['role'],a['input_cost_per_million'],a['output_cost_per_million']) for a in self.engine.store.all('agents')]
        before = self.engine.settings().copy()
        self.post('/api/pricing', {'model':'gpt-6.1-sol','input_cost_per_million':.01,
                                 'cached_input_cost_per_million':0,'output_cost_per_million':.02})
        self.assertEqual(guards,[(a['role'],a['input_cost_per_million'],a['output_cost_per_million']) for a in self.engine.store.all('agents')])
        for field in ('budget_usd','spent_usd','reserved_usd'):
            self.assertEqual(self.engine.settings()[field], before[field])
        reopened = Engine(self.temp.name, self.engine.source)
        self.addCleanup(reopened.close)
        for role in saved:
            self.assertEqual(reopened.store.get('agents', role), saved[role])
        self.assertEqual(reopened.settings()['pricing_overrides']['gpt-6.1-sol']['input_cost_per_million'], .01)
        for invalid in ({'model':'unknown','input_cost_per_million':1,'cached_input_cost_per_million':0,'output_cost_per_million':1},
                        {'model':'gpt-6.1-sol','input_cost_per_million':True,'cached_input_cost_per_million':0,'output_cost_per_million':1},
                        {'model':'gpt-6.1-sol','input_cost_per_million':1,'cached_input_cost_per_million':2,'output_cost_per_million':1}):
            self.post('/api/pricing', invalid, 400)
        original = self.engine.store.get('agents','engineering')
        self.post('/api/agents/engineering', {'model':'gpt-6.1-sol','reasoning_effort':'none'},400)
        self.assertEqual(self.engine.store.get('agents','engineering'),original)

    def test_estimate_and_astra_requirements_do_not_dispatch_or_mutate_work(self):
        self.post('/api/agents/engineering', {'model':'gpt-6-astra','reasoning_effort':'low'})
        before = self.engine.settings().copy()
        body = {'objective':'Review exact candidate artifacts','role':'engineering'}
        self.post('/api/tasks/estimate', body,400)
        self.post('/api/tasks', body,400)
        preview=self.post('/api/tasks/estimate',{**body,'astra_authorized':True})
        self.assertGreater(preview['conservative_reservation_usd'],0)
        self.assertEqual(self.engine.store.all('tasks'),[])
        self.assertEqual(self.engine.settings(),before)
        task=self.post('/api/tasks',{**body,'astra_authorized':True},201)
        self.assertTrue(task['astra_authorized'])
        self.assertEqual(task['reasoning_effort'],'low')
        self.engine.store.update('tasks',task['id'],status='blocked_credentials',astra_authorized=False)
        self.post('/api/tasks/'+task['id']+'/resume',{},400)
        resumed=self.post('/api/tasks/'+task['id']+'/resume',{'astra_authorized':True})
        self.assertTrue(resumed['astra_authorized'])
        self.assertFalse(any(e['action']=='model_request' for e in self.engine.store.events()))

    def test_fallback_effort_validation_is_independent(self):
        fallback={'provider':'openai','model':'gpt-6.1-terra','reasoning_effort':'none'}
        agent=self.post('/api/agents/engineering',{'model':'gpt-6.1-sol','reasoning_effort':'medium','fallbacks':[fallback]})
        self.assertEqual(agent['fallbacks'],[fallback])
        self.post('/api/agents/engineering',{'fallbacks':[dict(fallback,reasoning_effort='unsupported')]},400)
        self.post('/api/agents/engineering',{'fallbacks':[dict(fallback,astra_authorized=True)]},400)

    def test_static_assets_csp_and_unknown_resources(self):
        for path, mime in [('/', 'text/html'), ('/app.js', 'text/javascript'), ('/styles.css', 'text/css')]:
            with self.subTest(path=path):
                code, content, headers = self.request('GET', path)
                self.assertEqual(code, 200)
                self.assertTrue(content)
                self.assertTrue(headers['Content-Type'].startswith(mime))
                self.assertIn("script-src 'self'", headers['Content-Security-Policy'])
                self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
                self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
                self.assertEqual(headers['X-Frame-Options'], 'DENY')
        for path in ['/../genesis/server.py', '/%2e%2e/genesis/server.py', '/api/nope', '/api/tasks/missing', '/api/artifacts/missing', '/.env']:
            with self.subTest(path=path):
                self.assertEqual(self.request('GET', path)[0], 404)
        self.post('/api/nope', {}, 404)

    def test_malformed_or_oversize_request_bodies(self):
        headers = {'X-Genesis-CSRF': self.token, 'Content-Type': 'application/json'}
        for raw in [b'{broken', b'[]', b'null']:
            with self.subTest(raw=raw):
                self.assertEqual(self.request('POST', '/api/settings', headers=headers, raw=raw)[0], 400)
        self.assertEqual(self.request('POST', '/api/settings', headers=headers, raw=b'')[0], 413)
        self.assertEqual(self.request('POST', '/api/settings', headers={**headers, 'Content-Length': '131073'}, raw=b'{}')[0], 413)
        self.assertEqual(self.request('POST', '/api/settings', headers={**headers, 'Content-Type': 'text/plain'}, raw=b'{}')[0], 415)


if __name__ == '__main__':
    unittest.main()
