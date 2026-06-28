# PaperMemory Node 6 Verified Chat And Evidence UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make scoped chat consume validated `EvidencePacket`s and show answer, evidence, limits, source modality, citations, and page links in the existing UI.

**Architecture:** Node 6 connects the Node 5 hybrid packet to chat and frontend display without adding the Node 7 multi-pass orchestrator. The API should preserve SSE frame order and existing `PageEvidence` compatibility while using packet units as the answer/citation boundary. The web client should parse packet fields from early and done frames, display source provenance in the existing evidence panel, and keep current chat composition ergonomics.

**Tech Stack:** Python 3.12, FastAPI SSE, Pydantic v2, existing `ChatService`, `HybridRetrievalService`, `EvidencePacket`, React 19, Next.js 15, TypeScript, existing CSS.

---

## Stage Boundary

Node 6 integrates verified evidence packets into one-turn chat and visible UI. It must not implement the Node 7 three-pass orchestrator, new autonomous planning loops, new retrieval algorithms, dense text embeddings, OCR, report writing beyond the Node 6 result note, or a broad UI redesign.

## Current Baseline Findings

- Node 5 is complete and the opt-in hybrid route exists through `retrieval_mode="hybrid"`.
- `ChatResponse` and SSE frames already include `evidence_packet`, but `ChatService` currently rebuilds packets from `PageEvidence` and loses Node 5 hybrid rank traces.
- `context_builder.build_evisrag_prompt(...)` currently formats `PageEvidence`, not `EvidencePacket` units.
- The web types and SSE parser do not model `EvidencePacket` yet.
- The existing evidence panel can show page cards and citation jumps, but every API evidence item is currently labeled `VisRAG-Ret`.
- Current frontend typecheck fails before Node 6 because workspace dependencies are not installed/resolved:

```text
components/chat-panel.tsx(4,27): error TS2307: Cannot find module 'react-markdown' or its corresponding type declarations.
components/chat-panel.tsx(5,23): error TS2307: Cannot find module 'remark-gfm' or its corresponding type declarations.
```

Run `npm install` from the repo root before the final `npm --prefix apps/web run typecheck` gate if `node_modules` is missing.

## Latest-Code Surfaces To Preserve

- Conversation mode with no paper scope remains available and must not call retrieval.
- SSE order remains: early evidence frame, token delta frames, final done frame.
- Existing `evidence` arrays remain in chat responses for current clients.
- Citation verification still strips citations to pages outside the accepted packet/evidence pages.
- Existing `enable_agentic_retrieval` and query rewrite behavior stays as a compatibility path; Node 7 will replace it with a true state machine later.
- Existing evidence panel layout, page thumbnail modal, and citation chip behavior stay intact.

## File Map

- Modify: `apps/api/app/schemas/chat.py`
  - Add optional `retrieval_mode: Literal["visual", "hybrid"] = "hybrid"` to `ChatRequest`.
- Modify: `apps/api/app/routers/chat.py`
  - Build `HybridRetrievalService` and pass it into `ChatService`.
  - Preserve existing SSE serialization fields and order.
- Modify: `apps/api/app/services/chat_service.py`
  - Return a small retrieval outcome with `evidence`, `evidence_packet`, `retrieval_attempted`, and `limits`.
  - Use `HybridRetrievalService` when scoped chat asks for `retrieval_mode="hybrid"`.
  - Preserve visual fallback when `retrieval_mode="visual"` or no hybrid service is available.
  - Use accepted packet units for prompt construction and citation-boundary checks.
- Modify: `apps/api/app/services/context_builder.py`
  - Add packet-aware prompt rendering with stable `evidence_id`, page citation labels, source modality, rank traces, and limits.
  - Keep `build_evisrag_prompt(...)` for compatibility.
- Modify tests:
  - `apps/api/tests/test_chat_prompt.py`
  - `apps/api/tests/test_chat_streaming.py`
  - `apps/api/tests/test_chat_service_agentic.py`
  - `apps/api/tests/test_public_evidence_response.py`
