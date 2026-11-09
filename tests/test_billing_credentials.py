"""Hidden console credential setup; all local HTTP and input are mocked."""
import argparse
import contextlib
import getpass
import io
import json
import unittest
from unittest.mock import Mock, patch

from genesis import billing_credentials as helper


class BillingCredentialHelperTests(unittest.TestCase):
    def invoke(self, responses, argv=None, key='sk-admin-fake-console-test'):
        output = io.StringIO()
        with patch.object(helper, 'request_json', side_effect=responses) as request, \
                patch.object(getpass, 'getpass', return_value=key) as prompt, \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            result = helper.main(argv or [])
        return result, output.getvalue(), request, prompt

    def test_hidden_key_sent_only_to_loopback_and_not_output(self):
        key = 'sk-admin-fake-console-test'
        result, output, request, prompt = self.invoke([
            {'csrf_token': 'local-csrf'}, {'credential_configured': True}])
        self.assertEqual(result, 0)
        prompt.assert_called_once()
        sent = request.call_args_list[1].args[1]
        self.assertEqual(sent.full_url, 'http://127.0.0.1:8787/api/billing/credentials')
        self.assertEqual(json.loads(sent.data), {'admin_api_key': key})
        self.assertEqual(sent.get_header('X-genesis-csrf'), 'local-csrf')
        self.assertNotIn(key, output)

    def test_clear_never_prompts(self):
        result, output, request, prompt = self.invoke([
            {'csrf_token': 'local-csrf'}, {'credential_configured': False}], ['--clear'])
        self.assertEqual(result, 0)
        prompt.assert_not_called()
        self.assertEqual(json.loads(request.call_args_list[1].args[1].data), {'clear': True})

    def test_loopback_secret_bypasses_environment_proxies(self):
        with patch.object(helper.urllib.request, 'build_opener') as factory:
            result, _, _, _ = self.invoke([
                {'csrf_token': 'token'}, {'credential_configured': True}])
        self.assertEqual(result, 0)
        handlers = factory.call_args.args
        self.assertIsInstance(handlers[0], helper.urllib.request.ProxyHandler)
        self.assertEqual(handlers[0].proxies, {})
        self.assertIs(handlers[1], helper.NoRedirect)

    def test_errors_and_ordinary_keys_never_echo_secret(self):
        key = 'sk-admin-fake-console-test'
        result, output, _, _ = self.invoke([{'csrf_token': 'token'}, ValueError(key)])
        self.assertEqual(result, 1)
        self.assertNotIn(key, output)
        result, output, request, _ = self.invoke([{'csrf_token': 'token'}], key='sk-proj-test')
        self.assertEqual(result, 1)
        self.assertEqual(request.call_count, 1)
        self.assertNotIn('sk-proj-test', output)

    def test_no_echo_fallback_when_hidden_input_unavailable(self):
        output = io.StringIO()
        with patch.object(helper, 'request_json', return_value={'csrf_token': 'token'}) as request, \
                patch.object(getpass, 'getpass', side_effect=getpass.GetPassWarning()), \
                contextlib.redirect_stderr(output):
            self.assertEqual(helper.main([]), 1)
        self.assertEqual(request.call_count, 1)

    def test_reject_remote_urls_and_redirects(self):
        for url in ['https://127.0.0.1:8787', 'http://example.com:8787',
                    'http://user:pass@localhost:8787', 'http://localhost:8787/path',
                    'http://localhost:8787?query=1', 'http://localhost']:
            with self.subTest(url=url), self.assertRaises(argparse.ArgumentTypeError):
                helper.local_url(url)
        self.assertEqual(helper.local_url('http://localhost:8787/'), 'http://localhost:8787')
        self.assertIsNone(helper.NoRedirect().redirect_request(None, None, 302, '', {}, 'http://example.com'))

    def test_response_size_and_shape_are_bounded(self):
        for payload in [b'[]', b'x' * (2 * 1024 * 1024 + 1)]:
            response = Mock()
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            response.read.return_value = payload
            opener = Mock()
            opener.open.return_value = response
            with self.assertRaises(ValueError):
                helper.request_json(opener, Mock())


if __name__ == '__main__':
    unittest.main()
