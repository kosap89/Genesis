# Genesis engineering continuity

Read `docs/STATE.md` first, then `docs/ROADMAP.md` and the relevant source/tests.
Continue the existing implementation; never replace it with a new scaffold.

The CEO authorizes routine engineering decisions, project edits, ordinary local
dependencies, debugging and testing. Use parallel specialists for bounded work
when useful, with explicit file ownership to avoid concurrent edits.

Maintain a real integrated local system. Production must never use scripted AI
responses, fake workflows, fabricated sources or invented test results. Provider
doubles belong only in tests and must be explicitly identified as such.

Before committing a subsystem, run relevant tests and repair failures. Update
STATE.md with verified evidence, limits and the exact next task. Commit source,
tests and docs to Git. Never commit credentials, runtime data, artifacts or logs.
When paused or interrupted, preserve incomplete changes as an explicitly labeled
checkpoint with remaining verification recorded; do not claim it passed.

Verification commands:

- `python -m unittest discover -s tests -v`
- `node --check web/app.js`
- `npm.cmd run test:e2e` (Playwright using installed Chrome/Edge; no paid APIs)

Never change global Git settings to accommodate tests. On this machine use
`git -c safe.directory=C:/Genesis ...` when ownership checking requires it.

Live acceptance requires a CEO-supplied provider credential and spending
authorization. Keep keys in process environment, never chat, source or objectives.
The service is single-user/loopback only. Host subprocess execution is not an OS
sandbox; preserve the approval boundary and state its actual limitations.
