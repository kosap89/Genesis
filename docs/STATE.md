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

Finish the API/accounting regression tests and environment scrub, add cross-agent
artifact handoff, rerun relevant verification, and launch the actual application.
Then configure a provider via environment when CEO supplies credentials and run
the three objectives in ACCEPTANCE.md. Preserve this checkpoint and existing data.

## Verification boundaries

No production API calls have been verified. No CEO business objectives have run.
Subprocess isolation is a working directory boundary, not an OS security sandbox.
