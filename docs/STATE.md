# Genesis persistent project state

Updated 2026-11-09, Europe/Helsinki. Current preparation follows source commit `14857d6`.
Preserve existing implementation and data; do not scaffold a replacement.

## Current checkpoint: live acceptance prepared, awaiting CEO configuration

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
