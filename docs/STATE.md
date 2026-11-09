# Genesis persistent project state

Updated 2026-11-09, Europe/Helsinki. Dynamic-team development continues verified commit `6681fa0`.
Preserve existing implementation and data; do not scaffold a replacement.

## Current checkpoint: dynamic project teams, offline verified

Verified 2026-11-09, Europe/Helsinki. Extended the existing system and preserved
real data. Development remained subscription authenticated: `codex login status`
reported **Logged in using ChatGPT**. No live provider calls, paid task creation
or paid task resume occurred. Provider doubles were used only in isolated tests.
The earlier $5 authorization was not reused for this development work.

### Implemented behavior

- Seven built-in role templates and custom templates support unlimited persistent
  UUID instances, including multiple agents with the same role. Each instance has
  its own name, specialization, instructions, provider/model/reasoning, optional
  budget, project memberships, task count and activity. Creating/duplicating an
  instance has no model side effects. Templates seed future instances; editing a
  template never silently rewrites existing instances.
- Project Agent Team supports creation, duplication, assignment, enable/disable,
  responsibilities, project route overrides, optional agent/project budgets and
  soft removal/reassignment without deleting historical work. Settings use stable
  agent IDs; task attribution retains names/IDs and previous assignees.
- New tasks freeze their complete agent configuration, including instructions,
  specialization, responsibilities, routes, fallback reasoning and guard rates.
  Explicit resume with agent settings is audited. Disabling/removing membership
  stops subsequent requests/tool claims; already claimed requests can finish.
- Independent work needs no coordinator and cannot delegate. Collaborative work
  exposes eligible project agents and proposes a specific instance. Every child
  invocation requires individual CEO approval. Changed target configuration
  invalidates approval. Children do not inherit Astra authorization. Configurable
  limits default to depth one and eight total descendants per root.
- Same-project dependencies coordinate work; ancestor dependencies that would
  deadlock delegation are rejected. Independent review excludes current and prior
  contributing agent IDs and checks again on execution/resume. Prompt context
  includes attributed prerequisites, actual results and artifact handoff IDs.
  Explicit imports preserve source attribution and actual byte hashes.
- Collaborative file/directory claims detect case-insensitive overlapping paths
  across nonterminal collaborative tasks. Writes, reports, imports and candidate
  snapshot/diff operations check their corresponding paths. Independent task
  workspaces remain separate. These claims do not isolate arbitrary host code or
  merge independently produced application components automatically.
- Request concurrency defaults to one, configurable from 1 to 16. Global, project
  and optional agent caps all gate atomic reservations under the shared store lock.
  Settlement, cancellation and conservative restart recovery preserve all scoped
  ledgers. Metadata edits cannot reset spent/reserved. Existing conservative guard
  rules and separate published-price reporting remain intact.

### Verification and defects repaired

- `python -m unittest discover -s tests -v`: **155 tests in 92.078s, OK,
  one Windows symlink privilege skip**. Added 32 tests across team metadata,
  real loopback API and runtime orchestration. Coverage includes repeated roles,
  custom templates, concurrent creation, persistence, isolation, pinned snapshots,
  specific-instance approvals, scoped budgets, parallel scheduling, cancellation,
  review identity, dependencies, actual file claims and restart accounting.
- `node --check web/app.js` and `node --check tests/browser-e2e.cjs`: **PASS**.
- `npm.cmd run test:e2e`: **PASS** after final UI changes. Production-mode isolated
  server had credentials removed; separate execution fixture explicitly uses
  provider doubles. Verified template editing, duplicate identities, project
  overrides/isolation, remove/reassign/history, disabled membership eligibility,
  concurrency controls, configuration restart persistence, mobile layout and
  unsaved form/project-switch behavior alongside the existing workflows.
- Review and failed runs exposed actual defects: empty model names silently
  defaulted; specialization/responsibilities were omitted from prompts; reassigned
  reviewers could review their own work; membership disable missed tool claims;
  delegation could depend on ancestors; report/snapshot writes missed file claims;
  polling could overwrite unsaved configuration and retain stale agent choices.
  These were repaired and covered before the final passing runs.
- A pre-migration SQLite backup is local under ignored `data/`. Restarted only
  after checking all five tasks terminal, zero reservations, no pending approvals
  and no session credentials. Compared before/after original agent configuration
  fields and task IDs/status/objectives/routes/costs/results: **exactly preserved**.
  Seven templates were added; all five tasks gained legacy ID/config metadata.
  No model-response events were added. No demonstration tasks/agents were added
  to the real data directory.
