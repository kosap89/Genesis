# Prepared missions and project execution limits

A project may store a mission_draft containing objective text, the exact agent_id
and work_mode. Saving/loading it does not create a task, reserve a budget, grant
Astra authorization, approve tools or contact a provider. The CEO Command Center
can load the draft into the objective form for review; it never submits it
automatically. A deep link with mission=1 loads it once after project state arrives.

POST /api/projects/<id> accepts mission_draft (or null to clear it). The objective
must contain 1–24,000 characters, the lead must be an active project team member,
and mode must be independent or collaborative. Drafts and limits use the existing
venture record and survive restart. Loading a draft resets objective-specific
authorization rather than inheriting a previous form's permission.

## Execution controls

The same project endpoint accepts execution_limits with any of:

- max_concurrency: 1–16.
- max_steps: 1–100 model turns per task.
- max_output_tokens: 1–32,768 per request.
- max_delegation_depth: 0–8.
- max_delegated_tasks: 1–100 total descendants per root.

An empty object inherits global defaults. Missing keys inherit their corresponding
global setting. Project step/output/delegation values override global defaults;
the effective concurrency is the smaller of project concurrency and the global
worker/request capacity. The UI shows both. These are live controls: next request
and delegation checks use current limits, including reductions made during request
preparation. They do not rewrite the task's pinned model, reasoning or instructions.

Admission is serialized with budget reservations. Scheduler jobs and directly
started requests respect the global and project concurrency boundaries. A capped
project is skipped so other eligible projects can use remaining capacity.
Increasing capacity is not a requirement to use every slot and does not itself
consume tokens. Other projects without overrides continue to inherit global
defaults; raising global capacity must be an intentional operator decision.

Budgets and permissions are separate fields. Project limits/drafts cannot reset
spent/reserved balances, supply credentials, enable host execution or start work.
Explicit CEO project autonomy and local budget enforcement are separate controls,
described below. Accounting continues even when local budget admission is disabled.

## Collaboration and acceptance

A collaborative root can propose delegation to specific eligible project agents.
By default, each proposed invocation needs individual CEO approval. A CEO can
instead grant that project `autonomy: {delegation: true, research: true}` through
the project API/team UI. Delegation then runs without per-call prompts only for
explicitly active/enabled members of that project; public research can run without
per-call prompts only for the two research tools. Authorizations are audited as
project-policy decisions, never fabricated human approvals. Other projects remain
manual unless separately configured. Explicit denials still win; host execution
and other capabilities are not granted by these flags.

The live policy is checked at the invocation claim under the engine guard. Turning
it off affects future claims; in-flight work may finish. Earlier pending requests
superseded by policy are expired with provenance when executed, not left pending.
Ambiguous interrupted invocations are still not replayed automatically. Existing
waiting tasks require explicit resume; changing policy alone does not submit work.

The root waits while any existing child is nonterminal. To start independent work
in parallel, propose those delegations together in one model response. Dependencies
can refer only to existing same-project tasks and cannot create ancestor deadlocks.
Independent review references actual author task IDs and requires a different
agent from every contributing author. Review of the root by its own descendant
would create a dependency cycle and is rejected.

`depends_on` requires successful completion. `review_of` identifies contributing
authors and waits until those tasks are terminal; failed or cancelled authors may
have saved partial work that needs independent review. Such a review does not
mark its sources successful or replay them. Listing a task in both fields still
requires its success. Source status, errors and artifact handoffs remain visible
to the reviewer, and project, author-independence and cycle checks still apply.

Give parallel agents separate document ownership. Use explicit current revisions,
read full sources through paginated document tools, and serialize consolidation
of shared documents. Use real task IDs, revisioned output, independent findings
and a documented fix/recheck cycle to assess completion. Runtime completed alone
is not acceptance. No missing model calls, references, tests or approvals may be
invented.

## Spending authorization

Local budget enforcement defaults on. The CEO can set global
`budget_enforcement_enabled: false` through `/api/settings` or the controls UI.
This disables admission checks for all local global/project/agent dollar caps;
reservations, estimates, historical charges and settlement remain reporting data.
UI marks this tracking-only mode. It grants no network/host permissions, raises
no provider limits and does not remove step/concurrency/delegation controls.
Provider spend/quota failures remain real errors, not permission to retry forever.

When using local budget caps:

Before submitting a draft, report a maximum additional mission spending cap and
wait for explicit CEO authorization. With no reservations, a company-wide
additional cap B can be represented by global budget = existing spent + B and a
new venture allocation no larger than B (or spent + B for a previously used
venture). Re-read balances and unrelated reservations before changing limits.
Do not reset spent/reserved or count a past authorization as permission for a new
mission. A shared global ceiling can also be consumed by other work.

Configured charges and reservations are conservative estimates, not provider
invoices or a provider-enforced guarantee. Include all descendants in the venture
cap. The mission can block before completion when it lacks the next request's
full reservation. Do not silently enlarge the cap or change models.

Genesis credentials must be supplied through its process environment or local
password form. Codex subscription authentication is separate and must never be
read or reused as a Genesis credential. A missing key is a genuine execution
blocker. A listed public model does not prove account access or successful live
generation.


## Non-generating provider readiness

POST /api/providers/openai/check with an optional venture_id checks the exact saved
enabled OpenAI primary/fallback model IDs. The endpoint accepts no credential
field and uses only the Genesis service process key. Without a key it reports
missing_credentials and makes no external request. With a key it uses the fixed
GET https://api.openai.com/v1/models, a 10-second timeout, a 2 MiB response bound
and no redirects; response bodies and keys are never echoed or audited.

Model visibility can confirm metadata access, not successful Responses inference,
reasoning settings, rate limits, quota or an invoice. generation_tested remains
false. The check does not reserve budget or call a model. Unknown/unavailable
credentials or model access remain genuine blockers; do not silently substitute
a model. Official references: https://developers.openai.com/api/docs/models and
https://developers.openai.com/api/reference/resources/models/methods/list .
