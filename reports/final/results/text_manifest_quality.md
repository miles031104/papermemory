# Text Manifest Quality

Node 3 adds a persisted PyMuPDF text manifest for each successfully extracted
paper. The manifest is stored at:

```text
storage/indexes/text_manifests/{paper_id}.json
```

Each page record keeps selectable text, a bounded caption, text blocks, words,
page dimensions, and quality stats. The caption remains capped at the same
length used by the existing PDF caption fallback, so current page-image indexing
payloads stay bounded.

## Quality Labels

| Label | Rule | OCR flag |
| --- | --- | --- |
| `empty` | No selectable page text. | `ocr_needed=true` |
| `low_text` | Fewer than 20 characters or fewer than 3 words. | `ocr_needed=true` |
| `good` | Selectable text above both thresholds. | `ocr_needed=false` |

These labels are extraction-quality signals, not retrieval-quality metrics.
Pages marked `empty` or `low_text` should be treated as candidates for a later
OCR node before text retrieval claims are made.

## Scope Boundary

This node does not add BM25, hybrid retrieval, EvidencePacket text-span fusion,
OCR, UI display work, or a new retrieval endpoint. It only creates the local text
manifest substrate and preserves the current caption-based compatibility bridge
into page-image indexing.
