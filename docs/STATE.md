# Genesis persistent project state

Updated 2026-11-09, Europe/Helsinki. Live official reporting follows verified integration `b45a809` and repeat verification `0a49725`.
Preserve existing implementation and data; do not scaffold a replacement.

## Current checkpoint: real OpenAI organization reporting connected

CEO dashboard clarification: the supplied official OpenAI screenshot shows **$0.15
organization monthly spend against a $10 organization spend limit**. This is a
CEO-supplied dashboard observation, not a Costs API result or prepaid balance.
An authorized reporting refresh at **2026-11-09 03:57:00 UTC** still returned no
monetary rows. Genesis's **$3.91808** historical internal safety ledger and
**$0.2484168** published-price estimate are separate figures. The safety ledger
uses deliberately conservative configured rates, not provider invoicing; these
historical token totals at $10/$30 per million yield $3.91808. Cache/price/reporting
differences can affect the separate estimate, which is not a verified invoice.

The financial dashboard now places official organization costs first, explicitly
labels the internal safety estimate and explains that it is not the OpenAI bill
or consumed prepaid credit. Overview and venture budget labels use the same
distinction. The empty-cost message directs comparison with the official dashboard
while API costs lag. No screenshot amount was inserted into the provider API
report, no historical charges were rewritten and no budget limits were changed.
The full browser E2E and both JavaScript syntax checks passed after this change.
New assertions cover provider-cost ordering and the internal-budget disclaimer.
A separate read-only browser check of the real running dashboard passed too;
its screenshot remains ignored under `data/billing-integration/live/`.

The CEO supplied the separate Admin credential through the local setup flow and
authorized updating Genesis from official billing data. Credential presence was
verified without reading the key. A supported manual reporting refresh succeeded
at **2026-11-09 03:45:08 UTC**, with no provider error. Official query window:
**2026-11-01 00:00:00 UTC through 2026-11-09 03:45:06 UTC**.

The official completion Usage report returned **40 requests, 350486 input tokens
and 13774 output tokens**, matching the pre-existing Genesis model usage totals.
This verifies actual Admin authentication and completion usage retrieval; it does
not establish complete coverage of every API product or automatic attribution of
all organization activity to Genesis.

The Costs request also succeeded but returned **no monetary result rows**, no
currency and no daily/project/key cost amounts. The parser's empty aggregate is
zero, but this is not a verified zero final bill. The dashboard now displays
**No cost amounts reported yet**, explains reporting delays and avoids inventing
a USD currency for an empty report. Historical Genesis estimates/conservative
charges remain separate. No prepaid balance endpoint or balance became available.

Before/after local API comparisons confirm settings, agents, tasks, ventures,
approvals and accounting unchanged. Global/project budgets remain the values
below. Admin credential stays configured in the running process; no restart was
performed. Periodic reporting remains off. No model request or agent execution
was initiated. The authorized reporting synchronization used the official Costs
and completion Usage reads; HTTP pagination requests are not individually audited
by this implementation, so no exact external request count is claimed.
Ignored private evidence: `data/billing-integration/live/summary.json` plus
before/after state snapshots. No organizational raw report or credential is
committed to Git. Only aggregate verification findings are recorded here.

Verification for the live-data display adjustment: **38 billing tests passed in
4.697s**, JavaScript/browser-test syntax and full browser E2E passed. An explicit
browser fixture now covers successful usage with an empty cost report. The first
E2E attempt timed out in an existing ordinary-key test: it could enter the next
key before the previous save handler completed its refresh/finally. The test now
waits for save completion before clearing/re-entry; the complete rerun passed.
A separate headless browser against the real running CEO dashboard verified the
configured Admin status, 40 official requests, empty cost message and no JavaScript
errors, restricting all browser traffic to local GET requests. The production
server was not restarted and the session credential remains available.

**Exact next task:** use the financial dashboard's manual refresh when updated
provider charges are needed. Costs may lag usage; do not reconcile Genesis-only
invoices, estimate prepaid credit balance, reset spending or raise budgets from
this empty cost report. Keep model credentials and any future agent-execution
authorization separate. A server restart requires re-entry of the session Admin
key through the hidden local helper.

## Previous checkpoint: official organization billing integration verified offline

