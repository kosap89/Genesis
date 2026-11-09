# Genesis architecture

This document describes the implemented local system. It is not a statement that
live business acceptance objectives have passed. See `ACCEPTANCE.md` for those
objectives and `STATE.md` for verification evidence and the next development task.

## Runtime and persistence

`python -m genesis` starts `genesis.server`: a loopback-only Python HTTP service,
the static command center, and a background scheduler with a bounded worker pool. The production runtime
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

Each store write is committed immediately. Related approval records, waiting-task
state, and request audit events are committed together through `Store.batch`.
A complete engine operation may span several commits; the system does not claim
atomicity across SQLite, external providers, and filesystem effects. Restart
recovery accounts for these gaps.
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

The seven built-in roles are reusable templates. `TeamManager` persists custom
role templates, UUID agent instances and project memberships with route overrides
and responsibilities. Agents may share a role and belong to several projects.
There is no agent-count limit. Creating, configuring or duplicating an agent makes
no provider call. Legacy seven IDs remain compatible and their configurations and
history survive the additive, idempotent migration. These legacy defaults remain
available across projects; new instances require active project membership, or
may run standalone only when they have no active memberships.

Task creation captures the exact agent ID/name and a configuration snapshot,
including instructions, specialization, responsibilities, provider/model/reasoning,
fallbacks and conservative rates. Template, instance and membership edits do not
rewrite authorized tasks. Explicit resume with agent settings records the change.
Global enable and membership checks still stop new requests for disabled agents.

The scheduler selects queued tasks whose dependencies completed. Configurable
`max_concurrency` defaults to one and accepts 1?16. Each task has a separate
workspace; requests may execute concurrently when explicitly configured.
Each model turn:

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

- `waiting_approval`: a tool needs network, host execution or individual delegation authorization.
- `waiting_children`: the parent waits for its delegated tasks.
- `blocked_credentials`: no billable request was made and credentials are missing.
- `blocked_budget`: the next reservation would exceed a global, project or agent budget.
- `blocked_agent`: the assigned agent or project membership is unavailable.
- `blocked_dependencies`: a prerequisite failed, was cancelled or is missing.
- `paused_limit`: the configured model-turn limit was reached.
- `interrupted`: execution stopped with a result requiring review before resumption.
- `failed`: an execution/provider error stopped the task.
- `cancelled`: the CEO stopped future planned work.

Explicit resume is supported for `interrupted`, `blocked_credentials`,
`blocked_budget`, `blocked_agent`, `blocked_dependencies`, `paused_limit`, and `failed`. It requeues the existing task and
retains its history. Completed and cancelled tasks cannot be resumed. Cancellation
also cancels nonterminal children and denies pending approvals. It cannot undo
an external request or process that already started.

Normal resume preserves the captured primary route. An explicit resume request can
include a different provider/model and records the old/new route in the audit log.
The command center offers a separate “Resume with agent settings” action for this
purpose; updating a role configuration alone does not reroute old tasks.

Independent mode cannot delegate. Collaborative mode can propose work for a
specific enabled project agent. Every invocation needs a CEO decision before the
child is created; global network/terminal switches do not grant delegation.
Approval captures the target configuration and expires if it changes. The default
depth is one and total descendants per root eight; settings allow depth 0?8 and
1?100 descendants. Children do not inherit Astra authorization. Each child retains
its own history, configuration snapshot and workspace. Parents receive attributed,
untrusted child summaries after completion. There is no required COO.

Dependencies and review references must name existing tasks in the same project;
review requires another agent ID and waits for the reviewed task to complete.
Artifacts are explicitly imported with source task/agent attribution and SHA-256.
Collaborative tasks claim relative file paths or directory prefixes in their
project; overlapping claims from nonterminal collaborative tasks are rejected.
Workspace writes and imports claim their paths automatically. Independent tasks
have separate workspaces and do not conflict merely by using the same filename.
Claims coordinate cooperative tools, not arbitrary host subprocess edits; approved
host execution remains outside an OS sandbox.

## Model providers

`genesis.providers` translates the common message/tool contract into OpenAI
Responses, Anthropic Messages, and Gemini generateContent requests. Adapters
normalize text, function calls with object arguments, usage, and provider/model
identity. Provider-specific continuation material is retained where required, such
as OpenAI response items and Gemini thought signatures. Tool execution is owned
by the engine, never by the provider adapter.