- Service now listens only at **127.0.0.1:8787**, PID **14080**, health `ok`, worker
  alive; CEO Command Center opened in browser. Existing counts: seven legacy
  instances, seven templates, five tasks, one venture, zero explicit memberships.
  Stored budget **$5**, conservative spent **$3.91808**, reserved **$0**;
  concurrency **1**, delegation depth **1**, total descendants **8**.
  All providers currently unconfigured. Runtime evidence/logs/database remain
  ignored and are excluded from Git; no credentials were written to source/docs.

### Limits and exact next task

This verifies infrastructure using local tests, not live multi-agent effectiveness
or founding acceptance. Historical live acceptance remains **NOT PASSED**. Legacy
role IDs remain available across projects for compatibility; new UUID instances
require active membership (or no memberships for standalone work). Old records
never retained full configuration snapshots: migration can preserve stored task
routes and current agent metadata, not reconstruct lost historical instructions or
fallbacks. New tasks have complete snapshots. Removing an instance's membership
preserves its global identity/history; there is no destructive agent deletion API.

The service remains single-user/loopback. File claims coordinate supported tools,
not OS processes. Approved host execution is still **not an OS sandbox**. Price
estimates remain conservative ledger estimates, not official provider invoices.
The historical $0.2484168 uncached published-price estimate and unknown cache/
billing reconciliation remain unchanged; development added **zero API consumption**.
Modern model availability/live compatibility remains unverified.

**Next task:** use Project -> Agent Team for the next actual project. Before any
new live acceptance, strengthen the existing evidence/completion contracts, then
obtain fresh explicit CEO permission for the exact live scope/budget and configure
credentials through the local password form (process memory only). Execute and
independently review the three founding objectives from ACCEPTANCE.md; record
real artifacts, failures and provider consumption without inferring success from
runtime `completed` or test doubles. No paid acceptance was attempted here.

## Previous checkpoint: modern model controls and separate accounting, offline verified

Verified 2026-11-09, Europe/Helsinki. Continued the existing architecture and data.
**Development used subscription-authenticated Codex only.** `codex login status`
reported **Logged in using ChatGPT** before and after work; the local auth-mode
check reported chatgpt with no API key. Authentication was not switched. No live
OpenAI/other model requests and no Genesis paid task creation/resume occurred.
The previous $5 live-test consent is not permission for this development session;
**separate CEO authorization is required before any further live acceptance**.

### GitHub synchronization and safety

Initial main was clean at `3d7418c`, two commits ahead of `origin/main` at
`14857d6`: preparation `d765cb5` and live findings/byte fix `3d7418c` had been
committed locally but not pushed. A fresh fetch confirmed compatible ancestry.
Audited 41 tracked paths and 46 unique blobs across both unpublished trees: no
credential/runtime/database/private-log findings; matches were blank environment
examples and known URL-rejection fixtures. Normal push advanced GitHub main from
14857d6 to 3d7418c, without force or history rewriting. The implementation in this
checkpoint is committed on the same main branch for normal synchronization.
A final independent scan/review covered all 13 pending source/test/UI files and
found no secrets, binary artifacts or runtime-data paths. Runtime evidence remains
ignored. No global Git or provider account settings were changed.

### Model and permission controls

- Reviewed local catalog adds gpt-6.1-sol, gpt-6.1-terra, gpt-6-luna and gpt-6-astra,
  retaining legacy/custom routes. New OpenAI COO/operations use Luna low;
  strategy/engineering/finance Sol medium; QA Terra medium; growth Terra low.
  Existing seven agent records are preserved byte-for-value in their JSON data;
  none was automatically migrated away from its saved legacy route.
- Provider/model/reasoning dropdowns persist per role. A session key preserves
  saved routes by default; the initially unchecked opt-in applies recommended
  routes. Reporting-only model price overrides are editable and persistent.
- Responses payloads use supported reasoning.effort values, reject modern-model
  temperature before dispatch and retain function calls/encrypted continuation.
  Every primary/fallback route is prevalidated; fallback effort is independent.
  Legacy and non-OpenAI providers remain covered by existing tests.
- Astra requires an explicit task-scoped CEO authorization, including fallback and
  resume routes. Agent selection alone grants nothing; delegation does not inherit
  it. Unverified Astra snapshot aliases are rejected before transport.
