"""Explicit mocked provider transport and isolated loopback API; no live requests."""
import io
import json
import unittest
import urllib.error
from unittest.mock import patch, MagicMock
from genesis.providers import openai_model_availability
import test_server as _server_fixture

class AvailabilityTests(unittest.TestCase):
    def check(self, raw):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = raw
        opener = MagicMock()
        opener.open.return_value = response
        with patch('genesis.providers._key', return_value='sk-test-only'), patch('genesis.providers.urllib.request.build_opener', return_value=opener):
            result = openai_model_availability(['gpt-test', 'gpt-absent'])
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, 'https://api.openai.com/v1/models')
        self.assertEqual(request.get_method(), 'GET')
        self.assertIsNone(request.data)
        self.assertEqual(request.get_header('Authorization'), 'Bearer sk-test-only')
        self.assertEqual(opener.open.call_args.kwargs['timeout'], 10)
        response.__enter__.return_value.read.assert_called_once_with(2*1024*1024+1)
        self.assertNotIn('sk-test-only', json.dumps(result))
        return result

    def test_missing_key_makes_no_transport(self):
        with patch('genesis.providers._key', return_value=''), patch('genesis.providers.urllib.request.build_opener') as transport:
            result = openai_model_availability(['gpt-test'])
        transport.assert_not_called()
        self.assertEqual(result['status'], 'missing_credentials')
        self.assertFalse(result['checked'])
        self.assertIsNone(result['models'][0]['available'])

    def test_exact_ids_only_and_no_generation(self):
        result = self.check(b'{"data":[{"id":"gpt-test"}]}')
        self.assertTrue(result['checked'])
        self.assertFalse(result['generation_tested'])
        self.assertEqual([entry['available'] for entry in result['models']], [True, False])

    def test_response_limits_and_schema(self):
        for raw, status in [(b'x'*(2*1024*1024+1), 'response_too_large'), (b'not json', 'invalid_response'), (b'{"data":{}}', 'invalid_response'), (b'{"data":[{}]}', 'invalid_response')]:
            self.assertEqual(self.check(raw)['status'], status)

    def test_http_and_network_errors_never_echo_response(self):
        for code, status in [(401,'invalid_credentials'),(403,'http_error'),(302,'redirect_refused')]:
            error = urllib.error.HTTPError('https://api.openai.com/v1/models', code, 'sk-test-only', {}, io.BytesIO(b'sk-test-only'))
            with patch('genesis.providers._key', return_value='sk-test-only'), patch('genesis.providers.urllib.request.build_opener') as factory:
                factory.return_value.open.side_effect = error
                result = openai_model_availability(['gpt-test'])
                handler = factory.call_args.args[0]()
                self.assertIsNone(handler.redirect_request(None,None,302,None,None,'https://evil.invalid'))
            self.assertEqual(result['status'], status)
            self.assertNotIn('sk-test-only', json.dumps(result))
        with patch('genesis.providers._key', return_value='sk-test-only'), patch('genesis.providers.urllib.request.build_opener') as factory:
            factory.return_value.open.side_effect = urllib.error.URLError('sk-test-only')
            self.assertEqual(openai_model_availability([])['status'], 'connection_error')

    def test_model_validation_precedes_key_access(self):
        for models in ['gpt-test', [True], ['sk-secret'], ['a\nkey'], ['x']*51]:
            with patch('genesis.providers._key') as key, self.assertRaises(ValueError):
                openai_model_availability(models)
            key.assert_not_called()

class AvailabilityHTTPTests(unittest.TestCase):
    setUp = _server_fixture.ServerTests.setUp
    stop_server = _server_fixture.ServerTests.stop_server
    request = _server_fixture.ServerTests.request
    post = _server_fixture.ServerTests.post

    def test_guarded_endpoint_and_scoped_saved_models(self):
        venture = self.post('/api/ventures', {'name':'Test venture'}, 201)
        self.engine.teams.assign(venture['id'], 'coo')
        with patch('genesis.server.openai_model_availability', return_value=dict(status='missing_credentials', models=[{'id':'model-test','available':None}], checked=False, generation_tested=False)) as check:
            result = self.post('/api/providers/openai/check', {'venture_id':venture['id']})
        self.assertFalse(result['generation_tested'])
        self.assertIn(self.engine.teams.effective_agent('coo', venture['id'])['model'], check.call_args.args[0])
        self.assertEqual(self.engine.store.all('tasks'), [])
        self.assertTrue(any(event['action']=='provider_availability_checked' for event in self.engine.store.events()))
        with patch('genesis.server.openai_model_availability') as check:
            for body in [{'api_key':'never-read'}, {'venture_id':'missing'}, {'venture_id':None}]:
                self.post('/api/providers/openai/check', body, 400)
            code, _, _ = self.request('POST','/api/providers/openai/check',{},headers={'X-Genesis-CSRF':'invalid'})
            self.assertEqual(code,403)
            check.assert_not_called()

if __name__ == '__main__':
    unittest.main()
