# Persistent project state

Started 2026-10-17 (Europe/Helsinki). Repository initially empty.

## Current implementation

Implemented durable Python/SQLite execution, seven configurable specialist roles,
COO delegation, OpenAI/Anthropic/Gemini adapters, controlled tools, per-invocation
approvals, configured-rate budget reservations, artifacts, audit, and a connected
dependency-free browser command center. No paid API calls made.

## Verified checkpoint

- `python -m unittest discover -s tests -v`: 37 tests, all successful, one Windows
  symlink privilege skip. More API/accounting tests are being added.
- `npm.cmd run test:e2e`: PASS in installed headless Chrome. Production app tested
  through browser for venture creation, credential blocking at zero cost, memory,
  restart persistence and mobile layout. A separately launched, explicitly labeled
  test fixture verified browser approval, real Python tests and artifact downloads.
- Browser screenshots saved under ignored `test-results/` (production + fixture).
- Missing credentials have zero charges; failed transports and fallback requests
  have conservative reservations. Interrupted tool invocations are not replayed.

## Exact next task

**PAUSED at CEO request for computer restart (2026-10-17). Do not restart from scratch.**

Verified commits: `8a88138` (runtime) and `e6a989c` (browser command center).
The next checkpoint commit preserves the additional subsystem work in progress;
that checkpoint is not a claim that the entire new diff passed regression tests.

Resume with these steps:

1. Read this file, ROADMAP.md and README.md; inspect `git status`/latest log.
2. Finish/review `self_improvement_diff` in toolbox.py and its tests. Final agent
   toolbox run: 17 tests, 15 pass, one Windows symlink skip, one failure solely at
   test_toolbox.py:137: LF assertion vs actual preserved CRLF patch. Normalize
   `result['patch'].replace('\r\n','\n')` in that assertion or make fixture write
   LF bytes; then rerun. Earlier mid-edit `shutil` error has been removed.
3. Run `python -m unittest discover -s tests -v`, then
   `node --check web/app.js` and `npm.cmd run test:e2e`; repair actual failures.
4. Review task ZIP download tests/UI and latest architecture docs. Check new
   read-only baseline files are excluded from artifact bundles/registry.
5. Harden artifact_import to use a bounded 100001-byte read (current stat-then-read
   has a concurrent growth race). Ensure tool result truncation retains valid JSON
   and a full-result artifact rather than slicing JSON at 40000 characters.
6. Commit verified subsystem changes and update this file with final test counts.
7. Launch the actual app `python -m genesis` (or `.\start.ps1` for a masked key
   prompt) and verify health/browser. No production service is currently running.
8. No AI provider credentials are configured. Only after the CEO supplies one,
   run the three LIVE objectives in ACCEPTANCE.md within an approved budget.

Additional work preserved after the verified checkpoint:

- Same-venture artifact_list/artifact_import with content hashes and audit; six
  handoff tests pass including actual QA tests on imported engineering files.
- Six accounting regression tests and eleven HTTP API tests pass individually.
- OS CLI data-directory lease (two tests pass), masked start.ps1 launcher, new
  agents initially select the first configured provider.
- Workspace digest invalidates changed-code execution approvals (test passes).
- Child environment scrub verified by real subprocess test; no provider secrets
  inherited. Executed code still has current-user host privileges.
- Task ZIP bundles implemented, frontend link added; rerun test_server.py for the
  latest ZIP byte assertion. Extended browser/config/XSS/polling draft/denial tests
  passed before the latest ZIP link addition. node syntax check passed. Architecture
  docs and waiting_children UI filtering/metrics completed.
- Real research tool smoke checks succeeded: python.org HTTPS returned 200 and
  Wikipedia discovery returned five actual source URLs. Brave API unverified.

No task/test server processes were running at the pause checkpoint. Runtime data
and ignored browser screenshots remain on disk. All credentials absent; zero paid
model calls made. The last complete clean full suite before latest additions was
55 tests (one Windows symlink privilege skip); later individual tests passed, and
the subsequent full suite's snapshot error requires the fresh run above.

## Verification boundaries

No production API calls have been verified. No CEO business objectives have run.
Subprocess isolation is a working directory boundary, not an OS security sandbox.
