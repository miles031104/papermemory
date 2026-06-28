# PaperMemory Node 3 Text Manifest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist dependable PyMuPDF page-text manifests for indexed papers, with quality flags for weak/scanned pages, while preserving the current caption fallback used by visual retrieval.

**Architecture:** Node 3 productizes the latest-code `PdfRenderer.extract_page_texts()` behavior into structured manifest services. It adds a reusable extractor and manifest store, wires ingestion to persist manifests before indexing, and keeps `IndexingService.index_pages(..., captions=...)` as the current compatibility bridge. It does not implement BM25 retrieval or change ranking behavior.

**Tech Stack:** Python 3.12, PyMuPDF (`fitz`), Pydantic v2, existing `StoragePaths`, pytest.

---

## Stage Boundary

Node 3 creates a persisted text-evidence substrate. It must not implement BM25, hybrid retrieval, EvidencePacket fusion, UI display work, OCR, or a new retrieval endpoint. The manifest should be rich enough for Node 4 BM25 and later evidence spans, but the current page-image retrieval path must keep working.

## Latest-Code Surfaces To Preserve

- `IngestionService.accept_pdf_upload()` still renders pages, extracts page captions, indexes page images, and marks metadata ready.
- `IndexingService.index_pages()` still accepts optional `captions` and writes those captions into vector payloads.
- Current page evidence cards still receive caption text through existing vector payload behavior.
- The current `PdfRenderer` page rendering behavior and upload validation remain unchanged.
- Node 2 `EvidencePacket` remains page-grain; Node 3 does not wire text spans into packets yet.

## File Map

- Create: `apps/api/app/services/page_text_extractor.py`
  - Owns structured PyMuPDF extraction: page text, blocks, words, page dimensions, and quality stats.
- Create: `apps/api/app/services/text_manifest_store.py`
  - Owns deterministic JSON manifest persistence under `storage/indexes/text_manifests/{paper_id}.json`.
- Modify: `apps/api/app/services/ingestion_service.py`
  - Use the extractor/store to persist a text manifest after PDF rendering and before indexing.
  - Keep caption fallback passed into `index_pages`.
- Modify: `apps/api/app/services/indexing_service.py`
  - Keep current captions parameter and document/guard alignment with page paths if needed.
- Test: `apps/api/tests/test_page_text_extractor.py`
  - Born-digital, empty/weak page, blocks/words/page dimensions, deterministic page numbering.
- Test: `apps/api/tests/test_text_manifest_store.py`
  - Save/reload determinism, safe paper IDs, JSON shape.
- Modify or add tests where needed:
  - `apps/api/tests/test_ingestion_indexing.py` may need updates to assert caption fallback and manifest persistence.
- Update: `reports/final/results/text_manifest_quality.md`
  - Report-ready text quality/OCR limitation note.
- Update: `.planning/2026-06-22-paper-memory-evidence-agent/progress.md`
  - Commands, outcomes, review results.
- Update: `.planning/2026-06-22-paper-memory-evidence-agent/task_plan.md`
  - Node 3 status only after implementation/review gates.

## Manifest Shape

Use Pydantic models in `page_text_extractor.py` or `text_manifest_store.py`:

- `TextWord`
  - `text: str`
  - `bbox: tuple[float, float, float, float]`
  - `block_number: int | None`
  - `line_number: int | None`
  - `word_number: int | None`
- `TextBlock`
  - `block_number: int`
  - `text: str`
  - `bbox: tuple[float, float, float, float]`
  - `word_count: int`
- `PageTextQuality`
  - `char_count: int`
  - `word_count: int`
  - `block_count: int`
  - `has_text: bool`
  - `ocr_needed: bool`
  - `quality_label: Literal["good", "low_text", "empty"]`
- `PageTextEntry`
  - `paper_id: str`
  - `page_number: int`
  - `width: float`
  - `height: float`
  - `text: str | None`
  - `caption: str | None`
  - `blocks: list[TextBlock]`
  - `words: list[TextWord]`
  - `quality: PageTextQuality`
- `TextManifest`
  - `schema_version: Literal["text_manifest.v0"]`
  - `paper_id: str`
  - `page_count: int`
  - `pages: list[PageTextEntry]`

Quality rules for Node 3:

- Empty text: `has_text=False`, `quality_label="empty"`, `ocr_needed=True`.
- Low text: fewer than 20 characters or fewer than 3 words: `quality_label="low_text"`, `ocr_needed=True`.
- Good: otherwise `quality_label="good"`, `ocr_needed=False`.
- `caption` should be the same truncated page text used by current vector payloads, so caption fallback remains stable.
- Keep caption length compatible with the current `PdfRenderer._MAX_CAPTION_CHARS` limit unless a local constant is introduced.

## Subagent Plan

### Subagent A: Text Manifest Implementer

**Role:** worker.

**Write scope:** files listed in File Map.

**Task:** Implement structured extraction, manifest persistence, ingestion integration, tests, and report note.

- [ ] Create `page_text_extractor.py` with Pydantic models and a `PageTextExtractor.extract(pdf_path: Path, paper_id: str) -> TextManifest` API.
- [ ] Use PyMuPDF `page.get_text("text")`, `page.get_text("blocks")`, `page.get_text("words")`, and page rect dimensions.
- [ ] Create `text_manifest_store.py` with `save(manifest)`, `load(paper_id)`, `path_for(paper_id)`, and safe-paper-id validation.
- [ ] Modify `IngestionService` to extract and save the manifest after rendering.
- [ ] Preserve caption fallback by passing `[page.caption for page in manifest.pages]` into `IndexingService.index_pages`.
- [ ] Keep fallback behavior if extraction fails: upload should not invent text evidence; it may persist no manifest or failed/empty manifest only if tests define that behavior. Prefer failing softly only where current code already swallows extraction errors.
- [ ] Add tests for extractor and store.
- [ ] Update ingestion/indexing tests to prove captions still reach the indexer and manifest persists.
- [ ] Update `reports/final/results/text_manifest_quality.md`.
- [ ] Run required commands and update planning files.

Required commands:

```powershell
python -m pytest apps/api/tests/test_page_text_extractor.py apps/api/tests/test_text_manifest_store.py -q
python -m pytest apps/api/tests/test_ingestion_indexing.py apps/api/tests/test_phase1_local_pdf_to_evidence.py -q
python -m pytest apps/api/tests/test_evidence_contract.py apps/api/tests/test_public_evidence_response.py -q
```

### Subagent B: Node 3 Spec Reviewer

**Role:** default.

**Write scope:** none.

**Task:** Check implementation against this stage plan and the source superplan Node 3 section.

- [ ] Verify born-digital pages produce text, blocks, words, dimensions, and quality stats.
- [ ] Verify empty or low-text pages are marked `ocr_needed`.
- [ ] Verify manifest save/reload is deterministic and uses a safe storage path.
- [ ] Verify page numbers align with rendered page image numbering.
- [ ] Verify current caption fallback still reaches vector/indexing payloads.
- [ ] Verify report contribution exists.
- [ ] Verify no BM25/hybrid retrieval or UI work slipped in.

### Subagent C: Node 3 Quality Reviewer

**Role:** default.

**Write scope:** none.

**Task:** Check maintainability, failure behavior, and claim boundaries.

- [ ] Confirm extraction and persistence are separate, testable services.
- [ ] Confirm PyMuPDF details are isolated from ingestion logic.
- [ ] Confirm weak text is flagged rather than treated as reliable evidence.
- [ ] Confirm manifest JSON has stable ordering and no local-path leakage beyond storage-internal files.
- [ ] Confirm caption truncation is bounded and does not bloat vector payloads.
- [ ] Confirm report wording says Node 3 is text substrate/quality flags, not BM25 retrieval quality.

## Review Loop Limit

The controller may run at most two acceptance rounds for Node 3:

1. Round 1: implementation, spec review, quality review.
2. Round 2: targeted fixes only if either reviewer returns required fixes.

If Node 3 still fails after Round 2, leave it `blocked` or `in_progress_with_concerns` and record the exact remaining issue in `progress.md`.

## Final Node 3 Gate

Node 3 is accepted only when:

- All required commands pass.
- Spec review passes.
- Quality review passes.
- Each indexed paper can produce and reload a text manifest with quality flags.
- Existing caption-based retrieval evidence behavior remains compatible.
- `reports/final/results/text_manifest_quality.md` explains text quality and OCR limits.
- The next stage is still Node 4: BM25 Text Retriever.