Credentials come from the server environment, with `GENESIS_*_API_KEY` taking
precedence over the corresponding provider key names. The local command center
can set that process override for the current session through its password form.
The value clears from the input immediately, is not written to browser storage or
SQLite, and is lost when the server exits. Clearing removes only the process
override; an inherited standard provider key can remain active. An explicit checkbox
can configure the seven legacy default agents' provider/model, preserving rates/fallbacks.
Neither operation runs model work or automatically resumes existing objectives.
The UI reports only key presence. A configured key is not proof of connectivity,
quota, model availability, or account health. `.env` is not automatically loaded.

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
and applies the task snapshot's input/output guard rates. It reserves that amount for every possible
primary/fallback candidate. Requests block when spent plus reserved plus the new
reservation exceeds any configured global, project or optional agent budget.
All scoped reservations and settlements use the shared store lock and batched
SQLite writes. Changing configuration cannot reset spent or reserved ledgers.

Successful calls settle reported input/output tokens at configured rates. Missing
usage settles at the per-call ceiling. Earlier potentially billable fallback failures
are charged their per-call ceilings. Failed request sequences charge the ceiling
for the number of dispatched attempts; missing-key-only failures cost zero. Spent
and reserved values are persisted globally and per project/agent, with estimated task costs and request/
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
  maximum steps/output tokens, request concurrency and delegation depth/descendant limits.
- `POST /api/credentials`: process-only provider credential override (empty key
  clears it) and optional explicit configuration of the seven legacy default routes.
  Responses/audit contain presence and provider only, never the key.
- `POST /api/role-templates` and `/api/role-templates/<id>`: create/edit reusable defaults.
- `POST /api/agents`, `/api/agents/<id>`, `/api/agents/<id>/duplicate`: stable instances.
- `POST /api/projects/<id>`: optional project budget.
- `POST /api/projects/<id>/team` and `/api/projects/<id>/team/<agent_id>`:
  assignment, enable/disable, responsibilities, route overrides and soft removal.
- Task submission accepts `agent_id`, `work_mode`, `depends_on`, `review_of` and
  `file_claims`; role names remain a compatibility route for legacy defaults.

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

Cancellation/shutdown checks and model/tool claim records are serialized under the
engine guard. A claim is the point after which that one invocation is considered
in flight. Approval creation is guarded against a concurrent cancellation, so a
cancelled task cannot acquire a new pending approval. Startup also recovers legacy
pending approvals that were written before their task's waiting transition.

Tool execution records `tool_started` before invoking the tool and commits a result
afterward. If the persisted history indicates an ambiguous invocation without a
result, it records `tool_outcome_unknown` and does not automatically replay the
side effect. This provides conservative recovery, not exactly-once effects across
process crashes. Cancellation and shutdown cannot reliably retract in-flight work.
Back up the data directory with the service stopped; there is no backup service.
CLI shutdown retains its data-directory lease until the worker actually exits,
including any already dispatched request, rather than releasing it after a short
join timeout while the old worker can still write.

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


## Model registry and separate reporting ledger (2026-11-09)

`genesis.models` supplies reviewed catalog capabilities/prices and new-role routes;
existing agent records are retained. Model/effort and all fallback configurations
are validated before dispatch. Task-scoped Astra permission is checked at creation,
resume and each dispatch; delegation does not transfer it.

`genesis.accounting` reconstructs report estimates from persisted response usage
without rewriting legacy charges. `settings.pricing_overrides` changes reporting
only. `spent_usd`/`reserved_usd` remain the enforced conservative ledger. Known
published long-context rates may raise the effective guard; user reporting prices
cannot lower it. Missing cached details, incomplete usage and uncertain failed
attempts are exposed rather than inferred as zero billing. Official invoice data
is unavailable; the reporting summary explicitly returns null for it.

`POST /api/tasks/estimate` computes a local preview without task/workspace creation
or dispatch. `POST /api/pricing` persists validated reporting overrides. Agent and
task/resume APIs accept reasoning_effort; task/resume also accepts an explicit
astra_authorized boolean. Agent fallback objects allow optional reasoning_effort.
The local credential form preserves agent routes by default; an explicit opt-in
can apply recommended routes. No new endpoint automatically starts or resumes work.