- Local objective previews show route/effort, approximate call/task costs and the
  conservative reservation. They create no task, workspace, reservation or provider
  call; tokenization, maximum-output, step/context and fallback assumptions are shown.

### Reconciliation and preserved conservative budget protection

The historical 350486 input and 13774 output tokens at configured $10/$30 per
million equal **$3.91808 exactly**. That is the conservative charged ledger, not a
provider invoice and not the current outstanding reservation (**$0**).

The 40 historical calls used two differently priced models: 35 GPT-4.1 mini calls
with 303225 input / 12123 output tokens, and five GPT-4.1 calls with 47261 input /
1651 output tokens. Applying verified standard list prices without cache discounts
yields **$0.2484168**. The CEO-reported approximately $0.15 dashboard deduction has
not been independently reconciled. Cached-token details were not retained for any
of those 40 old responses, so the estimate is explicitly incomplete and assumes
uncached input. Those lost details cannot be recovered from the saved history.
Reporting timing, actual cache usage and invoice data remain unresolved; no billed
amount is invented. Official billed USD is null/unavailable in the dashboard.

New response metadata retains raw usage and known cached/reasoning counts. Missing
details stay unknown rather than zero. Reasoning tokens are already within output
totals and are not added twice. Failed billable fallback attempts are exposed as
unknown usage and mark estimates incomplete. The dashboard separates all of these
from conservative charges and current reservations.

Published registry prices and local reporting overrides never feed authorization
or reduce spent/reserved values. The original input-byte/output-token reservation
and uncertain-outcome settlement remain. Known expensive models can only raise
effective guard rates (including long-context Astra), not lower them. The stored
company budget stays $5, conservative spent $3.91808, reserved $0. The CEO reports
an external $10 OpenAI organization limit and disabled auto-reload; those account
protections were neither queried nor changed here.

Published prices/capabilities were checked against official OpenAI model/pricing
and reasoning pages on 2026-11-09; exact links and assumptions are in PROVIDERS.md.
Estimates exclude other processing tiers, regional premiums, extra cache-write
charges and hosted-tool charges. They do not guarantee a provider-side hard cap.
The preserved 4096-output-token limit may be insufficient for harder reasoning.
**Modern model account access and live compatibility remain unverified.**

### Verification and integrated local service

- `python -m unittest discover -s tests -v`: **123 tests in 49.056s, OK,
  one Windows symlink privilege skip**.
- `node --check web/app.js` and `node --check tests/browser-e2e.cjs`: **PASS**.
- `npm.cmd run test:e2e`: **PASS**, isolated ports/data, credentials absent for
  production-mode checks and explicitly identified provider doubles for execution.
  New checks cover four modern model families, reasoning/restart persistence,
  reporting/guard separation, non-dispatching previews, Astra authorization and
  opt-in route reset. Existing approval/artifact/history/mobile workflows pass.
  An intermittent test edited the next role before the preceding save handler
  finished; awaiting handler completion fixed it while preserving saved-value checks.
- Independent review found and repaired fallback-estimate completeness, missing
  detail/zero conflation and preview directory creation, with regression tests.
- Loaded the tested changes into idle production, PID **42180**, loopback
  **127.0.0.1:8787**, health **ok**, worker alive. Original seven agent records,
  settings and five task IDs were compared before/after restart and are unchanged.
  **Provider request/response count remains 40**, tokens remain 350486/13774;
  additional API consumption for this development: **0 requests / 0 tokens**.
  All providers remain unconfigured; no session key was present to lose.
  Chrome rendering check shows Connected, seven forms, no page errors; screenshot
  reviewed. Ignored evidence: `test-results/model-controls-production-evidence.json`
  and `test-results/live-acceptance-readiness.png`.

**Exact next task:** continue local-only completion/evidence contract hardening or
obtain separate CEO authorization for a tightly bounded modern-model live smoke.
Do not start/resume paid work merely because stored budget remains nonzero. Before
any authorized live run, choose explicit model/effort and verify account access,
limits and pricing; reconcile actual provider usage/billing independently. Founding
business/autonomous QA/self-improvement acceptance remains NOT PASSED; this work
establishes local model/accounting contracts, not new live acceptance success.

## Historical checkpoint: real live trials executed; founding acceptance NOT PASSED

