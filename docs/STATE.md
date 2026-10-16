# Genesis persistent project state

Updated 2026-10-17, Europe/Helsinki. Resumed from checkpoint `3294389`.
Preserve existing implementation and data; do not scaffold a replacement.

## Latest verified completion: verification and local launch

Effective access verified as `kosap\ville`: ordinary shell execution and a temporary
workspace file write/read/delete succeeded. Full filesystem access and network are
enabled; approval policy is never. No subagents were started or reused.

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
