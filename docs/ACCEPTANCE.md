# Founding acceptance runs

Status: **not yet executed with live AI**. Fixtures validate infrastructure only.

## 1. Company strategy

Create a venture, select the strategy agent (or COO for delegation), and submit:

> Research three viable AI-driven business opportunities that this organization could build and monetize.

Approve public network requests. Expect real source URLs, competitor comparisons,
cost assumptions, risks, monetization proposals, opportunity records, and a report.
Default Wikipedia discovery alone is insufficient evidence for a comprehensive
competitive assessment; configure Brave search or include authoritative URLs.
Review sources and reject unsupported claims.

## 2. Software development

Submit to engineering, including the selected opportunity and concrete requirements:

> Build and test a working application based on the selected business opportunity.

Expect executable source files, meaningful tests, actual test output in tool
history, a run guide and artifact downloads. Inspect files before approving host
execution. QA can list and import actual same-venture artifacts into a separate
workspace for independent inspection and execution. Importing does not grant
execution permissions; QA test execution has its own approval.

## 3. Self-improvement

Submit to engineering:

> Audit an existing Genesis component, identify a meaningful improvement, implement and test it.

Expect use of self_improvement_snapshot, candidate changes beneath the task
workspace, real tests, a unified patch from self_improvement_diff, and an auditable
report describing the proposed change.
The running checkout must remain unchanged. A human reviews and applies a verified
candidate; Genesis does not replace its own live execution code.

For each run record task IDs, provider/model, actual artifacts, independent test
results, usage and remaining limitations in STATE.md. Never replace this checklist
with a hardcoded successful result.

## Live acceptance runbook prepared 2026-11-09

Preparation only: none of the following objectives has been submitted or executed.
Run sequentially in one new venture named `Founding live acceptance`. Do not enqueue
work until a session credential and explicit CEO spending authorization exist.

### Secure first-key setup in the existing local interface

1. Open http://127.0.0.1:8787 and choose **Agents & controls**.
2. Under **Add a key for this session**, select the provider for the key you own.
3. Paste the key directly into **API key**, never into chat, an objective, a shell
   command, source, or a document. Do not save it in the browser password manager.
4. For a first single-provider run, check **Use this provider's default model for
   all agents**, then click **Save for this session**. The password field clears.
   This changes routes but makes no model call and resumes no objectives.
5. Confirm the provider is configured. This checks key presence only: authentication,
   credits, quotas and model access remain unverified until a genuine request.
6. Review **Agent configuration** for strategy, engineering, QA and any delegated
   roles. Model identifiers are editable. The provider list contains built-in
   defaults, not a live model catalog. Verify availability before the paid run;
   keep fallback routes empty for attributable first-provider evidence.
7. Tell the operator the provider name and approved total USD amount, without the
   key. The operator will apply that authorized company budget and verify settings.
   Do not mistake the original $5 default for spending authorization. Preparation
   has set the company budget to $0. Current rates are conservative configured
   estimates ($10 input / $30 output per million tokens), not invoice prices.
8. Leave network and terminal broad permissions disabled. Review individual public
   HTTPS requests and inspect generated Python before each execution approval.
   Host Python runs with server-user privileges; it is not an OS sandbox.

Session keys are GENESIS_* process environment overrides, disappear on server
restart, and are not persisted in SQLite or browser storage. **Clear process override** removes this override; inherited provider variables can remain active.
Budget reservation uses serialized input bytes plus an allowance and maximum output
at configured rates; missing usage or uncertain transport can charge an estimated
ceiling. Actual billing may differ. Reconcile provider usage separately; the local
budget is not a guaranteed provider-side spending cap. Do not increase it without
new authorization if a run blocks.

### Run 1: company strategy (lead: strategy)

> Research three viable AI-driven business opportunities that this organization
> could build and monetize. Use real public HTTPS sources, including authoritative
> product, pricing or customer-problem pages for each opportunity; Wikipedia-only
> discovery is insufficient. Record source URLs and observed facts separately from
> assumptions. Compare competitors, implementation and operating costs, risks,
> monetization and an explicitly estimated unit economics scenario. Save three
> opportunity records and a report artifact. Rank them and select one small
> opportunity whose useful core can be demonstrated locally in Python without
> additional paid services, external communications or deployment. Identify
> validation still needed; do not invent demand, customer interviews or citations.

Independent gate: reopen cited pages, verify consequential claims and pricing,
inspect all three stored opportunity records and report bytes. Record inaccessible
or weak sources and qualify the finding. Freeze the selected opportunity ID and a
small requirements list from the actual report before preparing Run 2's final text.
No Brave credential is required for direct public URL fetches; do not imply that
Wikipedia discovery validates commercial demand.

### Run 2: working software (lead: engineering; independent review: QA)

> Build and test a working local Python application for the selected opportunity
> [insert actual Run 1 opportunity ID and the frozen requirements]. Save executable
> source, a run guide and meaningful unittest tests covering a useful happy path,
> invalid input, and a consequential edge case. Use standard-library dependencies
> where practical. Run actual tests only after approval, and preserve their output.
> Save source/test/report artifacts and describe which requirements are demonstrated
> versus unimplemented. Do not use fabricated AI responses as the product's claimed
> functionality or claim a test passed without execution evidence.

Independent gate: inspect artifact contents before approving execution. Download
the actual bundle and independently execute its tests and a run-guide smoke example
in a separate local verification directory. QA can import the actual same-venture
artifacts into its own workspace; its execution requires a separate approval and
its AI calls count toward the same budget. Record commands, exit codes, discovered
tests and observed behavior; investigate defects, repair, and rerun affected checks.
Do not count an empty test suite or model-authored success statement as a pass.

### Run 3: candidate self-improvement (lead: engineering)

> Audit one existing Genesis component for a meaningful, bounded defect or
> improvement. Use self_improvement_snapshot and work only beneath the candidate
> source directory in your task workspace. Cite the observed issue; add a meaningful
> regression test, demonstrate its behavior before and after the fix where feasible,
> and run the affected tests after approval. Generate a real unified patch with
> self_improvement_diff. Save a report describing the evidence, exact change,
> verification and limitations. Keep the running checkout unchanged and do not
> apply your patch to live Genesis.

Independent gate: retain a tracked-source hash baseline immediately before this
run. Inspect the patch, apply it to an isolated copy of the same baseline, and run
the relevant tests plus full required checks if affected. Verify tracked live
source hashes match the baseline afterward. Do not promote the candidate. A proposed
improvement without reproducible evidence remains unverified.

### Evidence to record after each real run

Record venture/task/parent/QA IDs, effective provider/model and route changes,
request/response counts, token usage, configured rate estimates and cost deltas,
reservations, unknown-usage charges, tool approvals/denials, source URLs and checked
claims, artifact IDs/paths and SHA-256 hashes, real test commands/output/exit codes,
independent findings, defects/fixes/reverification and remaining limitations.
Distinguish provider-reported tokens, locally estimated USD and provider-console
billing. Never fabricate unavailable invoice evidence. Never record the API key,
CSRF token or authorization header. Runtime evidence stays in ignored data/ and
test-results/; put only sanitized findings and evidence references in STATE.md.