Implemented the documented OpenAI Organization Costs API in a separate HTTP-server
service, with current named UTC month totals, daily costs and provider project/API
key attribution. Optional completion usage reports request/token counts by project,
key and model; it does not claim to cover all API products. The CEO dashboard keeps
these organization-wide provider figures separate from Genesis conservative
spent/reserved budgets, published-price estimates, Genesis-attributed invoice data
and remaining venture budgets. No organization-to-venture mapping is invented.

Official report timestamps/windows, delayed reporting, partial amounts, stale and
historical snapshots are explicit. Old-month totals name their month. Failures
retain the last successful report; incomplete cost pagination never publishes a
new total. Missing amounts are unavailable rather than zero, and currencies are
not mixed. Manual refresh has a minimum 30-second cooldown; optional polling
defaults off and accepts only 900-86400 second intervals. Page/response/time bounds,
cursor checks, retry backoff and shutdown/key-rotation protection are implemented.

No documented supported prepaid credit-balance endpoint was found in the official
reference as of 2026-11-09. Balance stays null/unsupported; the dashboard links to
official billing settings. There is no scraping, private endpoint, credit estimate
presented as actual balance, top-up, billing mutation or budget adjustment.
See [BILLING.md](BILLING.md) for official sources and setup/limitations.

The optional Organization Admin key is separate, server-memory/session-only and
never enters frontend JavaScript, persisted state, environment, logs or agent tools.
`python -m genesis.billing_credentials` uses hidden local input and CSRF-protected
loopback HTTP, with redirects and environment proxies disabled. No Admin key has
been requested or configured during development. Model credential paths reject
Admin keys before provider transport. Existing host execution remains unsandboxed;
application-level credential isolation is not protection from hostile same-user
host code. Existing approvals and permission controls are unchanged.

Verified evidence:

- Subscription authentication: `codex.cmd login status` reported ChatGPT login.
- `python -m unittest discover -s tests -v`: **222 tests in 91.604s, OK**, one
  existing Windows symlink privilege skip. Includes 38 deterministic billing,
  local HTTP, hidden-input and credential-isolation tests. Provider doubles are
  explicitly test-only. Conservative preflight/reservation/settlement tests pass.
- `node --check web/app.js`, browser-test syntax and `git diff --check`: pass.
- `npm.cmd run test:e2e`: pass with isolated local server, explicit browser report
  fixtures, no model APIs. Covers display distinctions, cost/usage attribution,
  failure/partial/historical/month rollover states, settings and preserved tasks/
  budgets. Screenshots are fixture evidence, not live OpenAI reporting evidence.
- Independent review found and verified fixes for local helper proxy bypass and
  previous-month metric attribution. No remaining blocking findings.
- Updated real loopback server restarted as PID **11920**, health **ok**, worker
  alive. Admin/model credentials absent, official report unavailable, periodic
  refresh **off**. All existing SQLite tables are byte-value identical row-for-row
  to the pre-restart backup: records, messages, events and sqlite_sequence.
  Before/after API settings, agents, tasks, ventures, approvals and accounting match.
  Ignored local evidence: `data/billing-integration/verification.json`, before/after
  state snapshots and SQLite backup. Runtime data/logs are not committed.

CEO-requested repeat verification after commit `b45a809`: all **222 tests passed
in 96.524s** (same one Windows symlink skip), `node --check web/app.js` and the
full browser E2E passed again. Read-only checks against the running local server
confirmed healthy worker, unchanged settings/agents/tasks/ventures/approvals/
accounting, no Admin credential, no billing synchronization attempt, and periodic
refresh off. No source defect was found; no live provider request or spending
occurred. Real Admin-key synchronization remains unverified.

Global budget remains **$8.41808**, historical conservative spent **$3.91808**,
reserved **$0**; card venture budget **$4.50**, spent/reserved **$0**. Teams, models,
documents, protected CONCEPT/DECISIONS, mission draft and all five historical tasks
are preserved. **New live model calls 0, live billing API calls 0, new tasks 0,
API-billed development consumption $0.** No real Admin-key authorization or live
provider report has been validated. Mock success does not establish live success.

**Exact next task:** optional CEO setup of a separate expiring Organization Admin
key through the verified hidden local helper, then manual reporting refresh and
inspection of the actual provider window/errors. No Admin key is needed to keep
using local financial estimates. This development request forbids live Genesis
agent execution/prepaid inference; do not submit the previously prepared card-game
mission as part of billing verification. Its prior budget authorization remains
recorded below but is not development-spending authorization.

## Previous checkpoint: $4.50 mission cap authorized; Genesis credential missing

