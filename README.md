# Genesis — local AI company OS

Genesis runs a real browser command center backed by Python, SQLite and a durable
agent worker. Python 3.11+ is the only runtime requirement. No cloud hosting or
subscription is required by the application itself; model API usage is billable
by the provider you configure.

## Run

From this directory:

```powershell
python -m genesis
# Then open the URL below and add a key in Agents & controls when ready.
# Optional interactive launcher: asks for a hidden key, never saves it to disk.
.\start.ps1
# Or configure credentials in the launching shell:
# Configure ONE provider in this shell. Do not paste credentials into chat or Git.
$env:GENESIS_OPENAI_API_KEY = '<your key>'
# Alternatives: GENESIS_ANTHROPIC_API_KEY or GENESIS_GEMINI_API_KEY
python -m genesis
```

Open **http://127.0.0.1:8787**. You can launch without a key to inspect the command
center and organize ventures; objectives will explicitly block on credentials.
In Agents & controls, enter a provider key in the password form and save it for
this session. It stays in the server process, is never returned to the browser,
and is lost when the service stops. The optional, initially unchecked checkbox applies recommended
role routes; leaving it unchecked preserves every agent's saved configuration. No model request or task resume happens automatically.
Select provider, model and reasoning effort independently for each role. A local
preview shows approximate costs without creating an objective or calling a provider.
New OpenAI roles use Sol, Terra or Luna according to their responsibilities; legacy
routes remain available. Astra requires explicit authorization for each task,
including fallback use. See [model controls](docs/PROVIDERS.md).
New agents initially select the first configured provider. Existing agent settings
remain intact; select the provider/model in Agents & controls after changing your
setup. Provider presence is configuration detection, not a health check.

Use `--port 8788` or `--data-dir C:\path\to\private-data` if needed. Stop with
Ctrl+C. Restart using the same data directory to retain history. In-flight tasks
become interrupted and require review/resume; queued tasks continue automatically.
An OS file lease prevents two CLI processes from sharing the same data directory.
On graceful shutdown, the service retains that lease until the in-flight worker
finishes. Cancellation prevents new invocations, while already claimed work may finish.

## Operate

1. Create a venture to group its objectives, memory and deliverables.
2. Submit a natural-language objective and choose a responsible agent.
3. Inspect actual model messages, tool arguments, execution timeline and artifacts.
4. Approve individual network or host-execution requests in the approval queue.
5. Review results and download individual files or a complete task ZIP bundle.
   Create follow-up objectives as needed.

Tasks retain their original provider/model when resumed. After changing agent
configuration, use **Resume with agent settings** to explicitly change a blocked
task's route; the previous and new route are recorded in its audit history.

The COO can delegate to strategy, engineering, QA, growth, finance and operations
agents. Specialist tasks have their own model configuration and workspaces. The
COO waits for their results. They are functional prompt/tool capabilities, not
independent autonomous employees or guarantees of business success. Agents can
list and import same-venture artifacts into their own workspace for independent
QA; imports retain source attribution and content hashes in the audit log.

The three founding acceptance objectives are in [docs/ACCEPTANCE.md](docs/ACCEPTANCE.md).
They need live credentials and appropriate approvals. They have **not** been
declared passed using test doubles.

## Controls and limitations

- Service listens on loopback only. Host/origin validation, CSRF tokens, a restrictive
  browser policy and download-only artifacts protect the local HTTP boundary.
  This is a single-user local application, without multi-user authentication.
- Credentials are read from environment; the UI never returns their values. Do
  not put keys in objectives or company memory. The local credential form can set
  a process-only override protected by the same Host/origin/CSRF checks as other
  mutations. Clearing it removes that override; inherited environment credentials
  still apply. `.env` files are not auto-loaded.
- File tools reject path traversal, Windows devices, symlinks and junctions.
  Each task has a separate directory. **Approved Python/terminal execution runs
  as the current OS user and is not an OS sandbox.** Only approve trusted code;
  use a dedicated OS account/VM for untrusted objectives. Child processes receive
  a reduced environment; this does not prevent same-user access to host files.
- Per-invocation execution approvals record a workspace content digest. Changes
  after approval invalidate that decision and require a fresh review.
- Candidate test runs report the number of discovered tests. Empty discovery is
  a failure. Nested projects can set a workspace-relative test path and workdir.
- Large tool responses are kept as complete JSON artifacts, with a bounded preview
  in model history; workspace reads support Unicode character offsets and limits.
- External communication, purchases, public deployments and live source updates
  have no connector and cannot be approved as standalone product features yet.
  Host execution grants broad effective capabilities; review its exact code first.
- Self-improvement copies the source into a task workspace. Changes and tests run
  against that candidate. A preserved baseline produces a real unified patch;
  applying updates to the running service is manual review.
- Web research fetches real public HTTPS pages. Default search uses Wikipedia
  discovery; a `BRAVE_SEARCH_API_KEY` enables general web search. Source coverage
  is limited without that optional key; market claims must be checked accordingly.
- Budget enforcement uses **configured rate estimates**, not live provider invoices.
  Defaults ($10/$30 per million input/output tokens) are conservative placeholders,
  not verified prices. Known model prices can raise these guards, never lower them.
  A separate published-price registry (including cached input) estimates usage
  costs; editing reporting prices never changes budget authorization or settlement.
  Official billing remains unavailable without independent reconciliation.
  Before a call, Genesis reserves input-byte/output-token ceilings for every possible
  explicit fallback. Reported usage settles successful calls; potentially billed
  failures and interrupted reservations are charged at their configured ceilings.
  Provider tokenization, hidden usage and price changes can differ. Also set a
  provider-side spending limit. No provider-side billing limit is configured here.
- Cancellation prevents further planned calls; an already running request/process
  may finish. Ambiguous interrupted tool calls are not automatically replayed.
- SQLite preserves data locally; there is no backup service. Back up the data
  directory while the service is stopped. Logs and artifacts may hold sensitive
  company content. Keep the directory private.

## Verify

```powershell
python -m unittest discover -s tests -v
# Optional browser QA (uses installed Chrome/Edge):
npm.cmd ci --ignore-scripts
npm.cmd run test:e2e
# Optional: copy this real checkout and run its Python suite via candidate tools:
python scripts/verify_snapshot.py --execute
```

Tests explicitly use provider doubles/local HTTP fixtures. Production has no demo
provider, simulated agent mode, or fabricated business results. See
[docs/STATE.md](docs/STATE.md) for verification evidence and the exact next task,
[docs/ROADMAP.md](docs/ROADMAP.md) for remaining stages, and
[docs/TOOLS.md](docs/TOOLS.md) / [docs/PROVIDERS.md](docs/PROVIDERS.md) for contracts.

## Development authentication and spending

Develop through subscription-authenticated Codex. Check `codex login status`; do
not switch it to API-key authentication. Development and verification use local
unit tests, explicitly identified provider doubles and isolated browser E2E only.
Do not start/resume live Genesis agents or use prepaid model credits for software
development. Live acceptance requires separate CEO authorization, regardless of
any budget amount still stored in the runtime database.
