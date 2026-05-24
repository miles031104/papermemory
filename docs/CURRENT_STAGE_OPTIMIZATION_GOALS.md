# PaperMemory Current Stage Optimization Goals

This document breaks the current PaperMemory optimization work into staged,
verifiable slices. It complements `PHASE_GOALS.md`: that file describes the
larger product roadmap, while this file defines the near-term execution plan for
turning the current local MVP into a steadier paper assistant agent.

## Current Product Position

PaperMemory is already shaped as a local-first PDF research workspace:

- Local PDF upload and storage are the entry point.
- Page images and VisRAG-style retrieval are the evidence path.
- BYOK OpenAI-compatible providers are the generation path.
- The main workspace focuses on upload, library state, chat, and evidence.
- Provider/model/install controls belong in the settings surface.
- Agent answers must hide private reasoning and expose answer, evidence, and
  limits.

The next optimization stage should not turn PaperMemory into a generic agent
framework. The goal is to make the research workflow dependable first, then add
agentic behavior where it improves evidence quality.

## Stage 1: Stabilize The Evidence Loop

Goal: make upload -> render -> index -> retrieve -> answer reliable enough to be
the default daily workflow.

Deliverables:

- Confirm every uploaded paper has a durable manifest with paper ID, page count,
  rendered-page paths, browser-safe image URLs, title when available, and
  indexing status.
- Keep Qdrant local mode and server mode behavior explicit and testable.
- Make active library/group/paper scope filtering impossible to bypass by
  accident.
- Ensure empty scoped retrieval never falls back to a paper-grounded answer.
- Normalize evidence records returned to the frontend:
  - `paper_id`
  - `page_number`
  - `score`
  - `image_url`
  - `title`
  - optional snippet or page note
- Keep the citation contract stable as `paper_id p.N`.

Acceptance checks:

- Uploading a PDF creates rendered page images and searchable evidence.
- Searching in an empty library returns no evidence and no cross-library leak.
- Chat with an empty active paper scope enters conversation mode and still calls model generation.
- Scoped retrieval with zero evidence returns no paper-grounded answer or paper citations.
- Chat with evidence returns answer, citations, and visible evidence records.

## Stage 2: Agent Response Contract And Tool Results

Goal: make the backend agent orchestration explicit instead of relying on loose
strings and hidden assumptions.

Deliverables:

- Introduce a small PaperMemory response protocol inspired by ToolResponse:
  - `success`
  - `partial`
  - `error`
  - structured `data`
  - structured `error`
  - `stats`
  - optional `limits`
- Apply the protocol first to retrieval, chat orchestration, model gateway, and
  citation validation.
- Keep user-visible text separate from machine-readable evidence and diagnostic
  metadata.
- Treat partial success as first-class, for example:
  - retrieval succeeded but page-image attachment was disabled,
  - model answered but citations need a warning,
  - some evidence pages were truncated or unavailable.

Acceptance checks:

- Tests can assert status and error codes without parsing prose.
- Model gateway failures do not leak API keys or raw provider internals.
- Partial evidence states produce clear user-facing limits.

## Stage 3: Context Engineering For Paper QA

Goal: make prompt construction predictable, compact, and evidence-first.

Deliverables:

- Add or formalize a context builder with a Gather -> Select -> Structure ->
  Compress flow.
- Gather:
  - user question,
  - active scope,
  - recent conversation,
  - retrieved page evidence,
  - paper metadata,
  - future local notes when available.
- Select:
  - prefer scoped, high-score, high-signal pages,
  - cap page-image attachments,
  - avoid adding entire libraries or long manifests.
- Structure:
  - system contract,
  - active scope,
  - evidence list,
  - recent conversation,
  - output requirements.
- Compress:
  - summarize older conversation,
  - truncate long tool outputs,
  - preserve citation IDs and evidence boundaries.

Acceptance checks:

- Prompt-building tests show stable section order.
- Large libraries do not cause uncontrolled context growth.
- The model receives enough evidence to answer, but not unrelated paper noise.

## Stage 4: Frontend Workflow Polish

Goal: make the main research workspace feel complete and reduce configuration
noise.

