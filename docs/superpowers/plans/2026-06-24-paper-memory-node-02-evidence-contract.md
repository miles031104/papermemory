# PaperMemory Node 2 Evidence Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a small, deterministic EvidenceUnit/EvidencePacket contract that every current retrieval hit can be represented by, without breaking existing `PageEvidence` clients.

**Architecture:** Node 2 is an additive contract layer over the latest `origin/miles` baseline. Current `/retrieval/search`, `/chat`, SSE evidence frames, redaction behavior, and `PageEvidence[]` remain compatible. New packet fields are generated from existing `PageEvidence` objects and validated by a separate service; later nodes can extend packet provenance for text, BM25, hybrid, and bounded agent traces.

**Tech Stack:** Python 3.12, Pydantic v2, FastAPI response models, current `PageEvidence`, current `StoragePaths`, pytest.

---

## Stage Boundary

Node 2 must create the evidence contract all later nodes use. It must not implement BM25, text manifests, hybrid retrieval, UI redesign, or a new orchestrator. It may update current response schemas and services only enough to expose packet data additively.

## Latest-Code Surfaces To Preserve

- `PageEvidence` remains the public list item shape used by existing clients.
- `image_path` remains excluded from public serialization.
- Existing title/caption/metadata redaction behavior in `apps/api/app/schemas/retrieval.py` remains the source of truth for public text.
- `/retrieval/search` still returns existing `status`, `query`, `evidence`, `retrieval_model`, `note`, `stats`, and `limits`.
- `/chat` still returns existing `answer`, `evidence`, `prompt_preview`, `stats`, and `limits`.
- `ChatService.answer_stream()` still yields early evidence before delta tokens and final done frame after tokens.

## File Map

- Create: `apps/api/app/schemas/evidence.py`
  - Owns `EvidenceUnit`, `EvidenceCitation`, `EvidencePacket`, rank/source trace models, deterministic IDs, and adapters from `PageEvidence`.
- Create: `apps/api/app/services/evidence_validator.py`
  - Owns pure validation helpers for page/image existence, selected-paper scope, citation containment, and public path redaction.
- Modify: `apps/api/app/schemas/retrieval.py`
  - Add optional `evidence_packet: EvidencePacket | None = None` to `RetrievalResponse`.
- Modify: `apps/api/app/schemas/chat.py`
  - Add optional `evidence_packet: EvidencePacket | None = None` to `ChatResponse`.
- Modify: `apps/api/app/routers/retrieval.py`
  - Build an `EvidencePacket` from retrieved `PageEvidence` and include it in the response.
- Modify: `apps/api/app/services/chat_service.py`
  - Build an `EvidencePacket` from chat evidence and include it in non-streaming response, early SSE evidence frame, and final SSE done frame without changing frame order.
- Test: `apps/api/tests/test_evidence_contract.py`
  - Unit tests for IDs, adapters, validators, redaction, and response compatibility.
- Update: `reports/final/results/evidence_contract.md`
  - Report-ready schema table and visible evidence ID example.
- Update: `.planning/2026-06-22-paper-memory-evidence-agent/progress.md`
  - Commands, outcomes, review results.
- Update: `.planning/2026-06-22-paper-memory-evidence-agent/task_plan.md`
  - Node 2 status only after implementation/review gates.

## Contract Shape

`EvidenceUnit v0` should be page-grain and conservative:

- `evidence_id: str`
  - Deterministic and visible.
  - Format: `ev-{safe_paper_id}-p{page_number}-{digest8}`.
  - Digest input: `paper_id`, `page_number`, source label, and normalized caption/title text.
- `paper_id: str`
- `page_number: int`
- `source: Literal["visrag_page", "text_page", "hybrid_page", "manual"]`
  - Node 2 adapters from `PageEvidence` use `visrag_page`.
- `score: float | None`
- `image_url: str | None`
- `title: str | None`
- `caption: str | None`
- `metadata: dict[str, str] | None`
- `rank_trace: list[EvidenceRankTrace]`
  - Nullable/future-friendly trace entries such as retriever name, rank, score.
- `validation_state: Literal["unvalidated", "validated"]`

`EvidencePacket v0` should be small:

- `schema_version: Literal["evidence_packet.v0"]`
- `packet_id: str`
  - Deterministic from query, paper scope, and evidence IDs.
- `query: str | None`
- `paper_scope: list[str] | None`
- `units: list[EvidenceUnit]`
- `citations: list[EvidenceCitation]`
- `limits: list[str]`

`EvidenceCitation` should support both future answer citations and current page citations:

