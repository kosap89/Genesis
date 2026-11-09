# Genesis implementation roadmap

Mission: deliver a real, locally operated AI company OS with durable venture history,
provider independence, controlled tools, and reviewable execution.

## Stages

1. **Verified — durable execution core:** SQLite state, background worker,
   task recovery, approvals, budget reservations, audit and artifact registry.
2. **OpenAI live calls verified; other providers unverified — real integrations:** OpenAI, Anthropic and Gemini tool adapters;
   isolated task workspaces, public web research, development/test tools.
3. **Verified — CEO command center:** connected portfolio, objective submission,
   task history, agent configuration, approvals, memory, costs and artifacts.
4. **Verified — expanded verification and local launch:** 123 unit/security/HTTP
   tests (one Windows symlink privilege skip), browser E2E, partial-usage accounting,
   session credentials and real checkout candidate verification passed. Production
   is launched on loopback with healthy worker and the browser command center open.
   Provider doubles are tests only. Local regression suite now has 123 tests
   (one Windows skip); browser E2E passes after the byte-preservation repair.
5. **Executed; acceptance failed independent review:** real OpenAI founding trials
   made 40 calls within the authorized $5 estimated budget. Strategy evidence,
   autonomous QA and self-improvement deliverables did not pass. Operator-assisted
   repairs are verified separately. Strengthen evidence/completion contracts before
   a bounded retry; see STATE.md for usage and session-key restart requirements.
6. **Verified offline model/accounting controls:** modern role-based OpenAI catalog,
   persistent reasoning, explicit Astra authorization, separate published-price
   reporting and unchanged conservative budget protection. No new live API calls.
7. **Verified offline dynamic teams:** reusable/custom role templates, unlimited
   UUID instances, project memberships/overrides, independent/collaborative modes,
   individually approved delegation, dependencies, independent review, explicit
   artifact handoffs and collaborative file claims. Atomic scoped budgets and
   configurable concurrency defaulting to one. 155 tests (one Windows skip),
   browser E2E and real-data migration preservation verified; zero new API usage.
8. **Verified venture preparation:** project-only instructions and operating policy,
   durable revisioned source documents, protected references/human decisions and
   agent source tools. Card Game venture prepared with five scoped roles and six
   assets, restart verified, original records preserved. 172 tests (one Windows
   skip) and browser E2E pass. No design tasks or paid calls; await CEO assignment.
9. **Next hardening:** OS-level process isolation, richer research sources,
   independent acceptance evaluators, external action connectors with approvals.

## Session protocol

After each verified subsystem, update STATE.md and commit source and tests. Never
commit credentials, runtime database, or task workspaces. On interruption, write
the exact next command/task into STATE.md. No live acceptance is claimed from doubles.