Verified 2026-11-09, Europe/Helsinki. CEO configured OpenAI through the local UI
and explicitly authorized **$5 total**. Real OpenAI Responses requests were made;
no provider doubles or scripted responses were used for the live trials. Routine
independent source/testing work used a parallel specialist with isolated file
ownership. This entry supersedes older statements that no paid calls occurred.

### Genuine consumption and execution boundary

- Venture: `bac7d94914dc4cb0813f37eab55f4bc3` (Founding live acceptance).
- **40 requests / 40 parsed responses; 350486 input tokens, 13774 output tokens.**
  Four tasks used `gpt-4.1-mini`; one explicit task override used `gpt-4.1`.
  Authentication, real model responses and native tool calls were observed.
- **$3.91808 configured estimated charges**, **$0 reserved**, **$5 company budget**;
  **$1.08192 remains** under the existing authorization and conservative accounting.
  All agents retained $10 input / $30 output per million token estimates and no
  fallback routes. These are not actual invoice charges. Provider billing/credits
  were not independently inspected; invoice reconciliation remains unavailable.
- Automatic approval review rejected lowering persisted rate estimates because it
  could weaken the budget guard. No rate/budget weakening was performed. A second
  rejection blocked bundle execution until complete executable contents had been
  inspected; inspection was completed and explicit module execution then succeeded.
- Broad network and terminal permissions remained false. Public requests and host
  tests received individual reviewed invocation approvals. Host execution retains
  current-user OS privileges and is not an OS sandbox.
- Evidence is ignored under `test-results/live-acceptance/`: sanitized task JSON,
  `usage-summary.json`, artifact manifests with SHA-256 hashes, source baseline,
  independent probes, candidate reviews and actual before/after test logs. Runtime
  tasks/artifacts persist in `data/`. No keys or CSRF tokens were recorded in docs.

### Founding results and actual limitations

1. **Strategy: FAIL independent acceptance**, despite runtime status `completed`.
   Task `27a1358c33f74b88ae376d041a93e9b8`, mini, 4 responses,
   170177 input / 3036 output tokens, estimated $1.79285. It fetched 12 real public
   URLs, encountering 403/429/404 responses, redirects and 1 MB response limits.
   It saved three memories, **zero opportunity records**, and a report. The cited
   IBM watsonx and TechCrunch AI pages independently reopened with HTTP 200, but
   did not substantiate several demand, pricing and competitor assertions. The
   report therefore fails the source/evidence gate. Selected content-creator
   concept is provisional, not a validated business opportunity. Report artifact
   `1dd8e81991824432940ea9d6b623dbc7`, SHA-256
   `d694015818441bbbd16ba87e0d1a17b054572e9e0348807b91aa18cc6ec9521e`.
   A corrective venture memory flags the unsupported claims for later agents.

2. **Software: genuine runnable output; autonomous acceptance incomplete.**
   Task `1bde5d85c416411589faf089f6eb99d8`, mini, 8 responses,
   42366 input / 5627 output tokens, estimated $0.59247. Produced a standard-library
   Python content-plan CLI, source/tests/README artifacts and actual test history.
   It recovered from file-versus-directory test discovery and a Windows `python3`
   Store-alias failure; its nine tests then passed. Independent bundle download,
   SHA-256 manifest, separate-directory nine-test run and CLI probes were real.
   Probes found `true` wrongly accepted as one post, and arrays/null raising
   tracebacks instead of clear validation errors. Windows cache binaries created
   by the Store alias also entered the task bundle; these were not executed.
   The CLI explicitly produces deterministic planning aids, **not AI-generated
   content**. No AI functionality inside that app is claimed or simulated.
   QA task `75254baa61f84a61b01292a1cd3519a1`, mini, 12 responses,
   42648 input / 445 output tokens, estimated $0.43983, imported/read actual files
   but stopped at a plan asking permission; it made no repair or test execution.
   **Operator-assisted isolated repair** in `software-repaired/` added six meaningful
   regression methods: baseline 15 tests failed (6 failures, 7 errors); after root
   object/exact-integer validation fixes all 15 passed (0.912s), plus a real
   three-post CLI smoke. Original artifact hashes stayed unchanged. This verified
   repair is not an autonomous Genesis QA pass or a validated commercial product.

