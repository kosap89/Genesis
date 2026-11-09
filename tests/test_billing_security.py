"""Admin/model separation probes; no HTTP or model inference occurs."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from genesis.engine import Engine
from genesis.providers import KEY_NAMES, ProviderError, ProviderRouter, _key, provider_status
from genesis.toolbox import Toolbox, ToolContext


class BillingCredentialSecurityTests(unittest.TestCase):
    def test_selected_admin_environment_key_does_not_fall_through(self):
        with patch.dict(os.environ, {'GENESIS_OPENAI_API_KEY': 'sk-admin-test-only',
                                     'OPENAI_API_KEY': 'sk-proj-test-only'}, clear=True):
            self.assertEqual(_key('openai', {}), '')
            self.assertFalse(next(p for p in provider_status() if p['provider'] == 'openai')['configured'])
            transport = Mock(side_effect=AssertionError('Model transport forbidden'))
            with self.assertRaises(ProviderError) as caught:
                ProviderRouter(transport).generate([], [], {'provider': 'openai'})
            self.assertEqual(caught.exception.billable_attempts, 0)
            self.assertNotIn('sk-admin-test-only', str(caught.exception))
            transport.assert_not_called()

    def test_admin_config_key_cannot_reach_any_provider(self):
        for provider, variables in KEY_NAMES.items():
            with self.subTest(provider=provider), patch.dict(os.environ, {variables[0]: 'ordinary-test-only'}, clear=True):
                transport = Mock(side_effect=AssertionError('Model transport forbidden'))
                config = {'provider': provider, 'api_key': 'sk-admin-test-only'}
                self.assertEqual(_key(provider, config), '')
                with self.assertRaises(ProviderError) as caught:
                    ProviderRouter(transport).generate([], [], config)
                self.assertEqual(caught.exception.billable_attempts, 0)
                self.assertNotIn('sk-admin-test-only', str(caught.exception))
                transport.assert_not_called()

    def test_ordinary_key_precedence_preserved_without_requests(self):
        with patch.dict(os.environ, {'GENESIS_OPENAI_API_KEY': 'sk-proj-first-test-only',
                                     'OPENAI_API_KEY': 'sk-proj-second-test-only'}, clear=True):
            self.assertEqual(_key('openai', {}), 'sk-proj-first-test-only')
            self.assertEqual(_key('openai', {'api_key': 'sk-proj-config-test-only'}), 'sk-proj-config-test-only')
            self.assertTrue(next(p for p in provider_status() if p['provider'] == 'openai')['configured'])

    def test_agent_tools_do_not_expose_billing_administration(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            engine = Engine(root / 'state', root, ProviderRouter(Mock(side_effect=AssertionError('No inference'))))
            try:
                task = engine.create_task('Inspect schemas locally without execution')
                tools = engine.core_schemas(task) + Toolbox(ToolContext(root / 'workspace', root)).schemas()
                names = [tool['name'].lower() for tool in tools]
                self.assertFalse(any('billing' in name or 'admin' in name for name in names))
                self.assertNotIn('admin_api_key', json.dumps(tools))
                self.assertNotIn('billing', task.get('agent_config', {}))
            finally:
                engine.close()
