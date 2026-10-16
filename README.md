# Genesis — local AI company OS

Genesis runs a real browser command center backed by Python, SQLite and a durable
agent worker. Python 3.11+ is the only runtime requirement. No cloud hosting or
subscription is required by the application itself; model API usage is billable
by the provider you configure.

## Run

From this directory:

```powershell
# Configure ONE provider in this shell. Do not paste credentials into chat or Git.
$env:GENESIS_OPENAI_API_KEY = '<your key>'
# Alternatives: GENESIS_ANTHROPIC_API_KEY or GENESIS_GEMINI_API_KEY
python -m genesis
```

Open **http://127.0.0.1:8787**. You can launch without a key to inspect the command
center and organize ventures; objectives will explicitly block on credentials.
In Agents & controls, choose the configured provider and its model for each role.
For a Gemini-only or Anthropic-only setup, configure the COO and specialist roles
you plan to use. Provider presence is configuration detection, not a health check.

Use `--port 8788` or `--data-dir C:\path\to\private-data` if needed. Stop with
Ctrl+C. Restart using the same data directory to retain history. In-flight tasks
become interrupted and require review/resume; queued tasks continue automatically.
Do not run two Genesis processes against the same data directory.

## Operate

1. Create a venture to group its objectives, memory and deliverables.
2. Submit a natural-language objective and choose a responsible agent.
3. Inspect actual model messages, tool arguments, execution timeline and artifacts.
4. Approve individual network or host-execution requests in the approval queue.
5. Review results and download files. Create follow-up objectives as needed.

The COO can delegate to strategy, engineering, QA, growth, finance and operations
agents. Specialist tasks have their own model configuration and workspaces. The
COO waits for their results. They are functional prompt/tool capabilities, not
independent autonomous employees or guarantees of business success.

The three founding acceptance objectives are in [docs/ACCEPTANCE.md](docs/ACCEPTANCE.md).
They need live credentials and appropriate approvals. They have **not** been
declared passed using test doubles.

## Controls and limitations

- Service listens on loopback only. Host/origin validation, CSRF tokens, a restrictive
  browser policy and download-only artifacts protect the local HTTP boundary.
  This is a single-user local application, without multi-user authentication.
- Credentials are read from environment; the UI never returns their values. Do
  not put keys in objectives or company memory. `.env` files are not auto-loaded.
- File tools reject path traversal, Windows devices, symlinks and junctions.
  Each task has a separate directory. **Approved Python/terminal execution runs
  as the current OS user and is not an OS sandbox.** Only approve trusted code;
  use a dedicated OS account/VM for untrusted objectives. Child processes receive
  a reduced environment; this does not prevent same-user access to host files.
- External communication, purchases, public deployments and live source updates
  have no connector and cannot be approved as standalone product features yet.
  Host execution grants broad effective capabilities; review its exact code first.
- Self-improvement copies the source into a task workspace. Changes and tests run
  against that candidate. Applying updates to the running service is manual review.
- Web research fetches real public HTTPS pages. Default search uses Wikipedia
  discovery; a `BRAVE_SEARCH_API_KEY` enables general web search. Source coverage
  is limited without that optional key; market claims must be checked accordingly.
- Budget enforcement uses **configured rate estimates**, not live provider invoices.
  Defaults ($10/$30 per million input/output tokens) are conservative placeholders,
  not verified prices. Set rates in Agents & controls to bound all configured routes.
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
```

Tests explicitly use provider doubles/local HTTP fixtures. Production has no demo
provider, simulated agent mode, or fabricated business results. See
[docs/STATE.md](docs/STATE.md) for verification evidence and the exact next task,
[docs/ROADMAP.md](docs/ROADMAP.md) for remaining stages, and
[docs/TOOLS.md](docs/TOOLS.md) / [docs/PROVIDERS.md](docs/PROVIDERS.md) for contracts.