Verified 2026-11-09, Europe/Helsinki. The CEO approved the mission spending request
but constrained it to a reported **$4.85 remaining provider credit balance**.
Applied a **$4.50 maximum additional conservative mission cost**, leaving $0.35
below that reported balance. This supersedes the earlier proposed $10 cap; no
further spending consent is needed within the newly approved scope/cap.

Through supported APIs set venture budget to **$4.50** and global absolute ceiling
to **$8.41808** (preserved historical spent $3.91808 plus $4.50). Neither spent nor
reserved balances were reset. Venture spent/reserved remain $0. Updated only the
mission policy's authorization paragraph to record this approval and the credit
constraint. Models, memberships, concurrency/step/delegation settings, network and
terminal permissions, all six documents and all five historical tasks are unchanged.

The scoped non-generating provider check still returns **missing_credentials**:
credential_configured=false, checked=false, generation_tested=false. Account
visibility for Sol, Terra and Luna remains unknown. No external provider request
was made. Opened the local password form for the sole required secret input;
Codex subscription credentials were not accessed or substituted.

Actual added tasks **0**, model calls **0**, API consumption **$0**. Historical
model audit remains 40 requests plus 40 responses. The prepared collaborative
mission has **not been submitted** because the Genesis key is still absent.
Before/after checks confirm budget writes, preservation of previous spend,
unchanged documents/models/history and no unintended execution. No source changes
or new regression tests were needed for these supported configuration updates.
Runtime evidence is ignored data/full-design-mission/budget-authorization.json.

**Exact next task:** obtain the CEO-supplied Genesis OpenAI API key securely through
the local password form/environment, never chat or Codex auth. Recheck the three
exact model IDs using the non-generating endpoint. If available, submit exactly
one saved collaborative Creative Director mission under the existing **$4.50**
cap; do not ask for the same spending authorization again. Monitor and report
actual individual delegation/network approval gates and budget/credential/
execution blockers. Do not auto-approve unknown invocations or exceed the cap.
The cap is conservative application accounting, not an independently verified
provider invoice/credit reading; do not guarantee completion within it.

## Previous checkpoint: complete autonomous design mission prepared, awaiting authorization

Verified 2026-11-09, Europe/Helsinki, continuing committed/pushed d635eb6.
Existing Card Game venture 07587388a699471aa8fdb86b958cfe3a is prepared for
CARD GAME v0.3 — FIRST COMPLETE GAME DESIGN. This is preparation only:
**no mission task was submitted, no game design/research was performed and no
paid/model/provider request occurred**.

### Concrete prepared mission

The existing venture now stores a mission_draft with the exact lead agent coo,
collaborative mode and a 7,849-character full objective. It asks for a cohesive
complete playable-on-paper rules proposal, operational evolution for all four
classes, exact two-deck starter lists and full card text, numerical examples,
multi-turn walkthrough, independent critique, revision/recheck and durable
consolidation. It requires actual delegate_task invocations and actual task IDs,
document revisions and source evidence rather than invented agent activity.

The suggested seven-child sequence is: parallel Researcher and initial Designer
proposals in one tool-call batch; Designer research integration; independent QA;
Designer fixes; independent QA recheck; Documentation Manager consolidation.
The Creative Director coordinates the entire mission. Separate document ownership
avoids parallel write conflicts; full paginated reads and expected revisions are
required when excerpts are insufficient. All results remain provisional proposals.

The project operating policy and five membership instruction texts were updated
through supported APIs. They authorize ordinary provisional design choices
without requiring CEO creative input, including complete rules/numbers and an
initial useful theme. They retain human final approval, no programming/digital
prototype, no Miro work or external actions, protected sources and honest evidence.
Execution/spending is still conditional on separate CEO authorization and a
Genesis API key. Each individual delegation/network invocation retains approval;
a mission spending authorization is not a blanket tool decision.

Exact project model/provider/reasoning/fallback configurations are unchanged:
COO Sol medium, Designer Sol high, Researcher Terra medium, Reviewer Sol medium,
Documentation Manager Luna low; engineering and finance remain disabled only in
this venture. No global agent/template or other venture configuration changed.

### Supported execution controls and UI

Added reusable execution_limits and mission_draft project configuration to the
existing system; no card-game behavior was hardcoded into source.

