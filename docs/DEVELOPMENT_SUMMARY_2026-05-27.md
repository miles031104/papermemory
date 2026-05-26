# PaperMemory Development Summary - 2026-05-27

## Scope

This update moves PaperMemory toward a local-first research workspace with group-scoped paper management, evidence-grounded chat, and a clearer multimodal RAG path.

## Product Changes

- Reworked the workspace into separate Home, Chat, Paper Manager, and Settings surfaces.
- Added a table-oriented Paper Manager view for browsing and managing existing papers.
- Added group and library management flows, including delete actions.
- Added paper deletion and conversation deletion from the UI.
- Improved the paper upload and group move workflow so papers can be organized into a selected RAG scope.
- Compactified Settings so model configuration is the primary control surface and env-derived settings stay synchronized.
- Redesigned retrieval evidence into page-level cards with scrollable evidence and an expanded page preview.

## AI/RAG Route

The current AI route is:

```text
User question
  -> bounded LLM retrieval planning
  -> selected group RAG lookup
  -> page-level evidence selection
  -> multimodal-first context assembly
  -> cited answer generation
```

The default strategy is multimodal-first: when the selected model supports vision, PaperMemory sends evidence page images to the model. Text extraction and OCR are used as fallback context for text-only models.

## Backend Changes

- Added bounded agentic retrieval planning before evidence search.
- Added group, library, paper, and conversation deletion support.
- Hardened workspace repair and group membership consistency.
- Expanded chat responses with retrieval planning metadata for frontend evidence handling.
- Kept API-side model calls and secret handling on the backend instead of exposing provider calls directly in the browser.

## Verification Notes

The targeted verification set for this stage is:

- API tests with `pytest`.
- Web type checking with `npm --prefix apps/web run typecheck`.
- Git whitespace validation with `git diff --check`.
- Manual local API health and route checks on `127.0.0.1:8000`.

## Presentation Artifact

The one-slide AI technical route deck is stored at:

```text
outputs/manual-20260527-papermemory-ai-route/presentations/ai-route/output/papermemory-ai-technical-route.pptx
```

