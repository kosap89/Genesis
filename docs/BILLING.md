# Official OpenAI organization reporting

Verified against official documentation on 2026-11-09. Development used
subscription-authenticated Codex, deterministic HTTP fixtures and local tests only.
Initial implementation verification made no OpenAI request, paid model inference
or live Genesis agent execution. Subsequently, CEO-authorized real reporting
succeeded on 2026-11-09: completion usage returned 40 historical requests and the
Costs endpoint returned no monetary rows. Admin authentication/report retrieval
are verified; a nonempty live cost amount and prepaid balance are not. See
STATE.md for the exact window and evidence. No new model inference was performed.

## Dashboard figures

The financial section separates Genesis conservative spent/reserved/remaining
budget, published-price estimated API cost, official OpenAI organization costs,
and remaining internal venture budgets. Organization costs have daily, OpenAI
project ID and API key ID breakdowns, a named UTC month/window and last successful
synchronization time. OpenAI project IDs are not automatically Genesis ventures.
Optional completion request/token usage is grouped by project, API key and model;
it covers completions only, not all OpenAI products.

Organization costs can include other applications, storage or services. They are
not a Genesis-only invoice, payment record or remaining credit balance. Reporting
can be delayed or adjusted. Failed refreshes retain the last successful report
with failure/stale labels; old months name that month. Cached reports after
restart are labeled historical without a current session credential. Missing
amounts produce an incomplete report and known subtotal, never invented zeros.
Different currencies are never summed. The Genesis-attributed official billed
amount remains unavailable pending independent reconciliation; organization totals
do not populate it. Reporting figures never change budget enforcement.
When OpenAI returns no cost amounts or currency, the dashboard says so explicitly;
it does not display a fabricated USD total or claim a zero final bill, even if
usage has already appeared.

## Official sources and prepaid balance

- [Organization Costs API](https://developers.openai.com/api/reference/resources/admin/subresources/organization/subresources/usage/methods/costs):
  `GET https://api.openai.com/v1/organization/costs`, current UTC month, daily
  buckets, grouped by `project_id` and `api_key_id`. The current reference supports
  both cost attribution fields. Unavailable IDs remain unattributed.
- [Completion Usage API](https://developers.openai.com/api/reference/resources/admin/subresources/organization/subresources/usage/methods/completions):
  optional `GET https://api.openai.com/v1/organization/usage/completions`, daily
  buckets grouped by project/API key/model.
- [Administration guide](https://developers.openai.com/api/docs/guides/admin-apis):
  organization endpoints use a separate Admin key. The documented Admin-key
  creation contract does not expose a billing-only/read-only scope parameter.
  Do not assume the key itself is restricted to these reads. Choose the least
  privileges and shortest suitable expiry available in organization settings;
  Genesis itself only performs the two fixed GET reporting operations.

No officially documented supported endpoint for remaining prepaid credit balance
was found in the current official API reference. Genesis returns
`prepaid.supported=false`, `balance=null`, and links to the
[official billing dashboard](https://platform.openai.com/settings/organization/billing/overview).
The [official credit guide](https://developers.openai.com/api/docs/guides/chatgpt-api-credits)
directs users to billing settings. Genesis does not scrape the dashboard, use
private endpoints, infer prepaid credits from costs, purchase credits or top up.

## Optional secure setup after local verification

An Admin key is needed only for official reporting. Existing estimates and
budgets work without it. Never paste keys into chat, objectives, documents,
command arguments, source files or Git.

1. Run Genesis at its existing loopback address and open the CEO Command Center.
2. Obtain a separate Organization Admin API key from official OpenAI organization
   settings if you want reporting. Keep the ordinary model key separate.
3. In a local interactive terminal at `C:\Genesis`, run:

   ```powershell
   python -m genesis.billing_credentials
   ```

   The hidden prompt accepts an `sk-admin-` key and sends it directly to the local
   server with CSRF protection. It bypasses environment HTTP proxies and refuses
   redirects. Hidden input unavailability fails safely. Another local port can
   use `--url http://127.0.0.1:PORT`. Configuration alone makes no OpenAI request.
4. The browser shows credential presence only. Press **Refresh official reports**
   and inspect the result/window/time or safe error. This cannot run agents or
   model inference.
5. Optional periodic refresh defaults off. Supported intervals are 900 to 86400
   seconds; disable optional completion usage for cost-only reporting.
6. Clear the key with the dashboard button or
   `python -m genesis.billing_credentials --clear`. Restart removes the key too.

The Admin credential stays in server memory only: never returned to frontend
JavaScript, persisted in the database/environment/logs, sent to model providers,
or exposed through agent tools. Reports/settings persist locally and contain
organizational financial metadata, not the key. Key rotation/clearing invalidates
in-flight publication and clears the visible report. Historical database backups
may retain previous reports.

Genesis remains single-user and loopback-only, without OS process isolation.
Approved host subprocess execution is not a sandbox. Application isolation
prevents credential forwarding and offers no billing agent tool, but cannot
protect process secrets from arbitrary hostile same-user host code. Existing
terminal/network restrictions and approval boundaries remain unchanged.

## API, bounds and verification

`BillingService` belongs to the HTTP server, not the agent engine. Local endpoints:

- `GET /api/billing`: cached state only; also in `GET /api/state`.
- `POST /api/billing/credentials`: hidden helper's key or `{clear:true}`.
- `POST /api/billing/settings`: `refresh_interval_seconds` and `include_usage`.
- `POST /api/billing/refresh`: empty object, explicit reporting synchronization.

Mutations preserve Host/Origin/CSRF checks. No arbitrary URLs, billing mutations,
top-ups or automatic budget increases exist. Model credential selection rejects
Admin keys before a billable attempt. Refresh is serialized, with a 30-second
manual cooldown; HTTP 429 imposes at least 900 seconds backoff. Periodic refresh
requires both enabled settings and a session key. Pagination is capped at eight
pages per endpoint with cursor/duplicate checks, 2 MiB response limits,
per-request timeouts and a 30-second synchronization deadline. Incomplete cost
pagination never replaces the previous report. Usage failure can leave valid
costs available. Shutdown retains the data lease until in-flight work stops.

Tests use fake keys, injected HTTP responses and explicit browser fixtures. They
cover authentication/CSRF/proxy isolation, cost parsing, pagination, errors,
rate limits, delays, historical/month rollover labels, shutdown/key rotation and
unchanged budgets/tasks. Fixture screenshots are not live billing evidence.
See STATE.md for actual verification results and live limitations.
