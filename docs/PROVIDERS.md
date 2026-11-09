# Model providers

Genesis makes real synchronous HTTPS requests using Python's standard library. It does not fabricate model output. The router supports OpenAI Responses, Anthropic Messages, and Gemini generateContent, including native function calls and token usage. The runtime executes tools separately under its own authorization policy.

Configure credentials through `GENESIS_OPENAI_API_KEY`, `GENESIS_ANTHROPIC_API_KEY`, or `GENESIS_GEMINI_API_KEY`. Standard `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, and `GOOGLE_API_KEY` are also recognized. The adapter accepts a transient `api_key` configuration value; callers must never persist it. Status reports configuration presence only, never account access, keys, or health.

Provider defaults: `gpt-6.1-sol`, `claude-sonnet-4-5`, `gemini-2.5-flash`. New OpenAI agents use the role routes below; existing configurations are never migrated automatically. A configured model overrides defaults. Availability depends on the account. These adapters provide text and client function tools, not provider hosted search, image generation, streaming, or arbitrary multimodal content.

`ProviderRouter.generate(messages, tools, config)` accepts normalized system/user/assistant/tool history and JSON Schema function declarations `{name, description, parameters}`. Tool calls normalize to `{id, name, arguments}` with optional opaque `_provider_data`. Results expose text, tool calls, input/output tokens, actual provider/model, and `provider_data`. Persist the complete tool call dictionaries **and** put result `provider_data` on the corresponding assistant message. This preserves Gemini thought signatures and OpenAI reasoning/continuation output. Gemini output usage includes thinking tokens. Estimated currency costs belong to the runtime and its configured rates; the adapters do not claim to report billed cost.

Requests time out after 180 seconds by default (explicit transport timeout overrides remain supported); responses are limited to 4 MiB. HTTP redirects are rejected so authentication headers cannot be forwarded to another host. Errors omit remote bodies, keys, and URLs. There are no automatic retries. An explicit `fallbacks` list authorizes one request per listed candidate after a failure; a timeout may still have incurred provider charges. Keys do not carry between candidates. Incomplete, blocked, malformed, or empty responses fail explicitly rather than executing partial tool calls.

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


## Modern OpenAI controls (documentation checked 2026-11-09)

Agents & controls provides a model catalog, reasoning selector and visible
published input/cached-input/output prices. New OpenAI COO and operations roles
use gpt-6-luna/low; strategy, engineering and finance use gpt-6.1-sol/medium;
QA uses gpt-6.1-terra/medium; growth uses gpt-6.1-terra/low. Selecting provider
default effort uses Genesis's defaults (Sol medium; Terra/Luna low). Each role
can persist a different supported effort. Existing legacy/custom routes remain.

Sol and Astra support low, medium, high, xhigh and max. Terra and Luna also support
none. Responses requests use reasoning.effort, preserve encrypted continuation
and tool-call history, and reject temperature for these models before transport.
Reasoning defaults are chosen independently for explicit fallbacks. All routes
are validated before any network dispatch. Unknown custom identifiers remain
unverified; reasoning options are not guessed for them.

Astra requires explicit CEO authorization scoped to a task for primary or fallback
use. Merely selecting Astra in an agent form does not authorize spending. Delegated
tasks do not inherit this capability. Unverified gpt-6-astra-* snapshot identifiers
are rejected, preventing alias-based authorization or pricing bypasses.

The reviewed standard USD/million input/cached/output registry is: Sol 2/0.10/10,
Terra 1/0.05/5, Luna 0.10/0.01/0.50, Astra 10/1/50. The retained legacy entries are
GPT-4.1 mini 0.40/0.10/1.60 and GPT-4.1 2/0.50/8. Modern prompts above 272000 input
tokens apply 2x input/cache and 1.5x output to the whole request. These are list-price
estimates for standard text/function use, excluding provider billing adjustments,
other tiers, additional cache-write charges, regional premiums and hosted tools.
No such account-specific billing settings were queried or modified.

Reporting overrides are persisted by POST /api/pricing and the local pricing form.
They never feed budget enforcement. Existing conservative rates and historical
spent_usd remain intact. Known expensive routes raise enforcement to at least the
reviewed long-context input/output rates; this remains an estimate rather than an
external hard cap. Maximum output includes reasoning as well as visible output;
the existing 4096-token default may be too small for difficult reasoning work.
Output-limit failures remain failures, not claimed successful responses.

OpenAI raw usage and cached/reasoning detail fields are now retained. These counts
are subsets of input/output totals; reasoning is never added twice. Missing details
remain unknown. Historical records cannot recover caching that was never stored.
Reporting marks those estimates incomplete and assumes uncached input. Prior
failed fallback attempts remain conservatively charged and are exposed as unknown
usage rather than omitted from estimate completeness. Official billed USD stays
null until independently available; a reported dashboard deduction is not an invoice.

Local task previews estimate input tokens from UTF-8 bytes/4, maximum output and
the configured step limit. They disclose assumptions, context growth and excluded
fallback estimates. Previews create no task, workspace, reservation or provider call.
The actual guard still uses serialized input bytes plus an allowance and reserves
all explicit routes before dispatch.

Sources: [Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol),
[Terra](https://developers.openai.com/api/docs/models/gpt-6.1-terra),
[Luna](https://developers.openai.com/api/docs/models/gpt-6-luna),
[Astra](https://developers.openai.com/api/docs/models/gpt-6-astra),
[GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini),
[GPT-4.1](https://developers.openai.com/api/docs/models/gpt-4.1),
[pricing](https://developers.openai.com/api/docs/pricing), and
[reasoning usage](https://developers.openai.com/api/docs/guides/reasoning).
These contracts are verified locally with doubles, not through paid live tests.
