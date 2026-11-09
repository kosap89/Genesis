"""Deterministic organization billing tests; all HTTP is explicitly mocked."""
import json
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from genesis.billing import BillingService, BillingError
from genesis.store import Store

NOW = datetime(2026, 11, 9, 12, tzinfo=timezone.utc).timestamp()
DAY = int(datetime(2026, 11, 8, tzinfo=timezone.utc).timestamp())
KEY = 'sk-admin-unit-test-secret'


def page(rows=None, more=False, cursor=None):
    return {'data': [{'start_time': DAY, 'end_time': DAY+86400, 'results': rows or []}],
            'has_more': more, 'next_page': cursor}


def cost(value='1.25', **extra):
    return {'amount': {'value': value, 'currency': 'usd'}, 'project_id': 'proj_one', 'api_key_id': 'key_one', **extra}


class BillingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name)/'state.db')
        self.store.put('settings', {'id': 'global', 'spent_usd': 3.9, 'budget_usd': 8.4})
        self.now = NOW
        self.calls = []
        self.responses = []
        def transport(url, headers, timeout):
            self.calls.append((url, headers, timeout))
            response = self.responses.pop(0)
            if isinstance(response, Exception):
                raise response
            if callable(response):
                return response()
            return response
        self.service = BillingService(self.store, transport, lambda: self.now)
        self.addCleanup(self.service.close)

    def setup_key(self):
        self.service.set_credential(KEY)

    def refresh(self, costs=None, usage=None):
        self.responses += [costs or page([cost()]), usage or page([{'num_model_requests': 2, 'input_tokens': 4, 'output_tokens': 3, 'model': 'model-test'}])]
        return self.service.refresh()

    def test_no_requests_on_construction_configuration_or_credential(self):
        self.service.state()
        self.service.configure({'refresh_interval_seconds': 900})
        self.setup_key()
        self.assertEqual(self.calls, [])
        self.assertFalse(self.service.state()['prepaid']['supported'])
        self.assertIsNone(self.service.state()['prepaid']['balance'])

    def test_authentication_isolation_and_budget_preservation(self):
        self.setup_key()
        before = self.store.get('settings', 'global')
        state = self.refresh()
        self.assertEqual(state['report']['costs']['total'], 1.25)
        self.assertEqual(state['report']['costs']['daily'], {'2026-11-08': 1.25})
        self.assertEqual(state['report']['costs']['by_api_key'], {'key_one': 1.25})
        self.assertEqual(state['report']['usage']['requests'], 2)
        self.assertEqual(before, self.store.get('settings', 'global'))
        for url, headers, timeout in self.calls:
            self.assertTrue(url.startswith('https://api.openai.com/v1/organization/'))
            self.assertEqual(headers['Authorization'], 'Bearer '+KEY)
            self.assertLessEqual(timeout, 10)
            self.assertNotIn('/responses', url)
        self.assertNotIn(KEY, json.dumps(state))
        self.assertNotIn(KEY, json.dumps(self.store.all('billing_reports')))
        self.assertTrue(self.service.credential_matches(KEY))
        self.assertFalse(self.service.credential_matches('ordinary-key'))

    def test_cost_pagination_atomic_and_groups(self):
        self.setup_key()
        self.responses = [page([cost('0.1')], True, 'next'), page([cost('0.2', project_id='proj_two', api_key_id='key_two')]), page()]
        report = self.service.refresh()['report']
        self.assertEqual(report['costs']['total'], 0.3)
        self.assertEqual(report['costs']['by_project']['proj_two'], 0.2)
        self.assertEqual(parse_qs(urlparse(self.calls[1][0]).query)['page'], ['next'])

    def test_failed_page_preserves_last_success(self):
        self.setup_key()
        original = self.refresh()['report']
        self.now += 31
        self.responses = [page([cost()], True, 'next'), TimeoutError('contains '+KEY)]
        state = self.service.refresh()
        self.assertEqual(state['report'], original)
        self.assertEqual(state['last_successful_sync'], original['last_successful_sync'])
        self.assertTrue(state['stale'])
        self.assertNotIn(KEY, state['error'])

    def test_repeated_cursor_and_duplicate_rows_fail(self):
        self.setup_key()
        self.responses = [page([cost()], True, 'x'), page([cost('2')], True, 'x')]
        self.assertIsNone(self.service.refresh()['report'])
        self.now += 31
        self.responses = [page([cost(), cost()])]
        self.assertIn('Duplicate', self.service.refresh()['error'])

    def test_missing_amount_not_invented_zero(self):
        self.setup_key()
        state = self.refresh(page([cost(), {'amount': None}]))
        self.assertIsNone(state['report']['costs']['total'])
        self.assertEqual(state['report']['costs']['known_total'], 1.25)
        self.assertTrue(state['report']['partial'])

    def test_mixed_currencies_rejected(self):
        self.setup_key()
        self.responses = [page([cost(), cost(amount={'value': 2, 'currency': 'eur'})])]
        self.assertIn('Mixed', self.service.refresh()['error'])
        self.assertIsNone(self.service.state()['report'])

    def test_negative_provider_adjustments_and_finite_validation(self):
        self.setup_key()
        self.assertEqual(self.refresh(page([cost('-0.20')]))['report']['costs']['total'], -0.2)
        for invalid in [True, 'NaN', 'Infinity', '1e999']:
            self.now += 31
            self.responses = [page([cost(invalid)])]
            self.assertIn('Invalid monetary', self.service.refresh()['error'])

    def test_billing_error_secret_redacted_in_cost_and_usage_failures(self):
        self.setup_key()
        self.responses = [BillingError('Upstream echoed ' + KEY)]
        self.assertNotIn(KEY, json.dumps(self.service.refresh()))
        self.now += 31
        self.responses = [page([cost()]), BillingError('Upstream echoed ' + KEY)]
        state = self.service.refresh()
        self.assertNotIn(KEY, json.dumps(state))
        self.assertEqual(state['report']['costs']['total'], 1.25)
        self.assertFalse(state['report']['usage']['available'])

    def test_missing_required_usage_counters_are_not_invented_zero(self):
        self.setup_key()
        state = self.refresh(usage=page([{'num_model_requests': 2}]))
        self.assertFalse(state['report']['usage']['available'])
        self.assertNotIn('input_tokens', state['report']['usage'])
        self.assertEqual(state['report']['costs']['total'], 1.25)

    def test_usage_failure_does_not_hide_costs(self):
        self.setup_key()
        state = self.refresh(usage=PermissionError(KEY))
        self.assertEqual(state['report']['costs']['total'], 1.25)
        self.assertFalse(state['report']['usage']['available'])
        self.assertTrue(state['report']['partial'])
        self.assertNotIn(KEY, json.dumps(state))

    def test_cost_only_minimum_permissions(self):
        self.setup_key()
        self.service.configure({'include_usage': False})
        self.responses = [page([cost()])]
        state = self.service.refresh()
        self.assertEqual(len(self.calls), 1)
        self.assertFalse(state['report']['partial'])

    def test_failure_rate_limit_and_cooldown(self):
        self.setup_key()
        self.responses = [{'status': 429, 'body': {'error': KEY}}]
        self.assertIn('429', self.service.refresh()['error'])
        self.now += 31
        with self.assertRaises(ValueError):
            self.service.refresh()
        self.assertEqual(len(self.calls), 1)

    def test_pagination_page_bound_and_retry_after(self):
        self.setup_key()
        self.responses = [page([cost(str(i))], True, str(i)) for i in range(8)]
        self.assertIn('pagination limit', self.service.refresh()['error'])
        self.assertEqual(len(self.calls), 8)
        self.now += 31
        self.responses = [{'status': 429, 'headers': {'Retry-After': '9999999999999999'}, 'body': {}}]
        state = self.service.refresh()
        self.assertEqual(state['next_refresh_at'], self.now + 86400)

    def test_rotation_discards_inflight_old_report_and_clears_cache(self):
        self.setup_key()
        def rotate():
            self.service.set_credential('sk-admin-new-secret')
            return page([cost()])
        self.responses = [rotate, page()]
        self.assertIsNone(self.service.refresh()['report'])
        self.assertTrue(self.service.credential_matches('sk-admin-new-secret'))
        self.assertIsNone(BillingService(self.store, lambda *a: None).state()['report'])

    def test_clear_stops_periodic_and_inflight_publish(self):
        self.setup_key()
        self.service.configure({'refresh_interval_seconds': 900})
        def clear():
            self.service.set_credential('')
            return page([cost()])
        self.responses = [clear, page()]
        self.assertFalse(self.service.refresh()['credential_configured'])
        self.service.tick()
        self.assertEqual(len(self.calls), 2)
        self.assertIsNone(self.service.state()['report'])

    def test_month_rollover_and_stale_delay_labels(self):
        self.setup_key()
        self.refresh()
        self.now = datetime(2026, 12, 1, tzinfo=timezone.utc).timestamp()
        self.assertTrue(self.service.state()['stale'])
        self.assertTrue(self.service.state()['report']['delayed'])

    def test_periodic_disabled_by_default_and_configuration_bounds(self):
        self.setup_key()
        self.service.tick()
        self.assertEqual(self.calls, [])
        for value in [1, 899, 86401, True, '900']:
            with self.assertRaises(ValueError):
                self.service.configure({'refresh_interval_seconds': value})
        with self.assertRaises(ValueError):
            self.service.configure({'budget_usd': 100})

    def test_malformed_and_secret_echo_rejected(self):
        self.setup_key()
        for response in [page([cost(project_id=KEY)]), {'data': [{}]}, {'data': 'wrong'}]:
            self.responses = [response, page()]
            state = self.service.refresh()
            self.assertIsNone(state['report'])
            self.assertNotIn(KEY, json.dumps(state))
            self.now += 31

    def test_ordinary_key_rejected_and_row_types_validated(self):
        with self.assertRaises(ValueError):
            self.service.set_credential('sk-proj-ordinary')
        self.setup_key()
        self.responses = [page(['malformed'])]
        self.assertIn('Malformed', self.service.refresh()['error'])

    def test_no_key_no_request_and_close(self):
        with self.assertRaises(ValueError):
            self.service.refresh()
        self.setup_key()
        self.assertTrue(self.service.close())
        with self.assertRaises(ValueError):
            self.service.refresh()
        self.assertEqual(self.calls, [])

    def test_close_waits_for_manual_refresh_and_invalidates_publish(self):
        self.setup_key()
        entered, release = threading.Event(), threading.Event()
        def block():
            entered.set()
            release.wait(5)
            return page([cost()])
        self.responses = [block, page()]
        worker = threading.Thread(target=self.service.refresh)
        worker.start()
        self.assertTrue(entered.wait(1))
        started = time.monotonic()
        self.assertFalse(self.service.close())
        self.assertGreaterEqual(time.monotonic() - started, .9)
        release.set()
        worker.join(2)
        self.assertFalse(worker.is_alive())
        self.assertTrue(self.service.close())
        self.assertIsNone(self.service.state()['report'])
        self.assertFalse(self.store.get('billing_reports', 'openai').get('last_successful_sync'))

    def test_cached_report_is_historical_without_session_credential(self):
        self.setup_key()
        self.refresh()
        reloaded = BillingService(self.store, lambda *args: self.fail('Unexpected request'))
        self.addCleanup(reloaded.close)
        self.assertTrue(reloaded.state()['historical_snapshot'])
        self.assertFalse(self.service.state()['historical_snapshot'])

    def test_response_size_and_out_of_month_buckets_rejected(self):
        self.setup_key()
        self.responses = ['x' * (2*1024*1024+1)]
        self.assertIn('size', self.service.refresh()['error'])
        self.now += 31
        self.responses = [{'data': [{'start_time': 1, 'results': []}]}]
        self.assertIn('outside', self.service.refresh()['error'])


if __name__ == '__main__':
    unittest.main()
