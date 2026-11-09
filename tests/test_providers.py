"""Wire tests use a local HTTP test double, never a paid provider account."""
import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from genesis.providers import ProviderError, ProviderRouter, provider_status


TOOL = {"name": "lookup", "description": "Look up an item", "parameters": {"type": "object", "properties": {"id": {"type": "string"}}}}


class ProviderWireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        owner = cls
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                owner.requests.append((self.path, dict(self.headers), json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
                self.send_response(owner.status)
                self.end_headers()
                self.wfile.write(owner.response)
            def log_message(self, *args):
                pass
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        type(self).requests, type(self).status = [], 200
        self.router = ProviderRouter()
        for adapter in self.router.adapters.values():
            adapter.endpoint = f"http://127.0.0.1:{self.server.server_port}/generate"
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def respond(self, value):
        type(self).response = json.dumps(value).encode()

    def generate(self, provider, messages=None):
        return self.router.generate(messages or [{"role": "system", "content": "Be useful"}, {"role": "user", "content": "Find x"}], [TOOL], {"provider": provider, "api_key": "test-only-secret"})

    def test_openai_native_tool_round_trip_and_usage(self):
        self.respond({"status": "completed", "output": [{"type": "function_call", "call_id": "c1", "name": "lookup", "arguments": '{"id":"x"}'}], "usage": {"input_tokens": 12, "output_tokens": 8}})
        result = self.generate("openai")
        self.assertEqual(result.tool_calls[0]["arguments"], {"id": "x"})
        self.assertEqual((result.input_tokens, result.output_tokens), (12, 8))
        payload = self.requests[-1][2]
        self.assertFalse(payload["store"])
        self.assertEqual(payload["tools"][0]["type"], "function")
        self.respond({"output": [{"type": "message", "content": [{"type": "output_text", "text": "Done"}]}]})
        result2 = self.generate("openai", [{"role": "user", "content": "Find x"}, {"role": "assistant", "content": "", "tool_calls": result.tool_calls, "provider_data": result.provider_data}, {"role": "tool", "tool_call_id": "c1", "content": "Found"}])
        self.assertEqual(result2.text, "Done")
        self.assertEqual(self.requests[-1][2]["input"][-1], {"type": "function_call_output", "call_id": "c1", "output": "Found"})

    def test_anthropic_parallel_results_grouped(self):
        self.respond({"stop_reason": "tool_use", "content": [{"type": "tool_use", "id": "a", "name": "lookup", "input": {"id": "x"}}], "usage": {"input_tokens": 4, "output_tokens": 5}})
        result = self.generate("anthropic")
        self.assertEqual(result.tool_calls[0]["id"], "a")
        self.assertEqual(self.requests[-1][2]["system"], "Be useful")
        self.respond({"stop_reason": "end_turn", "content": [{"type": "text", "text": "Done"}]})
        calls = [{"id": x, "name": "lookup", "arguments": {}} for x in ("a", "b")]
        self.generate("anthropic", [{"role": "user", "content": "find"}, {"role": "assistant", "content": "", "tool_calls": calls}, {"role": "tool", "tool_call_id": "a", "content": "A"}, {"role": "tool", "tool_call_id": "b", "content": "B"}])
        history = self.requests[-1][2]["messages"]
        self.assertEqual(len(history[-1]["content"]), 2)
        self.assertEqual(history[-1]["role"], "user")

    def test_gemini_signature_round_trip_and_thinking_usage(self):
        self.respond({"candidates": [{"finishReason": "STOP", "content": {"parts": [{"functionCall": {"id": "g1", "name": "lookup", "args": {"id": "x"}}, "thoughtSignature": "opaque-signature"}]}}], "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 3, "thoughtsTokenCount": 4}})
        result = self.generate("gemini")
        self.assertEqual(result.output_tokens, 7)
        self.respond({"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "Done"}]}}]})
        self.generate("gemini", [{"role": "user", "content": "find"}, {"role": "assistant", "content": "", "tool_calls": result.tool_calls, "provider_data": result.provider_data}, {"role": "tool", "tool_call_id": "g1", "content": "Found"}])
        history = self.requests[-1][2]["contents"]
        self.assertEqual(history[1]["parts"][0]["thoughtSignature"], "opaque-signature")
        self.assertEqual(history[2]["parts"][0]["functionResponse"]["name"], "lookup")

    def test_missing_credentials_explicit_and_status_secret_free(self):
        with self.assertRaisesRegex(ProviderError, "missing API key") as caught:
            self.router.generate([], [], {"provider": "openai"})
        self.assertEqual(caught.exception.billable_attempts, 0)
        self.assertFalse(any(p["configured"] for p in provider_status()))
        os.environ["GENESIS_OPENAI_API_KEY"] = "secret"
        self.assertTrue(provider_status()[0]["configured"])
        self.assertNotIn("secret", json.dumps(provider_status()))
        self.assertEqual(len(self.requests), 0)

    def test_http_error_has_no_secret_and_no_retry(self):
        type(self).status, type(self).response = 401, b'{"error":"test-only-secret"}'
        with self.assertRaises(ProviderError) as caught:
            self.generate("openai")
        self.assertIn("401", str(caught.exception))
        self.assertNotIn("test-only-secret", str(caught.exception))
        self.assertEqual(caught.exception.billable_attempts, 1)
        self.assertEqual(len(self.requests), 1)

    def test_invalid_json_and_bounded_response(self):
        type(self).response = b"not json"
        with self.assertRaisesRegex(ProviderError, "invalid JSON"):
            self.generate("openai")
        type(self).response = b"x" * 100
        self.router.max_response_bytes = 10
        with self.assertRaisesRegex(ProviderError, "size limit"):
            self.generate("openai")

    def test_malformed_arguments_never_become_executable_calls(self):
        self.respond({"output": [{"type": "function_call", "call_id": "x", "name": "lookup", "arguments": "not-json"}]})
        with self.assertRaisesRegex(ProviderError, "malformed function arguments"):
            self.generate("openai")

    def test_explicit_fallback_and_key_isolation(self):
        os.environ["GENESIS_ANTHROPIC_API_KEY"] = "anthropic-test-key"
        self.respond({"content": [{"type": "text", "text": "Fallback"}], "stop_reason": "end_turn"})
        result = self.router.generate([{"role": "user", "content": "Hello"}], [], {"provider": "openai", "fallbacks": [{"provider": "anthropic"}]})
        self.assertEqual(result.provider, "anthropic")
        self.assertEqual(result.provider_data["_prior_billable_attempts"], 0)
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(self.requests[-1][1]["X-Api-Key"], "anthropic-test-key")

    def test_fallback_counts_prior_unknown_billing_outcome(self):
        def transport(url, headers, payload, timeout, limit):
            if "Authorization" in headers:
                raise ProviderError("Provider connection failed or timed out")
            return {"content": [{"type": "text", "text": "Success"}], "stop_reason": "end_turn"}
        self.router.transport = transport
        os.environ["GENESIS_ANTHROPIC_API_KEY"] = "test-anthropic"
        result = self.router.generate([{"role": "user", "content": "Hello"}], [], {"provider": "openai", "api_key": "test-openai", "fallbacks": [{"provider": "anthropic"}]})
        self.assertEqual(result.provider_data["_prior_billable_attempts"], 1)

    def test_all_failed_transports_counted_even_when_keys_missing(self):
        def transport(*args):
            raise ProviderError("Provider connection failed or timed out")
        self.router.transport = transport
        os.environ["GENESIS_GEMINI_API_KEY"] = "test-gemini"
        with self.assertRaises(ProviderError) as caught:
            self.router.generate([], [], {"provider": "openai", "api_key": "test-openai", "fallbacks": [{"provider": "anthropic"}, {"provider": "gemini"}]})
        self.assertEqual(caught.exception.billable_attempts, 2)

    def test_request_translation_failure_not_counted_as_billable(self):
        with self.assertRaises(ProviderError) as caught:
            self.generate("gemini", [{"role": "tool", "tool_call_id": "missing", "content": "result"}])
        self.assertEqual(caught.exception.billable_attempts, 0)
        self.assertEqual(len(self.requests), 0)

    def test_malformed_usage_rejected_for_each_provider_and_counted_as_attempt(self):
        examples = {
            'openai': ({'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': 'Untrusted usage'}]}]}, 'usage', ('input_tokens', 'output_tokens')),
            'anthropic': ({'content': [{'type': 'text', 'text': 'Untrusted usage'}], 'stop_reason': 'end_turn'}, 'usage', ('input_tokens', 'output_tokens')),
            'gemini': ({'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': 'Untrusted usage'}]}}]}, 'usageMetadata', ('promptTokenCount', 'candidatesTokenCount', 'thoughtsTokenCount')),
        }
        for provider, (base, usage_key, fields) in examples.items():
            for field in fields:
                for invalid in (-1, -0.5, 1.5, True, False, '12', None, [], {}):
                    with self.subTest(provider=provider, field=field, invalid=invalid):
                        # Positive siblings must never mask a negative component.
                        self.respond({**base, usage_key: {**{f: 10 for f in fields}, field: invalid}})
                        with self.assertRaisesRegex(ProviderError, 'nonnegative integers') as caught:
                            self.generate(provider)
                        self.assertEqual(caught.exception.billable_attempts, 1)
            for invalid in (None, [], 'usage'):
                with self.subTest(provider=provider, invalid_usage=invalid):
                    self.respond({**base, usage_key: invalid})
                    with self.assertRaisesRegex(ProviderError, 'invalid token usage'):
                        self.generate(provider)

    def test_invalid_usage_fallback_retains_prior_billable_attempt(self):
        def transport(url, headers, payload, timeout, limit):
            if 'Authorization' in headers:
                return {'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': 'Bad usage'}]}], 'usage': {'input_tokens': -200, 'output_tokens': 10}}
            return {'content': [{'type': 'text', 'text': 'Valid usage'}], 'usage': {'input_tokens': 20, 'output_tokens': 5}}
        self.router.transport = transport
        os.environ['GENESIS_ANTHROPIC_API_KEY'] = 'test-key'
        result = self.router.generate([{'role': 'user', 'content': 'Hi'}], [], {'provider': 'openai', 'api_key': 'test-key', 'fallbacks': [{'provider': 'anthropic'}]})
        self.assertEqual((result.input_tokens, result.output_tokens), (20, 5))
        self.assertEqual(result.provider_data['_prior_billable_attempts'], 1)

    def test_openai_encrypted_reasoning_replayed_without_duplication(self):
        output = [{'type': 'reasoning', 'id': 'reasoning-id', 'summary': [], 'encrypted_content': 'opaque-encrypted-state'},
                  {'type': 'function_call', 'call_id': 'r1', 'name': 'lookup', 'arguments': '{"id":"x"}'}]
        self.respond({'status': 'completed', 'output': output, 'usage': {'input_tokens': 0, 'output_tokens': 0}})
        result = self.generate('openai')
        self.assertEqual(result.provider_data['openai_output'], output)
        self.assertEqual((result.input_tokens, result.output_tokens), (0, 0))
        self.respond({'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': 'Done'}]}]})
        self.generate('openai', [{'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': '', 'tool_calls': result.tool_calls, 'provider_data': result.provider_data}, {'role': 'tool', 'tool_call_id': 'r1', 'content': 'Found'}])
        payload = self.requests[-1][2]
        self.assertIn('reasoning.encrypted_content', payload['include'])
        self.assertEqual(payload['input'][1:3], output)
        self.assertEqual(len([i for i in payload['input'] if i.get('type') == 'function_call']), 1)

    def test_usage_completeness_requires_both_reported_totals(self):
        examples = {
            'openai': ({'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': 'Valid text'}]}]}, 'usage', ('input_tokens', 'output_tokens')),
            'anthropic': ({'content': [{'type': 'text', 'text': 'Valid text'}]}, 'usage', ('input_tokens', 'output_tokens')),
            'gemini': ({'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': 'Valid text'}]}}]}, 'usageMetadata', ('promptTokenCount', 'candidatesTokenCount')),
        }
        for provider, (base, usage_key, fields) in examples.items():
            for supplied in ({}, {fields[0]: 12}, {fields[1]: 12}, {fields[0]: 0, fields[1]: 0}, {fields[0]: 12, fields[1]: 5}):
                with self.subTest(provider=provider, usage=supplied):
                    self.respond({**base, usage_key: supplied})
                    result = self.generate(provider)
                    self.assertEqual(result.provider_data['usage_complete'], all(f in supplied for f in fields))
                    self.assertEqual(result.input_tokens, supplied.get(fields[0], 0))
                    self.assertEqual(result.output_tokens, supplied.get(fields[1], 0))
            with self.subTest(provider=provider, usage='omitted'):
                self.respond(base)
                self.assertFalse(self.generate(provider).provider_data['usage_complete'])

    def test_incomplete_output_is_not_reported_as_success(self):
        self.respond({"status": "incomplete", "output": [{"type": "function_call", "call_id": "x", "name": "lookup", "arguments": "{}"}]})
        with self.assertRaisesRegex(ProviderError, "did not complete"):
            self.generate("openai")

    def test_modern_reasoning_and_usage_details_preserve_output_total(self):
        usage = {"input_tokens": 100, "output_tokens": 40,
                 "input_tokens_details": {"cached_tokens": 80}, "output_tokens_details": {"reasoning_tokens": 25}}
        self.respond({"output": [{"type": "message", "content": [{"type": "output_text", "text": "Done"}]}], "usage": usage})
        result = self.router.generate([], [], {"provider": "openai", "model": "gpt-6.1-terra", "reasoning_effort": "medium", "api_key": "test-only"})
        self.assertEqual(self.requests[-1][2]["reasoning"], {"effort": "medium"})
        self.assertNotIn("temperature", self.requests[-1][2])
        self.assertEqual((result.input_tokens, result.output_tokens), (100, 40))
        self.assertEqual(result.provider_data["cached_input_tokens"], 80)
        self.assertEqual(result.provider_data["reasoning_output_tokens"], 25)
        self.assertEqual(result.provider_data["raw_usage"], usage)

    def test_legacy_and_custom_models_do_not_receive_reasoning(self):
        self.respond({"output": [{"type": "message", "content": [{"type": "output_text", "text": "Done"}]}]})
        for model in ("gpt-4.1", "custom-model"):
            self.router.generate([], [], {"model": model, "api_key": "test-only", "temperature": .2})
            self.assertNotIn("reasoning", self.requests[-1][2])
            self.assertEqual(self.requests[-1][2]["temperature"], .2)

    def test_openai_missing_usage_details_remain_unknown(self):
        for extra, expected in (({}, None), ({"input_tokens_details": {}, "output_tokens_details": {}}, None),
                                ({"input_tokens_details": {"cached_tokens": 0},
                                  "output_tokens_details": {"reasoning_tokens": 0}}, 0)):
            usage = {"input_tokens": 10, "output_tokens": 4, **extra}
            self.respond({"output": [{"type": "message", "content": [{"type": "output_text", "text": "Done"}]}], "usage": usage})
            with self.subTest(extra=extra):
                result = self.generate("openai")
                self.assertEqual(result.provider_data["cached_input_tokens"], expected)
                self.assertEqual(result.provider_data["reasoning_output_tokens"], expected)
                self.assertEqual(result.provider_data["raw_usage"], usage)
                self.assertEqual((result.input_tokens, result.output_tokens), (10, 4))

    def test_invalid_fallback_prevents_all_transport(self):
        for fallback in ({"model": "gpt-6-astra"}, {"model": "gpt-6.1-sol", "reasoning_effort": "none"},
                         {"provider": "anthropic", "reasoning_effort": "high"}):
            with self.subTest(fallback=fallback), self.assertRaises(ProviderError) as caught:
                self.router.generate([], [], {"api_key": "test-only", "fallbacks": [fallback]})
            self.assertEqual(caught.exception.billable_attempts, 0)
        self.assertEqual(self.requests, [])
        # Shared legacy temperature must be checked on the effective modern route
        # before even the valid primary can incur a charge.
        with self.assertRaisesRegex(ProviderError, "Temperature") as caught:
            self.router.generate([], [], {"model": "gpt-4.1", "temperature": .5, "api_key": "test-only",
                                         "fallbacks": [{"model": "gpt-6-luna"}]})
        self.assertEqual(caught.exception.billable_attempts, 0)
        self.assertEqual(self.requests, [])

    def test_fallback_wire_effort_uses_its_own_default(self):
        requests = []
        def transport(url, headers, payload, *args):
            requests.append(payload)
            if len(requests) == 1:
                raise ProviderError("test-only failure")
            return {"output": [{"type": "message", "content": [{"type": "output_text", "text": "Done"}]}]}
        self.router.transport = transport
        self.router.generate([], [], {"api_key": "test-only", "reasoning_effort": "high",
            "fallbacks": [{"model": "gpt-6-luna", "api_key": "test-only"}]})
        self.assertEqual([p["reasoning"]["effort"] for p in requests], ["high", "low"])

    def test_astra_snapshot_cannot_bypass_authorization_before_transport(self):
        model = "gpt-6-astra-2026-11-01"
        for route in ({"model": model}, {"fallbacks": [{"model": model}]},
                      {"fallbacks": [{"model": model, "astra_authorized": True}]}):
            with self.subTest(route=route), self.assertRaisesRegex(ProviderError, "CEO authorization") as caught:
                self.router.generate([], [], {"api_key": "test-only", **route})
            self.assertEqual(caught.exception.billable_attempts, 0)
        self.assertEqual(self.requests, [])
        for route in ({"model": model}, {"fallbacks": [{"model": model}]}):
            with self.subTest(authorized_route=route), self.assertRaisesRegex(ProviderError, "Unverified Astra snapshot") as caught:
                self.router.generate([], [], {"api_key": "test-only", "astra_authorized": True, **route})
            self.assertEqual(caught.exception.billable_attempts, 0)
        self.assertEqual(self.requests, [])

    def test_invalid_openai_usage_details_are_billable_failures(self):
        for details in ({"cached_tokens": -1}, {"cached_tokens": True}, {"cached_tokens": 11}, None):
            self.respond({"output": [{"type": "message", "content": [{"type": "output_text", "text": "Done"}]}],
                          "usage": {"input_tokens": 10, "output_tokens": 4, "input_tokens_details": details}})
            with self.subTest(details=details), self.assertRaises(ProviderError) as caught:
                self.generate("openai")
            self.assertEqual(caught.exception.billable_attempts, 1)


if __name__ == "__main__":
    unittest.main()
