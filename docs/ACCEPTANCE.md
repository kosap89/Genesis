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