3. **Self-improvement: FAIL autonomous acceptance; protection boundary held.**
   Mini task `6803b4a1b7624523a50aea66e6263bdc`, 11 responses,
   48034 input / 3015 output tokens, estimated $0.57079. Its candidate replaced
   most of toolbox.py, removed Toolbox and TLS behavior, and added a test with an
   unterminated string literal. Independently inspected, cancelled before execution,
   and preserved as rejected evidence; never promoted.
   Explicit GPT-4.1 retry `453e7ab2739b48b9b0670eacbd312681`, 5 responses,
   47261 input / 1651 output tokens, estimated $0.52214. Actual candidate tests ran:
   **100 tests, 4 errors, 1 skip, exit 1, 39.916s**. Its new tests referenced an
   invented workspace_bytes API and passed bytes to a string API; these failures
   do not establish a regression in the intended workspace_write behavior. It
   stopped at a plan rather than delivering a fix or unified patch. Runtime
   `completed` is conversational termination, not evidence of acceptance.
   All **41 tracked live-file hashes matched** the baseline after both trials.
   No generated candidate was applied to live source.

### Actual engineering repair and verified local system

Independently reproduced the real Windows workspace_write defect: LF translation
changed saved bytes and reported lengths, doubled CR in existing CRLF, and allowed
100000 LF characters to create a 200000-byte file. An **operator-assisted minimal
fix**, distinct from the rejected AI candidates, now encodes once, checks encoded
size, writes exact bytes and reports that length. It preserves every unrelated
source branch and adds four existing-API regression methods for LF/CRLF/Unicode,
artifact reports and byte limits. Focused baseline: 27 tests, five failures and one
skip; repaired focused suite: 27 tests OK, one skip. Actual evidence and applicable
patch retained in ignored `operator-toolbox-fix/`.

Integrated verification after applying only the reviewed operator patch:
- `python -m unittest discover -s tests -v`: **99 tests in 39.926s, OK,
  one Windows symlink privilege skip**.
- `node --check web/app.js`: **PASS**.
- `npm.cmd run test:e2e`: **PASS**. Fixture phases remain explicitly test-only.

Restarted the verified idle production service to load the repair, preserving
`C:\Genesis\data`. New PID **36136**, **127.0.0.1:8787 only**, health **ok**, worker
alive. Actual production Chrome check: **Connected to local server**, seven agent
forms, no page errors. Five trial tasks persisted, no pending approvals or active
work, spend/reservations unchanged. Session key intentionally disappeared on restart;
all three providers now report unconfigured. Browser screenshot was refreshed at
ignored `test-results/live-acceptance-readiness.png`.

**Exact next task:** CEO re-enters the OpenAI key in Agents & controls (required
because the tested fix was loaded by restart; never request the key in chat).
Existing $5 total authorization persists; do not reset spend or increase the budget.
Before another paid retry, improve task completion/evidence contracts so a plan or
unsupported report cannot count as acceptance, require actual opportunity_save
records and claim-specific sources, and retain independent regression/patch review.
A bounded retry may use only the remaining $1.08192 conservative allowance. If a
reservation blocks it, request further spending authorization or explicit review
of current rates; do not silently lower estimates. Full founding live acceptance
remains **NOT PASSED**. OpenAI integration is live-verified; Anthropic/Gemini and
provider invoice reconciliation remain unverified.

## Preparation checkpoint (superseded): awaiting CEO configuration

Verified 2026-11-09, Europe/Helsinki, from source commit `14857d6`.
This entry supersedes the older launch/access assertions below. Current default
shell sandbox initialization fails; reviewed elevated commands worked. Browser
computer-use and node_repl initialization also failed. No production code changed.

- The old server was stopped (health connection refused; no listener). Relaunched
  the existing service/data with `python -m genesis --data-dir C:\Genesis\data
  --port 8787`, hidden background PID **38676**. Health returns **ok** and
  **worker_alive=true**; listener verified **127.0.0.1:8787 only**.
- Opened the local Command Center URL through Windows. Separately inspected the
  actual port-8787 page with installed headless Chrome/Playwright: **Connected to
  local server**, seven agent forms, OpenAI/Anthropic/Gemini selectors, password
  field with autocomplete off, 16-step limit, no page errors. Screenshot:
  ignored `test-results/live-acceptance-readiness.png`. Desktop foreground state
  could not be independently inspected because the computer-use runtime failed.
- Runtime has **0 ventures, 0 tasks, $0 spent, $0 reserved**. All three provider
  statuses are unconfigured. Changed only the stored company budget from its $5
  default to **$0 pending explicit spending authorization**. Broad network and
  terminal permissions remain false. Maximum output is 4096 tokens per call.
