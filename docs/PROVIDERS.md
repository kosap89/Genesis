# Model providers

Genesis makes real synchronous HTTPS requests using Python's standard library. It does not fabricate model output. The router supports OpenAI Responses, Anthropic Messages, and Gemini generateContent, including native function calls and token usage. The runtime executes tools separately under its own authorization policy.

Configure credentials through `GENESIS_OPENAI_API_KEY`, `GENESIS_ANTHROPIC_API_KEY`, or `GENESIS_GEMINI_API_KEY`. Standard `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, and `GOOGLE_API_KEY` are also recognized. The adapter accepts a transient `api_key` configuration value; callers must never persist it. Status reports configuration presence only, never account access, keys, or health.

Defaults: `gpt-4.1-mini`, `claude-sonnet-4-5`, `gemini-2.5-flash`. A configured model overrides defaults. Availability depends on the account. These adapters provide text and client function tools, not provider hosted search, image generation, streaming, or arbitrary multimodal content.

`ProviderRouter.generate(messages, tools, config)` accepts normalized system/user/assistant/tool history and JSON Schema function declarations `{name, description, parameters}`. Tool calls normalize to `{id, name, arguments}` with optional opaque `_provider_data`. Results expose text, tool calls, input/output tokens, actual provider/model, and `provider_data`. Persist the complete tool call dictionaries **and** put result `provider_data` on the corresponding assistant message. This preserves Gemini thought signatures and OpenAI reasoning/continuation output. Gemini output usage includes thinking tokens. Estimated currency costs belong to the runtime and its configured rates; the adapters do not claim to report billed cost.

Requests time out after 60 seconds; responses are limited to 4 MiB. HTTP redirects are rejected so authentication headers cannot be forwarded to another host. Errors omit remote bodies, keys, and URLs. There are no automatic retries. An explicit `fallbacks` list authorizes one request per listed candidate after a failure; a timeout may still have incurred provider charges. Keys do not carry between candidates. Incomplete, blocked, malformed, or empty responses fail explicitly rather than executing partial tool calls.

Accounting metadata counts every transport invocation conservatively, including timeouts and errors that might already have been billed. Final `ProviderError.billable_attempts` contains the total attempted transports (default zero). A success exposes `provider_data['_prior_billable_attempts']` for failed transports before the successful candidate. Missing credentials and request-translation failures never increase these counters. The engine reserves all candidates and charges configured ceilings for attempts with unknown outcomes.

Token usage fields must be nonnegative JSON integers. Negative numbers, floats, booleans, numeric strings, null values, and malformed usage objects fail the request; Gemini candidate and thinking counts are validated separately before addition. Such failures remain billable attempts for conservative accounting and explicit fallback handling. Omitted counts retain zero; `provider_data['usage_complete']` is true only when both input and output fields were explicitly reported. For Gemini these are `promptTokenCount` and `candidatesTokenCount`; omitted `thoughtsTokenCount` defaults to zero. Explicit zero input/output counts are complete. The engine conservatively charges its configured ceiling when usage is incomplete, including when one reported count is positive.

Continuation contracts are exercised locally: OpenAI replays the complete output items, including encrypted reasoning, with `store=false` and `include=['reasoning.encrypted_content']`, then appends `function_call_output` linked by `call_id`. Anthropic groups parallel `tool_result` blocks into the next user message. Gemini replays preserved content parts and their opaque signatures before matching `functionResponse` by name and ID. These are wire-contract tests against the documented formats, not claims of live account verification.

## Verification

Run `python -m unittest discover -s tests -p test_providers.py -v`. Tests use a clearly labeled local HTTP server test double to exercise actual urllib serialization, authentication headers, native function exchanges, signature preservation, token accounting, fallback, response limits, error sanitization, and absence of retries. These tests do **not** establish live credential validity or model availability. A live objective requires a real configured credential and is billed by its provider.

Wire formats checked against official documentation on 2026-10-17:

- [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling)
- [Anthropic Messages API](https://platform.claude.com/docs/en/api/messages/create)
- [Gemini function calling](https://ai.google.dev/gemini-api/docs/function-calling)
- [Gemini thought signatures](https://ai.google.dev/gemini-api/docs/thought-signatures)