- `evidence_id: str`
- `paper_id: str`
- `page_number: int`
- `label: str | None`

## Validation Contract

`apps/api/app/services/evidence_validator.py` should expose a small API such as:

```python
class EvidenceValidationError(ValueError):
    pass

def validate_evidence_packet(
    packet: EvidencePacket,
    *,
    paths: StoragePaths | None = None,
    paper_scope: list[str] | None = None,
    require_files: bool = False,
) -> EvidencePacket:
    ...
```

Required checks:

- Duplicate `evidence_id` values fail.
- Unit `page_number < 1` fails.
- Unit `paper_id` outside `paper_scope` fails when scope is provided.
- Citation `evidence_id` not present in `packet.units` fails.
- Citation `(paper_id, page_number)` not matching its referenced unit fails.
- When `paths` and `require_files=True`:
  - `paths.paper_metadata_path(paper_id)` must exist.
  - `paths.page_image_path(paper_id, page_number)` must exist and resolve under `rendered_pages`.
- Public packet serialization must not expose local absolute paths or `image_path`.

The validator should return a validated packet copy with `validation_state="validated"` for all units.

## Subagent Plan

### Subagent A: Contract And Response Implementer

**Role:** worker.

**Write scope:** production/schema/test/report files listed in File Map.

**Task:** Implement the additive contract, validators, response integration, tests, and report note.

- [ ] Create `apps/api/app/schemas/evidence.py`.
- [ ] Add deterministic ID helpers and `from_page_evidence` / `from_page_evidence_list` adapters.
- [ ] Create `apps/api/app/services/evidence_validator.py`.
- [ ] Add focused tests in `apps/api/tests/test_evidence_contract.py`.
- [ ] Add optional `evidence_packet` to `RetrievalResponse` and populate it in `apps/api/app/routers/retrieval.py`.
- [ ] Add optional `evidence_packet` to `ChatResponse` and populate it in `apps/api/app/services/chat_service.py`.
- [ ] Preserve SSE frame ordering while adding `evidence_packet` to evidence and done frames.
- [ ] Update `reports/final/results/evidence_contract.md`.
- [ ] Run required checks and update planning files.

Required commands:

```powershell
python -m pytest apps/api/tests/test_evidence_contract.py -q
python -m pytest apps/api/tests/test_public_evidence_response.py apps/api/tests/test_chat_streaming.py apps/api/tests/test_chat_service_agentic.py -q
python -m pytest apps/api/tests/test_phase1b_library_scoped_retrieval.py -q
```

### Subagent B: Node 2 Spec Reviewer

**Role:** default.

**Write scope:** none.

**Task:** Check implementation against this stage plan and the source superplan Node 2 section.

- [ ] Verify contract files exist and fields match the v0 page-grain contract.
- [ ] Verify deterministic IDs are stable for the same `PageEvidence`.
- [ ] Verify invalid page references, citation containment failures, scope failures, and missing files fail validation.
- [ ] Verify public serialization redacts local paths and omits `image_path`.
- [ ] Verify response additions are additive and existing `PageEvidence[]` remains present.
- [ ] Verify existing retrieval/chat regression tests pass.
- [ ] Verify report contribution exists.

### Subagent C: Node 2 Quality Reviewer

**Role:** default.

**Write scope:** none.

**Task:** Check maintainability, compatibility, and claim boundaries.

- [ ] Confirm no BM25, text manifest, hybrid retrieval, or orchestrator behavior was implemented in Node 2.
- [ ] Confirm packet schema leaves future fields nullable rather than overfitting to planned nodes.
- [ ] Confirm validation is pure/testable and not coupled to FastAPI request state.
- [ ] Confirm response integration does not duplicate `PageEvidence` logic or bypass redaction.
- [ ] Confirm SSE ordering remains evidence frame -> deltas -> done frame.
- [ ] Confirm report wording says Node 2 is a contract layer, not a retrieval quality improvement.

## Review Loop Limit

The controller may run at most two acceptance rounds for Node 2:

1. Round 1: implementation, spec review, quality review.
2. Round 2: targeted fixes only if either reviewer returns required fixes.

If Node 2 still fails after Round 2, leave it `blocked` or `in_progress_with_concerns` and record the exact remaining issue in `progress.md`.

## Final Node 2 Gate

Node 2 is accepted only when:

- All required commands pass.
- Spec review passes.
- Quality review passes.
- Existing public evidence and chat behavior remains compatible.
- `reports/final/results/evidence_contract.md` explains the schema and evidence ID format.
- `task_plan.md` status matches the true boundary.
- The next stage is still Node 3: PyMuPDF Text Manifest.