- All seven agent routes remain OpenAI / `gpt-4.1-mini`, $10 input / $30 output
  per million tokens configured estimates, no fallbacks. Session setup can route
  all agents to the selected provider; review model and rates afterward. Built-in
  defaults are not a live catalog. Official OpenAI model documentation currently
  labels gpt-4.1-mini deprecated; account/model access remains unverified. Recheck
  the chosen provider's model availability before the first authorized request.
  Reference: https://developers.openai.com/api/docs/models/gpt-4.1-mini
- `python -m unittest discover -s tests -v`: **95 tests in 47.033s, OK,
  one Windows symlink privilege skip**. `node --check web/app.js`: **PASS**.
- `npm.cmd run test:e2e`: **PASS**, including production credential blocking,
  settings/rates/routes/session-key/restart/mobile checks and explicitly identified
  test-provider fixtures for tool execution, approval/denial and ZIP downloads.
  These fixtures do not establish live AI acceptance. Tests used isolated data;
  production runtime remains free of acceptance objectives.
- Prepared exact secure UI setup steps, all three founding prompts, sequencing,
  independent review gates and consumption/evidence requirements in ACCEPTANCE.md.
  No paid requests made; API consumption this preparation: **0 calls, 0 tokens**.
  Provider invoice/account balance has not been inspected.

**Exact next task:** CEO enters a key directly in the local Agents & controls
session form and explicitly approves a total USD test budget. Do not request keys
in chat. Afterward check presence only, verify chosen model/access and configured
rates, apply the authorized budget, create one founding venture and execute the
three ACCEPTANCE.md runs sequentially with source/artifact/test review. Record
actual usage and sanitized evidence here, fix real defects and reverify. Stop at
budget exhaustion rather than increasing authorization. No live acceptance pass
is claimed. Approved host subprocesses are not an OS sandbox, and local estimated
budget controls are not a provider-side hard spending cap.

## Latest verified completion: verification and local launch

At launch, effective access was verified as `kosap\ville`: ordinary shell execution
and a temporary workspace file write/read/delete succeeded. After a temporary
workspace-write restriction, the CEO restored full filesystem access. Local Git
configuration and authenticated GitHub push now succeed; approval policy remains
never. No subagents were started or reused.

- `python -m unittest discover -s tests -v`: **95 tests, OK, one Windows
  symlink privilege skip** (35.529 seconds).
- `node --check web/app.js` and `node --check tests/browser-e2e.cjs`: **PASS**.
- `npm.cmd run test:e2e`: **PASS** after fixing two test synchronization races.
  Resume now awaits its HTTP response before checking blocked status and the exact
  task/provider/model audit event. Credential rejection waits for the preceding
  clear handler to finish before entering the next input. Assertions remain intact.
  Production-browser checks cover persistence, literal XSS-safe memory, settings,
  explicit rerouting, session credentials and mobile layout. Identified test-only
  provider fixtures cover approval/denial, actual Python execution and ZIP download.
- `python scripts/verify_snapshot.py --execute`: **PASS**, 95 discovered tests,
  one symlink skip, return code 0, no timeout, unchanged candidate. Fixed the script
  to use the actual diff contract's `changed` field rather than `modified`.
  Evidence: ignored `test-results/source-snapshot-verification.json`; workspace
  `data/verification/72e8b8061a2d4c89b61f56959585de0a`. Candidate suite took 35.674s.
- Production launched with `python -m genesis --data-dir C:\Genesis\data --port 8787`
  as hidden background PID **33432**. Verified listener **127.0.0.1:8787** only,
  `/api/health` status **ok**, worker_alive **true**. Opened the actual Chrome
  command center and observed **Connected to local server** and model setup required.
  Launch state: 7 agents, 0 ventures, 0 tasks, $0 spent/reserved; no configured
  providers. Existing data was preserved. Logs remain ignored under `test-results/`.

No provider credentials exist in the launch environment and no paid model calls
were made. Session-only key entry is available in Agents & controls. Live AI
acceptance still requires a CEO-supplied key and approved spending.

## Implemented

Local Python/SQLite company OS with a connected browser command center, seven
configurable agent roles, COO delegation, venture history, organizational memory,
opportunities, durable queued jobs, approvals, artifacts/ZIP downloads and audit.
Real OpenAI Responses, Anthropic Messages and Gemini generateContent adapters;
native tool calls, configured-rate budget reservations and explicit fallback.