- Project concurrency **3**, bounded by intentional global capacity **3**.
  Steps per task **24**; maximum output per request **16,384 tokens**;
  delegation depth **1** and total children per root **10** (seven planned,
  three buffer). Concurrency is a ceiling, not promised simultaneous activity.
- Project step/output/delegation keys override inherited global defaults.
  Concurrency respects both scopes under the shared admission/reservation lock.
  Capped projects do not starve other eligible work. Limits apply live at each
  next request/delegation; model/instruction snapshots remain unchanged.
- Global defaults remain 16 steps, 4,096 output tokens, depth one/eight descendants
  for projects without overrides; only the global concurrency capacity changed
  from one to three. Other ventures without a cap inherit that global capacity.
- Project UI exposes inherited/effective limits and a saved draft editor.
  Load prepared mission selects the exact lead and mode, resets objective-specific
  authorization and fills the form without submitting work or reserving money.
  Deep link opened:
  http://127.0.0.1:8787/?venture=07587388a699471aa8fdb86b958cfe3a&view=overview&mission=1
- Runtime budgets, scoped settlement/recovery and individual delegation approval
  were not weakened. Drafts/limit objects cannot set credentials, permissions or
  reset spent/reserved. Full generic documentation is in MISSIONS.md.

### Credential/model readiness and proposed spending

All Genesis providers are currently **unconfigured**. Codex login remains
**Logged in using ChatGPT**; its authentication was not read or reused as a Genesis
API credential. Only the API secret itself requires CEO input through the local
password form or an explicitly supplied Genesis environment credential.

Official OpenAI documentation was searched and fetched, confirming the exact saved
public IDs and supported reasoning levels:
https://developers.openai.com/api/docs/models
https://developers.openai.com/api/reference/resources/models/methods/list
Public listing does not establish this account's access, quota or live inference.

Added guarded POST /api/providers/openai/check, optionally scoped by venture_id.
It derives exact enabled primary/fallback model IDs and reads only the service
process Genesis/OpenAI API environment. With a key it uses fixed GET /v1/models,
10-second timeout, 2 MiB maximum response and no redirects, never generation.
It accepts no key in the request; no secrets or provider error bodies are echoed
or audited. generation_tested always remains false. Without a key it makes no
external request.

Actual scoped readiness result: missing_credentials, credential_configured=false,
checked=false, generation_tested=false; gpt-6.1-sol, gpt-6.1-terra and gpt-6-luna
availability all **null/unknown**. This is a genuine blocker, not a successful
account check. No model was silently substituted and no billable probe was made.

**Budgets remain unchanged and no new spending is authorized:**
global ceiling $5; spent $3.91808; reserved $0; remaining **$1.08192**.
Venture budget **$0**, spent/reserved $0. Network and terminal globals remain false.

Proposed maximum additional mission spending is **$10 total from now**, across the
root and all descendants, not $10 per agent. If separately approved with balances
unchanged, set venture budget to $10 and the company ceiling to **$13.91808**
(existing spent + $10); do not reset existing spent/reserved. Re-read all balances
and reservations first. The cap is enforced through conservative configured
charges, not a provider invoice/guarantee. It may stop the mission before completion
when the next full reservation cannot fit. Do not enlarge it silently.

Read-only root preview: initial configured reservation **$0.86831**, published-price
initial-call maximum-output estimate $0.18268; its $4.38432 fixed-context 24-step
approximation is for the selected root task only and excludes delegated work and
context growth. These are assumptions, not a full-mission cost guarantee. All
reported invoice/hidden usage limits from earlier checkpoints remain unchanged.

### Genuine verification and preserved data

- Final python -m unittest discover -s tests -v: **184 tests in 116.229s, OK,
  one Windows symlink privilege skip**. Twelve new tests exercise scoped caps,
  direct three-request concurrency, scheduler fairness, live preflight reductions,
  draft nonexecution, budget/metadata isolation and safe read-only provider checks.
- node --check web/app.js and tests/browser-e2e.cjs: **PASS**.
- Final npm.cmd run test:e2e: **PASS** on isolated servers/data. Verified project
  limits/inheritance, unchanged global default settings from project edits, draft
  persistence, exact agent/mode load, restart/deep link, zero implicit tasks/
  approvals/Astra grants and previous document, security and actual fixture test
  workflows. Provider doubles are explicitly isolated tests only.
- Independent actual-data verification after API configuration and again after
  restart: saved draft hash/lead/mode, five exact effective routes, project policy,
  all six document contents/metadata/histories, both protected locks and all
  original tasks pass. On an isolated actual-database snapshot, all five roles
  could read the documents and were denied protected writes; engineering/finance
  remained unavailable. No generator or new task was used for these probes.
