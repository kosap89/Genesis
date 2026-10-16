# Genesis architecture

This document describes the implemented local system. It is not a statement that
live business acceptance objectives have passed. See `ACCEPTANCE.md` for those
objectives and `STATE.md` for verification evidence and the next development task.

## Runtime and persistence

`python -m genesis` starts `genesis.server`: a loopback-only Python HTTP service,
the static command center, and one background agent worker. The production runtime
uses the Python standard library; Playwright is an optional development dependency
for browser verification. No external database, message broker, frontend build,
cloud deployment, or production demonstration provider is required.

`Engine` owns a `Store`, a `ProviderRouter`, the worker wake/stop events, and a
reentrant guard for related application operations. `Store` uses SQLite with WAL:

- `records(kind, id, body)` contains JSON ventures, tasks, agent configurations,
  settings, approvals, organizational memory, opportunities, and artifact metadata.
- `messages(seq, task_id, body)` preserves ordered user instructions, assistant
  responses, tool requests, tool results, and delegated results.
- `events(seq, task_id, body)` preserves the audit timeline with top-level event
  fields, IDs, and UTC timestamps.

Each store write is committed immediately. A complete engine operation may span
several commits; the system does not claim atomicity across SQLite, external
providers, and filesystem effects. Restart recovery accounts for these gaps.
Store writes are serialized within the process. The CLI takes an OS-owned
`DataLease` on `.genesis.lock`, rejecting a second CLI process for the same data
directory and releasing the lock when the process exits. Directly embedding Engine
does not acquire this lease. There is no distributed worker or multi-host job claim.

The default data directory is `data`, configurable with `--data-dir` or
`GENESIS_DATA_DIR`. The database is `genesis.sqlite3`. Each task receives
`workspaces/<task_id>/`. Files remain on disk, and artifact records refer to paths
inside that task's workspace. A final textual result is also written to
`GENESIS_RESULT.md`. The browser does not execute or embed generated artifacts;
the download route returns them as attachments.

## Task and agent lifecycle

The seven persisted roles are COO, strategy, engineering, QA, growth, finance, and
operations. Each has a prompt, provider, model, estimated input/output token rates,
and up to two explicit fallback routes. These are real model/tool configurations;
idle roles are not background employees or continuously running autonomous agents.

Creating a task validates its objective, venture, role, provider, and model, then
persists a `queued` record, initial user message, workspace, and audit event. The
task captures its primary provider/model at creation. Rate estimates and fallback
routes are read from the role configuration during execution; changing those
settings can affect later calls in an existing task.

One worker selects the next queued task and marks it `running`. Each model turn:

1. Resolves previously persisted tool calls that lack a result.
2. Pauses if delegated tasks remain outstanding.
3. Checks the step limit and estimated budget reservation.
4. Sends the system prompt, message history, and available tool schemas through
   the real provider router.
5. Settles estimated usage, persists the assistant response and tool calls, and
   increments the turn counter.
6. Runs requested tools on the next loop iteration, or saves a final response and
   marks the task `completed` when no tool calls remain.

Other durable task states are:

- `waiting_approval`: a tool needs network or host execution authorization.
- `waiting_children`: the parent waits for its delegated tasks.
- `blocked_credentials`: no billable request was made and credentials are missing.
- `blocked_budget`: the next configured reservation would exceed the budget.
- `paused_limit`: the configured model-turn limit was reached.
- `interrupted`: execution stopped with a result requiring review before resumption.
- `failed`: an execution/provider error stopped the task.
- `cancelled`: the CEO stopped future planned work.

Explicit resume is supported for `interrupted`, `blocked_credentials`,
`blocked_budget`, `paused_limit`, and `failed`. It requeues the existing task and
retains its history. Completed and cancelled tasks cannot be resumed. Cancellation
also cancels nonterminal children and denies pending approvals. It cannot undo
an external request or process that already started.

A top-level objective can delegate at most eight specialist tasks. Children have
their own task records, role configurations, histories, and workspaces; they cannot
delegate further. Work executes serially in the current worker. The parent resumes
when every child is terminal and receives an explicitly untrusted summary of their
results/errors. A child needing credentials, budget, approval, or other intervention
keeps the parent waiting. `task_inspect` is limited to the current venture.

## Model providers

