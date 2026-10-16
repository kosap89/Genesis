# Genesis implementation roadmap

Mission: deliver a real, locally operated AI company OS with durable venture history,
provider independence, controlled tools, and reviewable execution.

## Stages

1. **Verified — durable execution core:** SQLite state, background worker,
   task recovery, approvals, budget reservations, audit and artifact registry.
2. **Implemented; live provider calls unverified — real integrations:** OpenAI, Anthropic and Gemini tool adapters;
   isolated task workspaces, public web research, development/test tools.
3. **Verified — CEO command center:** connected portfolio, objective submission,
   task history, agent configuration, approvals, memory, costs and artifacts.
4. **In progress — expanded verification:** unit/security tests, HTTP integration tests and browser
   end-to-end verification. Provider doubles are tests only.
5. **Pending credentials — live acceptance:** run the three founding acceptance
   objectives using real provider credentials. Report actual artifacts and costs.
6. **Next hardening:** OS-level process isolation, richer research sources,
   independent acceptance evaluators, external action connectors with approvals.

## Session protocol

After each verified subsystem, update STATE.md and commit source and tests. Never
commit credentials, runtime database, or task workspaces. On interruption, write
the exact next command/task into STATE.md. No live acceptance is claimed from doubles.