- Global agents/templates, all other venture records, permissions/budget balances,
  task history, memories/opportunities/artifacts and pending approval state are
  unchanged. All six authoritative game documents, including CONCEPT.md revision
  2 and DECISIONS.md revision 1, are exactly unchanged; no design proposal was
  recorded as human approved.
- Historical audit remains **40 model requests + 40 responses = 80**. Existing
  five tasks unchanged; added tasks **0**, model calls **0**, external provider
  requests **0**, additional API consumption **$0**.
- Local service restarted only after verifying idle terminal tasks, no pending
  approvals/reservations and no process credentials. Persistence was checked without
  reapplying configuration. Healthy worker and loopback listener
  **127.0.0.1:8787**, PID **34696**. Prepared collaborative form opened.
- Private mission text, before-state/SQLite backups and verification/readiness
  evidence remain under ignored data/full-design-mission and data helper scripts.
  Generic source/tests/docs alone are committed; no runtime data, logs or keys.

### Exact next task / required gate

**Await explicit CEO authorization for the maximum additional spending cap and a
Genesis API credential. No mission submission until both exist.** The operator
will configure the approved limits through APIs; the CEO need not configure
agents, mission scope or budgets manually. After securely supplied key, use the
non-generating model check to verify the three exact account-visible IDs. Report
credential/availability errors instead of changing models or borrowing Codex auth.

With explicit spending approval, recheck balances, record authorized execution
scope, apply the approved absolute global/project ceilings, then POST exactly one
collaborative root task led by coo using the saved full objective and preserved
model settings. Monitor real execution, durable revisions and usage. Every pending
delegation and network approval remains a genuine review gate; report the exact
invocation and do not auto-approve it from general spending consent. Independently
check completed documents and review/fix evidence. Stop honestly on actual budget,
credential, permission, execution or completeness failures; never fabricate success.



## Previous checkpoint: complete human concept v0.2 restored and verified

Verified 2026-11-09, Europe/Helsinki, continuing committed/pushed dd3270b.
Existing venture 07587388a699471aa8fdb86b958cfe3a and existing document
bbda5e47682d4ddfb7864b7a5db7d1b8 were retained; no new venture or CONCEPT.md
was created. No application source changes were needed.

- CONCEPT.md is now **revision 2**, kind **reference**, read_only **true**,
  attributed to CEO/human source. Stored all ten sections from the supplied
  original, with only line-ending/trailing-newline normalization: **7,984
  characters / 8,004 UTF-8 bytes**. SHA-256:
  c28b6e205f9b94b9dc9a1ecc8607e13469e647a17c4053324f6156b35f6ffd86.
  The gameplay examples remain provisional, not approved requirements. The future
  theme exploration and Miro workflow were preserved; neither was initiated.
- Revision 1, its complete content, author/timestamps and all prior history remain
  unchanged. The original attachment and complete private source remain outside
  Git; authoritative content is in the existing venture document database.
- Removed only obsolete source-availability notices: GAME_DESIGN.md now references
  the complete human source (revision 2); OPEN_QUESTIONS.md no longer lists missing
  original source as an unresolved issue (revision 2). Their prior revisions and
  all other content were preserved. Updated only the corresponding obsolete
  sentence in the venture operating policy; the prior policy is retained in the
  local before-state/database backup. IDEAS.md, REVIEWS.md and especially
  **DECISIONS.md remain byte-for-byte and metadata-for-metadata unchanged**.
- All six document IDs and the six-document structure remain unchanged. Agent
  memberships/instructions, provider/model/reasoning settings, role templates,
  global agents, budgets, permissions, tasks, memories, opportunities and task
  artifacts were compared before/after and preserved exactly. Only the three
  authorized document records and the venture policy sentence changed; old
  unrelated database records, every original message and every audit entry remain.
- Downloaded restored content and checked exact equality and hash. Independently
  re-extracted the concept from the supplied attachment and compared it with the
  persisted document after restart; **PASS**. The existing command center document
  view was opened for the venture.
- Verified all five participating roles on an isolated copy of the actual database
  using a router that raises on any generation call. All could read the complete
  revision and received the full concept in source context (not truncated);
  all were denied edits to the protected human reference. No task was created
  or model invoked to perform these checks.