Deliverables:

- Keep Workspace and Settings as distinct surfaces.
- In Workspace, prioritize:
  - active library,
  - paper/group list,
  - upload state,
  - chat,
  - cited evidence.
- In Settings, keep:
  - provider base URL,
  - API key,
  - model,
  - multimodal/image context options,
  - retriever/backend setup notes.
- Improve empty, loading, error, and partial-success states.
- Make evidence inspection easy: users should be able to see which cited pages
  support an answer.

Acceptance checks:

- Browser smoke verifies Workspace and Settings show mutually exclusive content.
- A user can upload, ask, and inspect evidence without visiting Settings after
  initial provider setup.
- Missing provider key, missing indexed papers, and failed retrieval each show a
  different useful state.

## Stage 5: Paper Manager And Local Notes

Goal: move from "chat over uploads" to a useful local paper workspace.

Deliverables:

- Add a paper management view or pane backed by the real workspace store.
- Show library/group organization and paper readiness.
- Let users create, rename, and delete paper groups.
- Let users move papers between groups.
- Add a paper detail surface with:
  - metadata,
  - rendered page count,
  - indexing status,
  - important pages,
  - related conversations,
  - future paper note.
- Introduce a conservative paper-note schema:
  - summary,
  - contribution,
  - method,
  - experiments,
  - limitations,
  - key pages,
  - open questions.

Acceptance checks:

- Paper organization survives app restart.
- Chat can be scoped to a library, group, or paper.
- Generated notes are traceable to page evidence before they can be reused as
  context.

## Stage 6: Agentic Retrieval And Validation

Goal: add agent behavior where it improves evidence quality, without making the
MVP overcomplicated.

Deliverables:

- Add a lightweight validation pass that checks:
  - citation format,
  - unsupported claims,
  - missing evidence,
  - whether the answer pretends to inspect images that were not attached.
- Add optional iterative retrieval for hard questions:
  - initial retrieval,
  - identify evidence gaps,
  - run one or two targeted follow-up searches,
  - answer with limits.
- Keep Reflection internal. User-visible output should not include scratchpads or
  hidden reasoning.
- Defer multi-agent deep research until the normal paper QA path is solid.

Acceptance checks:

- Unsupported claims are either removed or moved into `Limits`.
- Citation drift is caught in tests.
- Iterative retrieval has a strict step cap and cannot loop indefinitely.

## Stage 7: Observability And Regression Safety

Goal: make failures diagnosable and prevent agent behavior from drifting.

Deliverables:

- Add structured session events for:
  - retrieval,
  - prompt construction,
  - page-image attachment,
  - model gateway calls,
  - citation validation,
  - redaction,
  - provider errors.
- Redact secrets and local-only sensitive paths from logs.
- Keep debug traces out of the default user chat transcript.
- Add regression fixtures for:
  - hidden `<think>` traces,
  - literal `<think>` text in normal answers,
  - empty library scope,
  - scoped retrieval with zero hits,
  - unsupported image provider,
  - citation format drift,
  - provider malformed output.

Acceptance checks:

- A failed answer can be debugged from structured events.
- Tests cover the known failure modes before larger agent changes land.
- User-facing output stays clean: answer, evidence, limits.

## Sequencing

Recommended order:

1. Stage 1: Stabilize the evidence loop.
2. Stage 2: Add structured response contracts.
3. Stage 3: Formalize context engineering.
4. Stage 4: Polish the main workspace workflow.
5. Stage 5: Add paper manager and local notes.
6. Stage 6: Add agentic retrieval and validation.
7. Stage 7: Expand observability and regression safety throughout.

Stages can overlap, but each code change should name which stage it advances and
which acceptance checks it affects.

## Near-Term Definition Of Done

The current optimization round is done when:

- A local user can upload papers, retrieve scoped evidence, ask questions, and
  inspect citations in the main workspace.
- Settings remain separate from the research workflow.
- Backend responses distinguish success, partial success, and failure.
- Context construction is evidence-first and bounded.
- Citation and hidden-reasoning failures are covered by tests.
- The app remains local-first and BYOK by default.
