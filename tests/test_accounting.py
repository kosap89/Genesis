"""Engine accounting regressions; all model replies/transports are labeled test doubles."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from genesis.engine import Engine
from genesis.providers import DEFAULT_MODELS, ProviderError, ProviderResult, ProviderRouter


class CallbackRouterDouble:
    def __init__(self, callback):
        self.callback = callback
        self.requests = []

    def generate(self, messages, tools, config):
        self.requests.append((messages, tools, config))
        return self.callback(messages, tools, config)


class AccountingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def engine(self, router):
        engine = Engine(self.root / 'state', self.source, router)
        self.addCleanup(engine.close)
        return engine

    def request_reserve(self, engine, task):
        return next(e['reserved_usd'] for e in engine.store.events(task['id']) if e['action'] == 'model_request')

    def assert_settled(self, engine, task, amount):
        self.assertAlmostEqual(engine.settings()['reserved_usd'], 0)
        self.assertAlmostEqual(engine.settings()['spent_usd'], amount)
        self.assertAlmostEqual(engine.store.get('tasks', task['id'])['cost_usd'], amount)

    def test_all_fallback_candidates_reserved_before_any_transport(self):
        def missing(*args):
            raise ProviderError('missing API key')
        router = CallbackRouterDouble(missing)
        engine = self.engine(router)
        baseline = engine.create_task('Measure one request')
        engine.run(baseline['id'])
        single_reserve = self.request_reserve(engine, baseline)
        self.assertGreater(single_reserve, 0)
        engine.store.update('agents', 'coo', fallbacks=[{'provider': 'anthropic'}, {'provider': 'gemini'}])
        engine.store.update('settings', 'global', budget_usd=single_reserve * 1.5)
        task = engine.create_task('Measure all requests')
        before = len(router.requests)
        engine.run(task['id'])
        self.assertEqual(len(router.requests), before)
        self.assertEqual(engine.store.get('tasks', task['id'])['status'], 'blocked_budget')
        self.assert_settled(engine, task, 0)

    def test_successful_fallback_charges_prior_unknown_attempt_ceiling(self):
        transports = []
        def transport(url, headers, payload, timeout, limit):
            transports.append(payload)
            if len(transports) == 1:
                raise ProviderError('Provider connection failed or timed out')
            return {'content': [{'type': 'text', 'text': 'Verified test-double fallback'}], 'stop_reason': 'end_turn',
                    'usage': {'input_tokens': 10, 'output_tokens': 20}}
        os.environ['GENESIS_OPENAI_API_KEY'] = 'test-openai'
        os.environ['GENESIS_ANTHROPIC_API_KEY'] = 'test-anthropic'
        engine = self.engine(ProviderRouter(transport=transport))
        engine.store.update('agents', 'coo', fallbacks=[{'provider': 'anthropic'}])
        task = engine.create_task('Fallback accounting')
        engine.run(task['id'])
        self.assertEqual(len(transports), 2)
        self.assertEqual(engine.store.get('tasks', task['id'])['status'], 'completed')
        ceiling = self.request_reserve(engine, task) / 2
        agent = engine.store.get('agents', 'coo')
        measured = (10 * agent['input_cost_per_million'] + 20 * agent['output_cost_per_million']) / 1e6
        self.assert_settled(engine, task, ceiling + measured)

    def test_unknown_provider_exception_retains_one_request_ceiling(self):
        def unknown(*args):
            raise RuntimeError('Unknown transport outcome from test double')
        engine = self.engine(CallbackRouterDouble(unknown))
        task = engine.create_task('Unknown provider failure')
        engine.run(task['id'])
        self.assertEqual(engine.store.get('tasks', task['id'])['status'], 'failed')
        self.assert_settled(engine, task, self.request_reserve(engine, task))

    def test_no_credentials_never_transports_or_charges(self):
        def forbidden(*args):
            self.fail('A transport was invoked without credentials')
        engine = self.engine(ProviderRouter(transport=forbidden))
        engine.store.update('agents', 'coo', fallbacks=[{'provider': 'anthropic'}, {'provider': 'gemini'}])
        task = engine.create_task('Credentials required')
        engine.run(task['id'])
        self.assertEqual(engine.store.get('tasks', task['id'])['status'], 'blocked_credentials')
        self.assert_settled(engine, task, 0)

    def test_cancelled_inflight_response_is_settled_without_completion(self):
        task_holder = {}
        def cancel_during_request(*args):
            engine.cancel(task_holder['task']['id'])
            return ProviderResult('Late test-double response', [], 10, 20, 'openai', 'test-model')
        engine = self.engine(CallbackRouterDouble(cancel_during_request))
        task = engine.create_task('Cancel model in flight')
        task_holder['task'] = task
        engine.run(task['id'])
        final = engine.store.get('tasks', task['id'])
        self.assertEqual(final['status'], 'cancelled')
        self.assertEqual(final['result'], '')
        self.assertFalse((engine.workspace(task) / 'GENESIS_RESULT.md').exists())
        actions = [e['action'] for e in engine.store.events(task['id'])]
        self.assertNotIn('task_completed', actions)
        self.assertIn('cancelled_request_settled', actions)
        self.assertGreater(final['cost_usd'], 0)
        self.assert_settled(engine, task, final['cost_usd'])

    def test_provider_override_uses_its_default_model(self):
        engine = self.engine(CallbackRouterDouble(lambda *args: self.fail('No request expected')))
        for provider in ('anthropic', 'gemini'):
            with self.subTest(provider=provider):
                task = engine.create_task('Use another provider', provider=provider)
                self.assertEqual(task['model'], DEFAULT_MODELS[provider])
                explicit = engine.create_task('Use explicit model', provider=provider, model='chosen-model')
                self.assertEqual(explicit['model'], 'chosen-model')


if __name__ == '__main__':
    unittest.main()
