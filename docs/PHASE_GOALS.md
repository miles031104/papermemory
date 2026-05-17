# PaperMemory Phase Goals

This document defines the staged product path for PaperMemory. The near-term priority is a usable local-first MVP for paper upload, visual retrieval, BYOK answering, and paper management. LLM Wiki-style persistent synthesis is an important later expansion, but it should not displace the core paper workflow.

## Product Principle

PaperMemory should first become a reliable local research paper workspace:

- Users can install and run it locally from GitHub.
- Users can upload local PDFs without sending papers to a hosted PaperMemory service.
- Paper pages are rendered as images and indexed with a VisRAG-style retriever.
- Answers are grounded in page-level evidence.
- Users bring their own model API key.
- Libraries, conversations, paper groups, and paper metadata persist locally.

The long-term direction is a research memory system, not a generic chatbot. However, the project should earn that direction by first making the core PDF-to-evidence workflow dependable.

## Phase 0: Local Install And Runtime Foundation

Goal: make the app easy to install and start on a normal developer machine.

Required outcomes:

- Windows setup script detects Python, npm, and Docker.
- If Docker is available, configure Qdrant server mode.
- If Docker is unavailable, ask whether to install Docker Desktop.
- If the user declines Docker, configure Qdrant local mode.
- Keep Qdrant mode explicit through `PAPERMEMORY_QDRANT_MODE=server|local`.
- Keep API keys and Hugging Face tokens out of persistent setup files.
- Provide clear start commands and health-check behavior.

Done when:

- A fresh local checkout can run setup in either Docker mode or local vector mode.
- Backend tests, frontend typecheck/build, and a basic web smoke test pass.
- README explains Docker mode versus local mode without implying a remote server is required.

## Phase 1: Core PaperMemory MVP

Goal: complete the main local paper assistant loop.

Required outcomes:

- Upload local PDF files from the web UI.
- Store original PDFs under local storage.
- Render PDF pages to local images.
- Index page images into Qdrant.
- Support the default stub retriever for lightweight local development.
- Support real `openbmb/VisRAG-Ret` as an explicit opt-in backend.
- Search page evidence inside the active library.
- Ask questions with BYOK OpenAI-compatible model providers.
- Attach selected page images to multimodal chat requests when enabled.
- Return answers with page-level citations and visible evidence.
- Never call the external model when the active paper scope is empty.

Done when:

- A user can complete: install -> upload PDF -> index pages -> search evidence -> ask a question -> inspect cited page images.
- The same flow works in Qdrant local mode without Docker.
- The same flow works in Qdrant server mode when Docker is available.
- Error states are clear for missing Qdrant, missing provider key, failed indexing, and unsupported PDFs.

## Phase 2: Paper Management Page

Goal: make PaperMemory useful as a researcher's paper manager, not only a chat surface.

Required outcomes:

- Add a paper management page or secondary workspace view.
- Show papers grouped by library and paper group.
- Display title, authors, year, source file, indexing status, and page count.
- Store and show a concise core-idea summary for each paper.
- Let users create, rename, and delete paper groups.
- Let users move papers between groups inside a library.
- Let users open a paper detail panel with:
  - metadata,
  - key claims,
  - method summary,
  - limitations,
  - important pages or figures,
  - related conversations.
- Keep paper groups backed by the real workspace store, not frontend-only mock state.

Done when:

- A user can organize uploaded papers into meaningful groups.
- The active chat can be scoped to a library or group.
- Paper metadata survives app restart.
- Paper manager UI remains useful before LLM Wiki synthesis exists.

## Phase 3: Ingestion Job Reliability

Goal: make long-running ingestion safe and observable.

Required outcomes:

- Introduce a persistent ingestion job model.
- Track upload, render, embed, index, and failure states separately.
- Support retry for failed ingestion.
- Avoid cross-library contamination when users switch active databases during ingestion.
- Make indexing progress visible in the frontend.
- Record enough job detail to diagnose common local failures.

Done when:

- A failed PDF or interrupted app session does not leave ambiguous state.
- Users can retry indexing without re-uploading the PDF.
- The frontend can show which papers are ready for retrieval and which are still processing.

## Phase 4: Research Notes For Papers

Goal: start compiling durable paper knowledge without adopting the full LLM Wiki system yet.

Required outcomes:

- Generate a markdown-style paper note for each indexed paper.
- Store notes locally under a predictable workspace path.
- Include source traceability back to `paper_id`, page numbers, and evidence images.
- Use a conservative paper-note schema:
  - bibliographic metadata,
  - one-paragraph summary,
  - core contribution,
  - method,
  - experiments,
  - limitations,
  - key terms,
  - important figures/pages,
  - open questions.
- Let the user regenerate or edit the note.
- Show the note in the paper detail page.

Done when:

- Paper notes are useful even without cross-paper synthesis.
- Notes can be cited or used as context in chat.
- Generated claims link back to page evidence.

## Phase 5: LLM Wiki Expansion

Goal: evolve PaperMemory from paper RAG into a persistent research memory system.

This phase should be inspired by LLM Wiki, but only after the core MVP and paper manager are stable.

Candidate features:

- Workspace-level `index.md` and `log.md`.
- Topic pages for paper groups.
- Concept pages shared across papers.
- Method, dataset, benchmark, and claim pages.
- `[[wikilink]]`-style cross-references.
- YAML frontmatter with source traceability.
- Two-stage ingest:
  - analysis first,
  - wiki generation second.
- Lint passes for:
  - contradictions,
  - stale summaries,
  - orphan concepts,
  - weakly supported claims,
  - missing paper links.
- Save high-value chat answers back into the research wiki.
- Optional graph view for concepts, papers, claims, and methods.

Done when:

- PaperMemory can maintain an evolving research topic page across multiple papers.
- New papers update existing concepts instead of only creating isolated summaries.
- Users can inspect what changed and why.
- Wiki-generated claims remain grounded in page-level PDF evidence.

## Phase 6: Collaboration And Hosted Extensions

Goal: add optional shared workspaces without weakening the local-first baseline.

Candidate features:

- Shared libraries.
- Team conversations.
- Hosted metadata database.
- Server-side indexing workers.
- Access control.
- Billing and usage limits.
- Cloud backup or sync.

Non-negotiable constraints:

- Local-only mode must remain useful.
- Hosted mode must make data retention and deletion explicit.
- Secret storage and model-provider delegation need a separate security design.
- Migration from local JSON/filesystem storage to hosted storage must be deliberate.

## Current Priority

The immediate roadmap should be:

1. Finish Phase 0 install polish and local Qdrant fallback.
2. Complete Phase 1's real PDF-to-evidence-to-answer loop.
3. Build Phase 2's paper management page on top of the real workspace model.
4. Add Phase 3 ingestion reliability before broad synthesis automation.
5. Start Phase 4 paper notes.
6. Treat Phase 5 LLM Wiki as a deliberate expansion, not the MVP baseline.

This sequencing keeps the project focused: PaperMemory should first become an excellent local paper assistant, then become a compounding research memory system.
