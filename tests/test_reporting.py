"""Offline model-control/accounting regressions. All provider results are doubles."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from genesis.engine import Engine
from genesis.accounting import accounting_summary, estimate_cost, conservative_rates
from genesis.models import default_route
from genesis.providers import ProviderResult


class ResultDouble:
    def __init__(self, result=None):
        self.calls = []
        self.result = result or ProviderResult('LOCAL TEST DOUBLE', [], 10, 5, 'openai', 'gpt-6.1-sol',
                                             {'usage_complete': True, 'cached_input_tokens': 4, 'reasoning_output_tokens': 3})

    def generate(self, messages, tools, config):
        self.calls.append(config)
        return self.result


class ReportingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def engine(self, result=None):
        router = ResultDouble(result)
        engine = Engine(self.root / 'data', self.root, router)
        self.addCleanup(engine.close)
        return engine, router

    def test_new_role_defaults_and_existing_routes_survive_restart(self):
        engine, router = self.engine()
        for agent in engine.store.all('agents'):
            expected = default_route(agent['role'])
            self.assertEqual(agent['model'], expected['model'])
            self.assertEqual(agent['reasoning_effort'], expected['reasoning_effort'])
        engine.store.update('agents', 'engineering', model='gpt-4.1-mini', reasoning_effort=None)
        engine.store.update('agents', 'qa', reasoning_effort='high')
        task = engine.create_task('Preserve queued history')
        engine.close()
        reopened = Engine(self.root / 'data', self.root, router)
        self.addCleanup(reopened.close)
        self.assertEqual(reopened.store.get('agents', 'engineering')['model'], 'gpt-4.1-mini')
        self.assertEqual(reopened.store.get('agents', 'qa')['reasoning_effort'], 'high')
        self.assertEqual(reopened.store.get('tasks', task['id']), task)
        self.assertEqual(router.calls, [])

    def test_task_snapshots_effort_and_never_dispatches_astra_implicitly(self):
        engine, router = self.engine()
        task = engine.create_task('Snapshot effort', role='engineering')
        engine.store.update('agents', 'engineering', reasoning_effort='high')
        engine.run(task['id'])
        self.assertEqual(router.calls[0]['reasoning_effort'], 'medium')
        for args in ({'model':'gpt-6-astra'}, {'model':'gpt-6-astra','astra_authorized':1}):
            with self.assertRaises(ValueError):
                engine.create_task('No Astra permission', **args)
        self.assertEqual(len(router.calls), 1)
        engine.store.update('agents', 'coo', fallbacks=[{'provider':'openai','model':'gpt-6-astra'}])
        with self.assertRaises(ValueError):
            engine.create_task('No fallback permission')
        authorized = engine.create_task('Explicit Astra permission', astra_authorized=True)
        self.assertTrue(authorized['astra_authorized'])
        self.assertTrue(any(e['action']=='astra_authorized' for e in engine.store.events(authorized['id'])))

    def test_tampered_astra_task_still_fails_before_reserving(self):
        engine, router = self.engine()
        task = engine.create_task('Guard dispatch')
        engine.store.update('tasks', task['id'], model='gpt-6-astra')
        engine.run(task['id'])
        self.assertEqual(router.calls, [])
        self.assertEqual(engine.settings()['spent_usd'], 0)
        self.assertEqual(engine.settings()['reserved_usd'], 0)
        self.assertFalse(any(e['action']=='model_request' for e in engine.store.events(task['id'])))

    def test_cached_reasoning_usage_estimate_does_not_change_budget_ledger(self):
        engine, _ = self.engine()
        engine.store.update('agents', 'engineering', model='gpt-6.1-sol', reasoning_effort='medium')
        task = engine.create_task('Record fixture usage', role='engineering')
        engine.run(task['id'])
        report = engine.state()['accounting']
        self.assertEqual((report['input_tokens'],report['output_tokens']), (10,5))
        self.assertEqual((report['cached_input_tokens'],report['reasoning_output_tokens']), (4,3))
        self.assertAlmostEqual(report['estimated_cost_usd'], (6*2+4*.1+5*10)/1e6)
        self.assertAlmostEqual(report['conservative_charged_usd'], (10*10+5*30)/1e6)
        self.assertIsNone(report['official_billed_usd'])
        before = engine.settings().copy()
        engine.store.update('settings', 'global', pricing_overrides={'gpt-6.1-sol':{
            'input_cost_per_million':0,'cached_input_cost_per_million':0,'output_cost_per_million':0}})
        after = engine.state()['accounting']
        self.assertEqual(after['estimated_cost_usd'], 0)
        self.assertEqual(engine.settings()['spent_usd'], before['spent_usd'])
        next_task = engine.create_task('Zero report prices cannot permit excess spend', role='engineering')
        engine.store.update('settings', 'global', budget_usd=before['spent_usd'])
        engine.run(next_task['id'])
        self.assertEqual(engine.store.get('tasks',next_task['id'])['status'], 'blocked_budget')
        self.assertEqual(after['conservative_charged_usd'], before['spent_usd'])

    def test_historical_report_is_reconstructed_without_rewriting_spend(self):
        engine, _ = self.engine()
        engine.store.update('settings','global',spent_usd=3.91808)
        samples=[('gpt-4.1-mini',303225,12123),('gpt-4.1',47261,1651)]
        for model, inp, out in samples:
            task = engine.create_task('Historical fixture')
            engine.store.event('model_request',task['id'],provider='openai',model=model,reserved_usd=1)
            engine.store.event('model_response',task['id'],provider='openai',model=model,input_tokens=inp,output_tokens=out,cost_usd=1)
            engine.store.message(task['id'],{'role':'assistant','content':'HISTORICAL TEST DOUBLE','provider_data':{'usage_complete':True}})
        report=accounting_summary(engine.store)
        self.assertEqual(report['input_tokens'],350486)
        self.assertEqual(report['output_tokens'],13774)
        self.assertAlmostEqual(report['estimated_cost_usd'],.2484168)
        self.assertEqual(report['cache_usage_unknown_responses'],2)
        self.assertFalse(report['estimate_complete'])
        self.assertAlmostEqual(report['conservative_charged_usd'],3.91808)
        self.assertIsNone(report['official_billed_usd'])

    def test_estimate_is_local_and_cannot_create_work_or_reserve_budget(self):
        engine, router = self.engine()
        before=engine.settings().copy()
        preview=engine.estimate_task('A sufficiently concrete objective',role='engineering')
        self.assertEqual(preview['model'],'gpt-6.1-sol')
        self.assertGreater(preview['conservative_reservation_usd'],preview['estimated_call_cost_usd'])
        self.assertEqual(engine.store.all('tasks'),[])
        self.assertEqual(engine.settings(),before)
        self.assertEqual(router.calls,[])
        self.assertFalse((engine.root/'preview').exists())

    def test_published_long_context_estimates_and_expensive_routes_raise_guard(self):
        normal=estimate_cost('openai','gpt-6.1-sol',272000,100,1000)
        long=estimate_cost('openai','gpt-6.1-sol',272001,100,1000)
        self.assertAlmostEqual(normal,((271000*2+1000*.1)+100*10)/1e6)
        self.assertAlmostEqual(long,((271001*2+1000*.1)*2+100*10*1.5)/1e6)
        rates=conservative_rates(dict(provider='openai',model='gpt-6.1-sol',input_cost_per_million=10,output_cost_per_million=30,
                                     fallbacks=[{'provider':'openai','model':'gpt-6-astra'}]))
        self.assertEqual(rates,(20,75))
        self.assertIsNone(estimate_cost('openai','custom',100,20))

    def test_failed_fallback_attempt_cannot_look_like_complete_accounting(self):
        engine,_=self.engine(ProviderResult('FALLBACK TEST DOUBLE',[],10,5,'openai','gpt-6-luna',
                                         {'usage_complete':True,'cached_input_tokens':0,'_prior_billable_attempts':1}))
        task=engine.create_task('One logical request with a failed billable attempt')
        engine.run(task['id'])
        report=engine.state()['accounting']
        self.assertEqual(report['request_count'],1)
        self.assertEqual(report['known_billable_attempt_count'],2)
        self.assertEqual(report['unknown_usage_attempts'],1)
        self.assertFalse(report['estimate_complete'])
        self.assertGreater(report['conservative_charged_usd'],report['estimated_cost_usd'])

    def test_unknown_or_partial_usage_is_not_reported_as_verified_zero(self):
        engine,_=self.engine(ProviderResult('PARTIAL TEST DOUBLE',[],10,0,'openai','gpt-6.1-sol',{'usage_complete':False}))
        task=engine.create_task('Partial fixture')
        engine.run(task['id'])
        report=engine.state()['accounting']
        self.assertFalse(report['estimate_complete'])
        self.assertEqual(report['incomplete_usage_responses'],1)
        self.assertGreater(report['conservative_charged_usd'],0)


if __name__ == '__main__':
    unittest.main()
