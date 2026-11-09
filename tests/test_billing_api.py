"""Loopback billing API tests with fake Admin keys and mocked provider HTTP only."""
import json
import os
import unittest
from unittest.mock import patch

import test_server as server_fixture


class BillingAPITests(unittest.TestCase):
    setUp = server_fixture.ServerTests.setUp
    stop_server = server_fixture.ServerTests.stop_server
    request = server_fixture.ServerTests.request
    post = server_fixture.ServerTests.post

    def test_session_key_is_separate_and_never_serialized_or_persisted(self):
        secret = 'sk-admin-fake-local-test'
        original = self.engine.state()
        with patch.dict(os.environ, {'GENESIS_OPENAI_API_KEY': 'ordinary-model-test'}):
            response = self.post('/api/billing/credentials', {'admin_api_key': secret})
            self.assertTrue(response['credential_configured'])
            self.assertEqual(os.environ['GENESIS_OPENAI_API_KEY'], 'ordinary-model-test')
            self.post('/api/credentials', {'provider': 'openai', 'api_key': secret}, 400)
            self.post('/api/billing/credentials', {'admin_api_key': 'ordinary-model-test'}, 400)
            self.post('/api/billing/credentials', {'admin_api_key': 'sk-proj-test'}, 400)
        _, state, _ = self.request('GET', '/api/state')
        self.assertNotIn(secret, json.dumps(state))
        self.assertEqual(state['settings'], original['settings'])
        self.assertEqual(state['tasks'], original['tasks'])
        self.assertNotIn(secret.encode(), self.engine.store.path.read_bytes())
        self.assertFalse(hasattr(self.engine, 'billing'))
        cleared = self.post('/api/billing/credentials', {'clear': True})
        self.assertFalse(cleared['credential_configured'])
        self.assertFalse(self.server.billing.credential_matches(secret))

    def test_get_and_settings_never_fetch_or_change_budget(self):
        original = self.engine.state()
        with patch.object(self.server.billing, 'transport', side_effect=AssertionError('No HTTP allowed')):
            _, billing, headers = self.request('GET', '/api/billing')
            self.assertFalse(billing['credential_configured'])
            self.assertIsNone(billing['report'])
            self.assertFalse(billing['prepaid']['supported'])
            self.assertIsNone(billing['prepaid']['balance'])
            self.assertEqual(headers['Cache-Control'], 'no-store')
            self.post('/api/billing/refresh', {}, 400)
            self.post('/api/billing/settings', {'refresh_interval_seconds': 899}, 400)
            self.post('/api/billing/settings', {'refresh_interval_seconds': 86401}, 400)
            self.post('/api/billing/settings', {'refresh_interval_seconds': 0, 'include_usage': False})
        current = self.engine.state()
        self.assertEqual(current['settings'], original['settings'])
        self.assertEqual(current['tasks'], original['tasks'])
        self.assertEqual(current['ventures'], original['ventures'])

    def test_credential_mutations_require_csrf(self):
        status, _, _ = self.request('POST', '/api/billing/credentials',
            raw=json.dumps({'admin_api_key': 'sk-admin-test'}).encode(),
            headers={'Content-Type': 'application/json'})
        self.assertEqual(status, 403)
        self.assertFalse(self.server.billing.state()['credential_configured'])


if __name__ == '__main__':
    unittest.main()