- Existing targeted offline regressions: **9 document tests in 1.008s, PASS**;
  **8 venture context/HTTP tests in 3.844s, PASS**. No code changed, so the full
  172-test/browser suites were not rerun for this document-only operation.
- Restarted only after confirming idle terminal tasks, no pending approvals,
  no reservations and no process credentials. Without reapplying any updates,
  complete content, exact document IDs, revisions, locks, configuration and history
  all passed verification again. Service is healthy at **127.0.0.1:8787**, worker
  alive, PID **21420**.
- Added tasks **0**, added model calls **0**, paid token/API consumption **$0**.
  Historical audit remains **40 requests + 40 responses**. Five original tasks
  remain unchanged. Project budget **$0**, global budget **$5**, conservative spent
  **$3.91808**, reserved **$0**; no budget or permission changes occurred.

Runtime before-state/SQLite backup, restoration script, extracted source, hashes
and verification evidence are local under ignored data/concept-restoration and
data helper scripts. No private concept content, database, credential or runtime
artifact is included in the continuity commit.

**Next task / STOP:** the complete original concept is restored. Wait for a separate
CEO-authorized design assignment and budget. Do not research, run agents, create
design objectives, program a prototype or create a Miro board/integration. Existing
live-provider availability and quality limits remain unverified; this operation
verifies source restoration and access protection only.



## Previous checkpoint: card game organization prepared, no design execution

Verified 2026-11-09, Europe/Helsinki, continuing commit df814e1. Development
authentication remains **Logged in using ChatGPT**. No Genesis task was created,
resumed or executed, no design research/playtest was performed and no paid model
request occurred. This is preparation, not live design or founding acceptance.

### Configured venture and organization

Exactly one **Card Game — Concept Development** venture exists:
07587388a699471aa8fdb86b958cfe3a. Open
http://127.0.0.1:8787/?venture=07587388a699471aa8fdb86b958cfe3a&view=team
or use view=documents for its durable assets.

The existing role IDs are reused through venture-specific memberships; no global
agent or reusable role template was rewritten.

- COO / Creative Project Director: OpenAI gpt-6.1-sol, medium.
- Strategy / Lead Game Designer: OpenAI gpt-6.1-sol, high.
- Growth / Comparative Game Researcher: OpenAI gpt-6.1-terra, medium.
- QA / Critical Game Design Reviewer: OpenAI gpt-6.1-sol, medium.
- Operations / Design Documentation Manager: OpenAI gpt-6-luna, low.
- Engineering and finance: disabled only in this venture, no active assignment;
  their global configurations remain unchanged.

Each participating membership stores the requested specialization, instructions
and responsibilities, plus explicit provider/model/reasoning overrides and empty
fallbacks. Venture operating policy preserves human creative authority, provisional
mechanics, physical playability, evidence distinctions, durable results, no initial
programming/worldbuilding, and individual delegation approval. Project instructions
do not grant global permissions. The venture budget is **$0** as an execution
barrier pending the separately authorized first design assignment. Global controls
remain unchanged: budget $5, conservative spent $3.91808, reserved $0, concurrency 1.

### Source documents and reusable functionality

Six actual venture documents are stored durably in the existing SQLite database,
not only in task workspaces: CONCEPT.md, GAME_DESIGN.md, IDEAS.md, DECISIONS.md,
OPEN_QUESTIONS.md and REVIEWS.md. All currently have one immutable revision.
CONCEPT.md preserves every known fact supplied in the configuration request,
including the four placeholder evolution classes and proposed battle/resource/
reserve/evolution mechanics. **The complete original v0.2 source was unavailable**;
the reference explicitly states that it is incomplete. No missing rules or values
were invented. Other documents provide an unfilled structure and distinguish
provisional ideas, absent evidence and human approval; no actual design work is
represented as complete.

Already available: ventures, global role templates/agents, persistent memberships,
project model overrides, budgets, task artifact storage and downloads, approvals,
read-only estimates, and concurrency controls.

Added as general features, with no card-game behavior hardcoded into source:

- Membership-level system_instructions and specialization, separate from global
  instance defaults; project operating_policy; explicit UI editors. New tasks pin
  effective instructions/policy; plain resume retains them and explicit resume
  with agent settings can refresh them.
- VentureDocuments using records kinds venture_documents and
  venture_document_revisions, immutable full revisions, source actors, timestamps,
  safe filenames, duplicate-name rejection, project isolation and optimistic
  expected_revision updates. Reference locks and human-only decision documents
  are enforced against agent tools. CEO revisions preserve history.
