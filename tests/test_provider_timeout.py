"""Bounded inference waits; HTTP responses and timeout failures are mocked only."""
import math
import unittest
from unittest.mock import Mock, patch

from genesis.providers import ProviderError, ProviderRouter


class ProviderTimeoutTests(unittest.TestCase):
    config = {'provider': 'openai', 'model': 'gpt-6.1-sol',
              'api_key': 'offline-test-key', 'fallbacks': []}

    @staticmethod
    def completed():
        return {'status': 'completed', 'output': [
            {'type': 'message', 'content': [{'type': 'output_text', 'text': 'OFFLINE RESPONSE'}]}],
            'usage': {'input_tokens': 12, 'output_tokens': 5}}

    def test_default_transport_receives_finite_180_second_bound(self):
        transport = Mock(return_value=self.completed())
        router = ProviderRouter(transport=transport)
        result = router.generate([{'role': 'user', 'content': 'Offline timeout check'}], [], self.config)
        self.assertEqual(result.text, 'OFFLINE RESPONSE')
        transport.assert_called_once()
        self.assertEqual(transport.call_args.args[3], 180)
        self.assertTrue(math.isfinite(transport.call_args.args[3]))
        self.assertEqual(transport.call_args.args[4], 4 * 1024 * 1024)

    def test_explicit_timeout_and_response_bound_are_preserved(self):
        transport = Mock(return_value=self.completed())
        router = ProviderRouter(transport=transport, timeout=7.5, max_response_bytes=2048)
        router.generate([], [], self.config)
        transport.assert_called_once()
        self.assertEqual(transport.call_args.args[3:], (7.5, 2048))

    def test_provider_failure_does_not_retry_and_preserves_billable_attempt(self):
        transport = Mock(side_effect=ProviderError('Offline transport timeout'))
        router = ProviderRouter(transport=transport)
        with self.assertRaises(ProviderError) as caught:
            router.generate([], [], self.config)
        transport.assert_called_once()
        self.assertEqual(caught.exception.billable_attempts, 1)
        self.assertIn('timeout', str(caught.exception))

    def test_default_http_timeout_is_safe_error_without_automatic_retry(self):
        opener = Mock()
        opener.open.side_effect = TimeoutError('sensitive transport diagnostic')
        with patch('genesis.providers.urllib.request.build_opener', return_value=opener):
            with self.assertRaises(ProviderError) as caught:
                ProviderRouter().generate([], [], self.config)
        opener.open.assert_called_once()
        self.assertEqual(opener.open.call_args.kwargs['timeout'], 180)
        self.assertEqual(caught.exception.billable_attempts, 1)
        self.assertNotIn('sensitive transport diagnostic', str(caught.exception))
        self.assertNotIn(self.config['api_key'], str(caught.exception))


if __name__ == '__main__':
    unittest.main()