`genesis.providers` translates the common message/tool contract into OpenAI
Responses, Anthropic Messages, and Gemini generateContent requests. Adapters
normalize text, function calls with object arguments, usage, and provider/model
identity. Provider-specific continuation material is retained where required, such
as OpenAI response items and Gemini thought signatures. Tool execution is owned
by the engine, never by the provider adapter.

Credentials come from the server environment, with `GENESIS_*_API_KEY` taking
precedence over the corresponding provider key names. The UI reports only key
presence. A configured key is not proof of connectivity, quota, model availability,
or account health. `.env` is not automatically loaded.

Each configured candidate receives at most one request. The router tries the primary
route and then explicitly configured fallback routes; it does not silently choose a
new model or repeatedly retry a paid request. Missing credentials are skipped
without a billable attempt. Transport/parse failures after request dispatch are
counted conservatively as potentially billable. Provider errors expose safe
diagnostics rather than API keys or raw error bodies. The standard transport uses
fixed provider HTTPS endpoints, disallows redirects, has a timeout and response
size limit, and does not implement streaming.

## Estimated cost accounting

The budget is a local estimate, not a provider-side hard cap or invoice integration.
Role defaults of $10 input / $30 output per million tokens are configurable
conservative placeholders, not verified current prices. Operators must set estimates
that cover all configured routes and separately configure provider account limits.

Before a model request, the engine estimates an input ceiling from serialized
message/tool UTF-8 bytes plus 4,096 bytes, adds the configured maximum output tokens,
and applies the role's input/output rates. It reserves that amount for every possible
primary/fallback candidate. Requests block when spent plus reserved plus the new
reservation exceeds the configured budget.

Successful calls settle reported input/output tokens at configured rates. Missing
usage settles at the per-call ceiling. Earlier potentially billable fallback failures
are charged their per-call ceilings. Failed request sequences charge the ceiling
for the number of dispatched attempts; missing-key-only failures cost zero. Spent
and reserved values are persisted globally, with estimated task costs and request/
response audit events. Provider tokenization, hidden usage, changed prices, and
account billing can differ from this estimate.

## Tools and trust boundaries

The browser, engine, provider, filesystem tools, network tools, and approved host
execution have different authority:

- The local HTTP interface is single-user. It binds to `127.0.0.1`/`localhost`,
  validates Host and supplied Origin headers, and requires a per-process CSRF token
  for mutations. It has no multi-user authentication, remote access, or tenant boundary.
- Static assets use a restrictive same-origin CSP, no inline scripts, frame denial,
  `nosniff`, and no-store responses. User/model content is inserted as text through
  DOM APIs; arbitrary memory and result strings are not interpreted as HTML.
- API keys stay in the server environment and are not part of state responses.
  Objectives, memory, audit entries, model responses, and artifacts are ordinary
  sensitive company data, persisted locally without application-level encryption.
- Workspace tools validate relative paths, reject traversal, Windows reserved
  devices, alternate stream syntax, symlinks, and junctions. Reads/writes and
  directory listings have size/count limits. These checks constrain the tool API;
  they are not an operating-system sandbox.
- Network research requires an invocation approval unless globally enabled.
  Fetching is restricted to public HTTPS on port 443, rejects URL credentials and
  nonpublic resolved addresses, pins the validated DNS results while retaining TLS
  hostname checks, revalidates redirects, strips credentials on cross-host redirects,
  and limits response size/redirect count. Search uses Brave with an optional key;
  otherwise it is explicitly limited to Wikipedia discovery. Model-provider calls
  use their configured credentials independently of this research permission.
- Python test/terminal execution requires invocation approval unless globally
  enabled. Only the Python interpreter is exposed, with isolated Python mode, no
  shell, a reduced child environment, bounded time, and capped captured output.
  **The code runs as the server OS user. It can still access host files, network,
  and other same-user capabilities. It is not contained by the workspace path checks.**
- Memory, files, fetched sources, and child results are untrusted input. The system
  prompt identifies them as such; prompt text is not a security enforcement boundary.
  Network/execution permissions are enforced outside the model.

When a tool requests permission, its exact arguments and risk are persisted in an
approval record tied to its tool-call ID. Approval grants only that invocation's
capability. Host-execution requests also capture a SHA-256 workspace fingerprint.
If the workspace content changes before approved execution, that approval expires
and the invocation needs a fresh approval. This detects changes through normal
workspace files; it does not prevent same-user concurrent mutation or sandbox the
process. Denial produces a tool error instead of executing the invocation. Global
network/terminal controls authorize that capability for later calls without an
individual queue entry. Neither option authorizes rollback or safely limits arbitrary
approved Python code. Credentials are filtered out of the child environment, but
same-user filesystem access can still expose credentials stored elsewhere.

