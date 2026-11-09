# Venture instructions and durable documents

Genesis uses the existing SQLite store and CEO Command Center for both features.
They do not start a provider session, authorize spending or create a task.

## Project configuration

Select a venture, open Agent Team and edit its project specialization, instructions
and responsibilities. These fields are stored on its team membership, separately
from global agent defaults. Provider/model/reasoning and fallback overrides are
also project specific. A disabled membership prevents assignment in that venture.
Global instance defaults have a separate explicit save action.

The project operating policy is stored on the venture. Policy text is an instruction,
not a grant of network, terminal, spending or external-action permissions. Existing
approval and budget checks still apply. A zero project budget prevents model work
until the CEO changes it for an authorized assignment.

Tasks snapshot the effective member configuration and project policy. Editing the
configuration affects new tasks; explicit Resume with agent settings refreshes an
existing resumable task. Plain resume retains its authorized snapshot. Role
templates remain reusable defaults; a shared agent can have different memberships
in several ventures without changing its global configuration.

## Persistent assets

Open Project documents for the selected venture. Named Markdown/text documents are
stored in SQLite records, independently of task workspaces. The CEO can inspect
content, download it under its document filename, create documents and save a new
revision. The revision history retains complete prior content, source actor and
timestamps. Updating requires the displayed expected revision; concurrent stale
updates are rejected instead of silently overwriting newer content.

Kinds are reference, design, proposal, review and decisions. References and
decisions default to locked against agents. The CEO can revise them while retaining
history. Agents cannot modify a locked reference or decision document or promote
a proposal to a decision. No automatic task completion records creative approval.
There is no destructive document deletion API.

The CEO is the single user of this loopback application. HTTP mutations use the
existing Host/origin and CSRF boundary. Actor attribution for HTTP edits is CEO;
agent tools supply their own actor in code, ignoring model-supplied actor fields.
These controls do not isolate an approved host subprocess from same-user files.

## Agent access and source context

Project agents receive bounded excerpts of current documents, with names, revision
numbers, lock status and truncation indicators. References and decisions are
prioritized. They can use venture_document_list, venture_document_read (paginated),
venture_document_propose and venture_document_update. Tools resolve only the task's
venture and check active membership. Proposed documents remain proposals, while
ordinary writable documents can be revised using optimistic version checks.

Agent read/update calls accept either `document_name` (preferred, exact name such
as `GAME_DESIGN.md`, case-insensitive) or `document_id`. Names resolve only inside
the task's venture. If both selectors are supplied they must identify the same
document; a bad or foreign ID never falls back to a name or fuzzy match. Missing
lookups explicitly instruct the agent to call `venture_document_list` before
retrying. Updates still require the actual `expected_revision`, and name lookup
cannot bypass protected references, human decisions or active membership checks.

Current shared documents may evolve between turns; the prompt labels their actual
revision. Document content is source material and never grants capabilities.
Separate task artifacts, imports, hashes and downloads continue to work unchanged.
Reports alone do not update shared documents; agents must explicitly use the
durable document tools when an authorized task requires a persistent update.

## API and storage

- GET /api/projects/<venture_id>/documents lists current documents.
- GET /api/projects/<venture_id>/documents/<document_id> reads a document.
- GET the same path plus /revisions returns immutable revision records.
- GET the same path plus /download returns a text attachment.
- POST the collection creates {name, content, kind, read_only}.
- POST a document updates {content, expected_revision}; CEO callers may also edit
  its name, kind and lock status.
- POST /api/projects/<id> accepts operating_policy and an optional budget.
- Team membership endpoints accept project system_instructions and specialization
  alongside responsibilities, enabled and route overrides.

records kinds venture_documents and venture_document_revisions contain content and
history. Agent instructions live in team_memberships; operating_policy lives in
ventures. All related document/revision/audit writes use Store.batch under the
shared lock. Back up the existing SQLite database; authoritative documents are
not stored only in temporary task directories.

The service accepts up to 200,000 characters internally, while the existing HTTP
request ceiling is 128 KiB for the entire JSON request. Large text may therefore
hit the HTTP limit first, especially with non-ASCII content. Prompt excerpts are
bounded to 24,000 content characters overall and 8,000 per document, with up to
30 document summaries; tools can read remaining content in pages of at most
20,000 characters. These limits do not claim complete context for arbitrarily
large archives. Current history/list APIs are intended for moderate local use.