- Modify: `apps/web/lib/types.ts`
  - Add `ApiEvidencePacket`, `ApiEvidenceUnit`, `ApiEvidenceRankTrace`, `ApiEvidenceCitation`.
  - Add `evidence_packet` to `ApiRetrievalResponse`, `ApiChatResponse`, and `ApiChatStreamDone`.
- Modify: `apps/web/lib/api.ts`
  - Parse `evidence_packet` in stream evidence and done frames.
  - Pass packet through callbacks.
- Modify: `apps/web/lib/use-chat-session.ts`
  - Store latest packet and limits.
  - Build assistant citations from packet citations when available.
  - Request `retrieval_mode: "hybrid"` for scoped chat and evidence search.
- Modify: `apps/web/components/chat-view.tsx`
  - Pass packet and limits to `EvidencePanel`.
- Modify: `apps/web/components/evidence-panel.tsx`
  - Display source modality from packet units/rank traces.
  - Display packet limits as visible trust notes.
  - Preserve page thumbnail modal behavior.
- Modify: `apps/web/components/chat-panel.tsx` only if citation display needs packet-safe labels; keep message layout unchanged.
- Optional modify: `apps/web/app/globals.css`
  - Add small source/limit badge styles only if existing classes are insufficient.
- Update or create:
  - `reports/final/results/chat_ui_packet.md`
  - `demo/shot-list.md`
  - `.planning/2026-06-22-paper-memory-evidence-agent/progress.md`
  - `.planning/2026-06-22-paper-memory-evidence-agent/task_plan.md`

## API Contract

`ChatRequest.retrieval_mode`:

- `"hybrid"`: scoped chat should use `HybridRetrievalService` and preserve hybrid packet rank traces.
- `"visual"`: scoped chat should use the existing visual/vector retrieval path and wrap evidence into a validated packet.
- default: `"hybrid"` for product-visible scoped chat.
- no `paper_ids`: conversation mode; no retrieval.

Internal retrieval outcome shape:

```python
@dataclass(frozen=True)
class ChatRetrievalOutcome:
    evidence: list[PageEvidence]
    evidence_packet: EvidencePacket
    retrieval_attempted: bool
    limits: list[str]
```

Prompt behavior:

- For evidence-bearing answers, prompt context must list accepted packet units.
- Each item should include:
  - `evidence_id`
  - `citation_id` or citation label in `paper_id p.N` form
  - `paper_id`
  - `page`
  - `source`
  - `score`
  - source rank trace summary, such as `visrag r1 score=...; bm25 r2 score=...`
  - caption/snippet when text context is enabled
  - image reference when available
- The prompt should say final citations may only use the packet citation labels.
- Empty scoped evidence must produce an insufficient-evidence instruction and visible limits.

SSE behavior:

- Early frame keeps `type="evidence"` and includes `evidence`, `evidence_packet`, and `note`.
- Delta frames stay unchanged.
- Done frame includes `answer`, `evidence`, `evidence_packet`, `note`, `stats`, `summary_message`.
- Existing streaming tests for frame order must continue to pass.

## Frontend Contract

Types:

```ts
export interface ApiEvidenceRankTrace {
  retriever: string;
  source: "visrag_page" | "text_page" | "hybrid_page" | "manual";
  rank: number | null;
  score: number | null;
}

export interface ApiEvidenceUnit {
  evidence_id: string;
  paper_id: string;
  page_number: number;
  source: "visrag_page" | "text_page" | "hybrid_page" | "manual";
  score: number | null;
  image_url?: string | null;
  title?: string | null;
  caption?: string | null;
  metadata?: Record<string, string> | null;
  rank_trace: ApiEvidenceRankTrace[];
  validation_state: "unvalidated" | "validated";
}
```

UI behavior:

- Evidence cards should derive retriever/source label from packet unit source and rank traces:
  - both visrag and bm25 traces: `Hybrid`
  - only visrag: `VisRAG-Ret`
  - only bm25/text: `Qdrant text` or `BM25 text`
- Evidence panel should show packet limits in addition to note.
- Citation chips should use packet citations when available, so they jump only to accepted evidence pages.
- The UI should not display raw local paths.
- Do not add a landing page or broad redesign.

## Required Commands