`artifact_list` and `artifact_import` let agents inspect/copy actual deliverables
from tasks in the same venture. Import validates both workspace paths, refuses an
existing destination, limits each file to 100 KB, and records the source task and
SHA-256 in the audit log. Independent QA can import source/tests before running
them with the usual execution approval. Tasks without a venture share the unassigned
scope; venture filtering is organizational, not a multi-user isolation boundary.

`self_improvement_snapshot` copies a bounded, filtered source snapshot into a task
workspace and preserves a separate baseline plus hash manifest in reserved internal
`.genesis-*` paths. Ordinary workspace tools cannot edit those internal paths.
`self_improvement_diff` compares candidate changes to that original baseline,
validates baseline hashes, detects live-source conflicts, and writes a reviewable
patch artifact. Binary/oversize omissions are explicitly listed. It never applies
changes to the running service. Candidates can be edited/tested and delivered for
manual review. Approved Python execution can still bypass these file-tool controls.
The filename filter is not a secret scanner; keep secrets out of source.

## HTTP API and command center

`GET /api/state` returns durable collections, settings, estimated usage, provider
presence, stats, recent audit events, and the CSRF token. The browser polls every
three seconds while visible. Polling preserves in-progress form input. Task detail
polling separately exposes actual model messages, tool calls/results, and events.

The implemented routes are:

- `GET /api/health`: service and worker-alive status.
- `GET /api/tasks/<id>`: one task, messages, events, and artifacts.
- `GET /api/tasks/<id>/bundle`: ZIP attachment of actual task deliverables, excluding
  internal `.genesis-*` files and unsafe paths, with a 50 MB bound.
- `GET /api/artifacts/<id>`: validated workspace file, attachment-only, up to 20 MB.
- `POST /api/tasks`: objective and optional venture/role/provider/model.
- `POST /api/tasks/<id>/cancel` and `/resume`: explicit lifecycle transitions.
- `POST /api/approvals/<id>`: `approved` or `denied` decision.
- `POST /api/ventures`, `/api/memories`, `/api/opportunities`: persistent context.
- `POST /api/settings`: estimated budget, research/host execution permissions,
  maximum steps, and maximum output tokens.
- `POST /api/agents/<role>`: provider, model, estimated rates, and fallback routes.

Mutations accept JSON objects and require `X-Genesis-CSRF`. Requests have a 128 KiB
body limit. Settings validate finite numeric bounds and actual boolean types;
agent routing accepts only implemented providers. Static serving is allowlisted
to the three command-center files. Unknown resources and unavailable artifacts
fail explicitly. There is no API for sending messages, purchases, deployments,
automatic source application, or billing-account administration.

## Restart, recovery, and operational limits

Startup creates missing defaults and role records without replacing persisted
configuration. New role records use the first configured provider in the supported
provider order, or OpenAI if no credentials are present. `start.ps1` offers a masked
credential prompt when no key is configured and forwards it only through the process
environment; it does not write credentials to disk. Queued work continues
automatically. A task previously marked
running becomes interrupted. A waiting approval remains pending; if a decision
was persisted but the task was not requeued before shutdown, it becomes interrupted
for review. Outstanding cost reservations are conservatively transferred to spent
usage because a dispatched request may already have been billed.

Tool execution records `tool_started` before invoking the tool and commits a result
afterward. If the persisted history indicates an ambiguous invocation without a
result, it records `tool_outcome_unknown` and does not automatically replay the
side effect. This provides conservative recovery, not exactly-once effects across
process crashes. Cancellation and shutdown cannot reliably retract in-flight work.
Back up the data directory with the service stopped; there is no backup service.

Current limits include serial task execution, no durable external scheduler or
multi-host workers, no external business connectors, no automatic source promotion,
no operating-system isolation, no retrieval index/context compaction, no live billing
reconciliation, and no application authentication/encryption. Messages accumulate
and are sent as history until provider/context or configured budget limits intervene.
The command center is a local operating surface, not evidence that an objective
was commercially validated or that its model output is correct.

Unit/HTTP/browser tests use explicitly identified fixtures and real local processes,
files, SQLite, and permission decisions. Browser model doubles verify orchestration,
not live intelligence. Provider transport tests verify request/response contracts;
paid live provider acceptance remains a separate, explicitly documented activity.
