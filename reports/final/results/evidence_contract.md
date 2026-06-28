# Evidence Contract

Node 2 adds an additive evidence contract over the current page-image retrieval
surface. Existing `PageEvidence[]` responses remain present for current clients,
while `EvidencePacket` gives later nodes a deterministic envelope for citations,
validation state, and retrieval trace metadata.

This is a contract layer only. It does not add BM25, text manifests, hybrid
retrieval, UI redesign, or a new orchestrator.

## EvidenceUnit v0

| Field | Type | Node 2 meaning |
| --- | --- | --- |
| `evidence_id` | `str` | Stable visible page evidence id. |
| `paper_id` | `str` | Paper identifier from the current `PageEvidence`. |
| `page_number` | `int` | One-based page number. |
| `source` | `visrag_page \| text_page \| hybrid_page \| manual` | Current adapters use `visrag_page`. |
| `score` | `float \| null` | Current retrieval score when available. |
| `image_url` | `str \| null` | Public page image URL, not a local file path. |
| `title` | `str \| null` | Public, redacted title text from `PageEvidence`. |
| `caption` | `str \| null` | Public, redacted caption text from `PageEvidence`. |
| `metadata` | `dict[str, str] \| null` | Public metadata keys already allowed by `PageEvidence`. |
| `rank_trace` | `EvidenceRankTrace[]` | Retriever name, source, rank, and score trace. |
| `validation_state` | `unvalidated \| validated` | Validator marks units as `validated` after checks pass. |

## EvidenceCitation v0

| Field | Type | Node 2 meaning |
| --- | --- | --- |
| `evidence_id` | `str` | Referenced `EvidenceUnit.evidence_id`. |
| `paper_id` | `str` | Must match the referenced unit. |
| `page_number` | `int` | Must match the referenced unit. |
| `label` | `str \| null` | Current page label, for example `paper-1 p.3`. |

## EvidencePacket v0

| Field | Type | Node 2 meaning |
| --- | --- | --- |
| `schema_version` | `evidence_packet.v0` | Version tag for downstream nodes. |
| `packet_id` | `str` | Stable packet id from query, paper scope, and evidence ids. |
| `query` | `str \| null` | Retrieval or chat question text. |
| `paper_scope` | `list[str] \| null` | Active paper scope when provided. |
| `units` | `EvidenceUnit[]` | Page-grain evidence units. |
| `citations` | `EvidenceCitation[]` | Current page-level citations for each unit. |
| `limits` | `list[str]` | Retrieval or generation limits already surfaced to clients. |

## Visible Id Format

Evidence ids use:

```text
ev-{safe_paper_id}-p{page_number}-{digest8}
```

Example:

```text
ev-paper-1-p3-4f8a91c2
```

The digest is derived from `paper_id`, `page_number`, source label, and
normalized title/caption text. Local filesystem paths and `image_path` remain
excluded from public packet serialization.
