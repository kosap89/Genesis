# Genesis persistent project state

Updated 2026-10-17, Europe/Helsinki. Resumed after two CEO-requested restarts.
Preserve existing implementation and data; do not scaffold a replacement.

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

- Full `python -m unittest discover -s tests -v`: **90 tests, OK, one Windows
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
- Provider wire suite: 15 tests passed before partial-usage accounting follow-up.
  No real provider account has been called.
- Earlier extended browser E2E passed (credential blocking, real persistence/XSS,
  draft preservation, settings/routing, mobile, approval/denial, actual tests and
  downloads). Final rerun for new resume controls is in progress.

## Exact next tasks

1. Finish provider partial-usage completeness metadata and conservative engine
   accounting, with regressions; do not treat an omitted output count as zero cost.
2. Collect final browser/API verification for explicit resume-with-agent-settings.
3. Rerun the relevant/final integrated checks for these last changes, commit verified
   work and record the final counts here.
4. Launch `python -m genesis` on loopback, verify health and open the actual browser
   command center. The production service has not been launched at this checkpoint.
5. Credentials are absent for all three providers. The next LIVE acceptance stage
   requires a CEO-supplied key and approved spend. Use masked `.\start.ps1` or a
   process environment variable; never ask for or store keys in chat/source/data.
6. Execute the three founding objectives in ACCEPTANCE.md with real providers,
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