```powershell
python -m pytest apps/api/tests/test_chat_prompt.py apps/api/tests/test_chat_streaming.py apps/api/tests/test_chat_service_agentic.py apps/api/tests/test_public_evidence_response.py -q
python -m pytest apps/api/tests/test_evidence_contract.py apps/api/tests/test_hybrid_retrieval_service.py -q
npm install
npm --prefix apps/web run typecheck
git diff --check
```

If `npm install` changes `package-lock.json`, inspect the diff and keep only legitimate dependency resolution changes. If it only restores `node_modules`, do not stage generated dependency directories.

## Subagent Plan

### Subagent A: Verified Chat And UI Implementer

**Role:** worker.

**Write scope:** files listed in File Map.

**Task:** Wire validated packets into chat prompts, SSE, and frontend display while preserving existing chat behavior.

- [ ] Add failing API tests for packet-aware prompt context containing `evidence_id`, source traces, citations, and limits.
- [ ] Add failing API tests for streaming early/done frames containing the same validated packet while preserving frame order.
- [ ] Add failing API tests proving visual mode remains available and no-scope conversation mode does not retrieve.
- [ ] Implement `ChatRequest.retrieval_mode` and packet-aware `ChatRetrievalOutcome`.
- [ ] Inject `HybridRetrievalService` from the chat router and use it for scoped hybrid chat.
- [ ] Add packet-aware context builder function and keep old `PageEvidence` prompt function compatible.
- [ ] Update citation generation and verification to use accepted packet citations/pages.
- [ ] Update web API types and SSE parsing for `evidence_packet`.
- [ ] Update `use-chat-session` to store packet, pass packet to evidence panel, and build citation chips from packet citations.
- [ ] Update evidence panel source/limit display without broad redesign.
- [ ] Add `reports/final/results/chat_ui_packet.md` and update `demo/shot-list.md`.
- [ ] Run all required commands and update planning files.

### Subagent B: Node 6 Spec Reviewer

**Role:** default.

**Write scope:** none.

**Task:** Check implementation against this stage plan and source superplan Node 6.

- [ ] Verify scoped chat consumes validated `EvidencePacket`s.
- [ ] Verify prompt context uses stable packet evidence IDs and accepted citation labels.
- [ ] Verify citations are limited to accepted packet pages.
- [ ] Verify weak/missing scoped evidence creates visible limits/refusal wording.
- [ ] Verify SSE order and frame shape remain compatible.
- [ ] Verify frontend parses and displays packet source modality and limits.
- [ ] Verify `npm --prefix apps/web run typecheck` passes after dependency install.
- [ ] Verify Node 7 multi-pass orchestrator is not implemented.
- [ ] Verify `task_plan.md` is not final-complete before reviews pass.

### Subagent C: Node 6 Quality Reviewer

**Role:** default.

**Write scope:** none.

**Task:** Check maintainability, UI quality, and claim boundaries.

- [ ] Confirm chat retrieval changes are cohesive and do not duplicate Node 5 fusion logic.
- [ ] Confirm packet prompt rendering is compact enough for model context and does not expose hidden/local paths.
- [ ] Confirm frontend state does not desynchronize evidence arrays and packets.
- [ ] Confirm no-scope conversation mode remains ergonomic.
- [ ] Confirm evidence panel text fits existing layout and uses source labels clearly.
- [ ] Confirm tests cover behavior and important regressions.
- [ ] Confirm report/demo wording says packet-visible chat/UI, not Node 7 autonomy.

## Review Loop Limit

The controller may run at most two acceptance rounds for Node 6:

1. Round 1: implementation, spec review, quality review.
2. Round 2: targeted fixes only if either reviewer returns required fixes.

If Node 6 still fails after Round 2, leave it `blocked` or `in_progress_with_concerns` and record the exact remaining issue in `progress.md`.

## Final Node 6 Gate

Node 6 is accepted only when:

- All required commands pass.
- Spec review passes.
- Quality review passes.
- Scoped chat uses validated packet evidence.
- SSE frame order is preserved.
- The web UI displays source modality, packet limits, citations, and page links.
- `reports/final/results/chat_ui_packet.md` and `demo/shot-list.md` contain Node 6 demo/report notes.
- The next stage is still Node 7: Three-Pass Bounded Research Orchestrator.