- CEO project document viewing, creation, revision, full history and actual file
  downloads; project deep links. Existing task artifacts remain unchanged.
- Agent document list/read/propose/update tools scoped to active membership.
  Proposal creation cannot promote content into approved decisions. Current source
  excerpts include revision/lock/truncation metadata; full reads are paginated.

Application source and generic operational instructions are documented in
VENTURE_DOCUMENTS.md and ARCHITECTURE.md. Actual venture instructions, baseline
content, local backups, configuration/verification scripts and runtime evidence
remain in ignored data/test-results locations, outside Git.

### Genuine verification

- Full regression: **172 tests in 111.364s, OK, one Windows symlink privilege
  skip**. Seventeen new tests cover document durability/revisions/concurrency,
  protected decisions/references, cross-project isolation, membership instruction
  snapshots, actual agent tool dispatch without generation, and real HTTP APIs.
- node --check web/app.js and node --check tests/browser-e2e.cjs: **PASS**.
- npm.cmd run test:e2e: **PASS**. Isolated production-mode server had provider
  credentials removed. Verified project/global instruction separation, policy,
  document create/revise/history, actual downloaded bytes, restart persistence,
  deep links, venture isolation, mobile layout and existing execution/approval
  paths. Provider doubles were confined to the explicitly identified fixture.
  Synchronization exposed async form reset/editor draft issues and the global
  save flow was repaired to preserve unsaved venture fields.
- Independently reviewed protections: spoofed actor/kind cannot approve decisions;
  references remain unchanged; wrong-venture IDs, stale revisions and removed
  memberships are rejected. The local HTTP integration tests also verify CSRF
  and forbidden permission fields.
- Applied configuration through local APIs. A retry-script error initially created
  an unused duplicate; uniqueness checks detected it. After a local backup, only
  that new duplicate and its 19 membership/document/revision records were removed
  while the service was stopped, with an audit event retained. The corrected
  idempotent preparation preserves existing documents instead of overwriting them.
  Final state contains exactly one Card Game venture.
- Restarted the configured real service **without reapplying configuration**.
  Verified all five intended routes and project-specific prompts on an isolated
  snapshot with a router that raises if invoked; all five could read all six
  documents and were denied changes to CONCEPT.md and DECISIONS.md. Engineering/
  finance remain unavailable in this venture. Downloaded all six actual documents,
  checked hashes and revision-one content against saved preparation evidence.
- Compared the pre-configuration SQLite backup against the current database:
  **all 144 original raw records and every original message/audit entry are
  preserved exactly**. Derived project_ids in API agent displays appropriately
  reflect new memberships; underlying global agents are unchanged.
- Real model audit totals remain **40 requests + 40 responses = 80 events**.
  Existing five tasks remain unchanged. Added tasks **0**, added provider calls
  **0**, added API consumption **$0**. All providers are currently unconfigured.
- Current service: **127.0.0.1:8787**, PID **15668**, health ok, worker alive.
  CEO Command Center opened directly on the configured venture. There are two
  ventures total (one original plus this one), seven unchanged global agents,
  seven new venture memberships (five enabled), and six durable venture documents.

### Limits and exact next task

STOP CONDITION reached. **Wait for a separate CEO-authorized first design
assignment and budget. Do not start design research, prototype construction or
paid agents.** The complete original v0.2 text may be added later by the CEO in a
preserved reference revision; until then the source remains explicitly incomplete.

Preferred models are configured, but account availability/live compatibility is
unverified. No provider credential is needed for this prepared state. Before
authorized paid execution, a process-only key and an explicit venture budget are
still required. Global permissions and individual delegation/host/network approval
boundaries remain intact; operating policy is an instruction, not an OS sandbox.
Approved host processes can access same-user files and are outside document-tool
locks. This remains a single-user loopback application.

Document content is stored as SQLite assets with downloadable filenames, not
authoritative files in task directories. CEO revisions may change locked source
content while immutable history preserves earlier versions. Service content limit
is 200,000 characters, while HTTP JSON requests remain bounded to 128 KiB. Prompt
excerpts and paginated tool reads are bounded; very large archives are not fully
included automatically. These are configuration/infrastructure checks, not proof
of live agent quality, game balance or successful founding acceptance.



## Previous checkpoint: dynamic project teams, offline verified

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