Controlled public HTTPS research/search, bounded workspace files, real Python
development/tests, cross-agent artifact imports and candidate self-improvement.
Source snapshots preserve protected baselines and generate actual unified patches.
Production has no mock AI provider; doubles exist only in identified test fixtures.

## Latest verified checkpoint

- Full `python -m unittest discover -s tests -v`: **95 tests, OK, one Windows
  symlink privilege skip**. This includes real subprocesses and local HTTP.
- Toolbox: 23 tests, including exact-byte Git patch application across LF/CRLF,
  missing EOF newline, additions/deletions and Unicode line separators. The saved
  restart test failure is fixed without modifying global Git configuration.
- Candidate test runner supports nested project imports and working directories;
  it reports discovered test count and treats zero tests as failure.
- Self-improvement integration observes a real regression fail, edits only the
  candidate, observes tests pass after a new approval, and downloads a patch ZIP.
  Live source stays unchanged; protected baseline files stay out of artifacts.
- Large tool results retain complete JSON evidence in artifacts, with valid bounded
  model-message envelopes. Chunked Unicode reads support inspecting evidence.
- Actual read ceilings cover concurrent growth during imports/ZIP downloads.
- Atomic approval/task/audit persistence closes crash gaps. Legacy partial approvals
  recover; cancellation cannot leave new orphan approvals or dispatch new calls
  before their durable claim points. Shutdown keeps the data lease while worker lives.
- Provider wire suite: 16 tests; accounting suite: 8 tests; server suite: 13 tests,
  all passed within the full suite. Missing either usage total charges the configured
  ceiling; explicit complete zero settles zero. Session keys are not persisted or
  echoed, and explicit route changes are audited. No live provider calls made.
- Final extended browser E2E passed, including session credentials and resume controls.

## Exact next tasks

1. Local verification and launch are complete. If the service has stopped, relaunch
   `python -m genesis --data-dir C:\Genesis\data --port 8787`; preserve that directory.
2. Credentials are absent for all three providers. The next LIVE acceptance stage
   requires a CEO-supplied key via the session-only local UI and an explicit spending
   authorization. Never ask for or store keys in chat/source/data. Review agent routes,
   configured rates, budget and requested execution approvals before acceptance.
3. Execute the three founding objectives in ACCEPTANCE.md with real providers,
   approvals and independent review, retaining actual evidence. Never count the
   infrastructure fixtures as live AI acceptance.

## Git and operations

GitHub publication completed (2026-10-17): CEO authorized safe project upload,
signed in, and restored access after earlier connector/browser permission blocks.
Repository **https://github.com/kosap89/Genesis** is **private**; connector verified
ownership and push permission. Normal authenticated Git push succeeded, publishing
the complete original history through verified implementation commit `dc92e2b`.
Local `origin` points to `https://github.com/kosap89/Genesis.git`; `main` tracks
`origin/main`. No source changes or provider calls were needed for publication.

Reviewed 87 unique blobs in local HEAD history: no runtime/credential file paths or
provider/GitHub/private-key patterns found; URL credential matches were only the
explicit `https://user:pass@example.com` rejection fixture. `.env.example` has blank
values. The 41 tracked files and all seven implementation/checkpoint commits were
uploaded through normal Git push, preserving original hashes and bytes. Runtime
data, logs, dependencies and verification output are excluded. The earlier browser
upload staging directory remains ignored under `test-results/github-upload/` and
was not uploaded. Publication changes only this operational record; the previously
verified implementation is unchanged. Next engineering task remains live acceptance
with CEO-provided credentials and explicit spending authorization, as listed above.

Prior checkpoints: `8a88138` runtime, `e6a989c` browser app, `80dade3` first restart,
`6ed5497` second restart. Later verified commits are available in `git log`.
Runtime data is ignored under `data/`; browser screenshots under `test-results/`.
No paid model calls made. Real research smoke checks already returned python.org
HTTP 200 and five actual Wikipedia discovery URLs. Brave search remains unverified.

## Remaining limits

No live provider/CEO business acceptance yet. Approved Python runs with current-user
host privileges, not an OS sandbox; credentials are scrubbed from child environment.
No external communications, purchasing, public-deploy or live-update connector.
Budget checks use configured estimates, not provider invoices or a provider-side cap.
Single-user loopback service; no multi-user auth, durable external scheduler,
retrieval compaction, OS container backend or automatic source promotion.
