# Node 6: Verified Chat and Evidence UI

## Scope

Node 6 connects validated `EvidencePacket` output to scoped chat prompts, SSE frames, and the existing evidence panel. It does not add the Node 7 multi-pass orchestrator, new retrieval algorithms, dense text embeddings, OCR, or a broad UI redesign.

## Implementation Summary

- `ChatRequest.retrieval_mode` now supports `"hybrid"` and `"visual"`, with `"hybrid"` as the product-facing default for scoped chat.
- The chat router constructs `HybridRetrievalService` from the existing VisRAG service, vector store, and `TextManifestStore`.
- Scoped hybrid chat preserves the Node 5 packet, including `hybrid_page` units and `visrag`/`bm25` rank traces, instead of rebuilding a visual-only packet.
- Prompt context now renders accepted packet units with `evidence_id`, citation label, source modality, rank trace, score, image reference, caption/snippet, and packet limits.
- Final citation filtering is bounded to accepted packet citation pages for the active paper scope.
- SSE order remains: early `evidence` frame, token `delta` frames, final `done` frame. Early and done frames both include `evidence_packet`.
- The web client parses packets from streaming frames, stores the latest packet, builds assistant citation chips from packet citations, and displays packet source modality and limits in the existing evidence panel.

## Demo Evidence

The Node 6 demo should show:

1. A scoped chat turn with `retrieval_mode="hybrid"`.
2. The early evidence panel filling before the streamed answer begins.
3. Evidence cards labeled by packet provenance, such as `Hybrid`, `VisRAG-Ret`, or `BM25 text`.
4. Visible packet limits when text manifests are missing or generation falls back to text-only evidence.
5. Citation chips jumping only to accepted packet pages.
6. Conversation mode still answering without paper evidence when no ready paper scope is active.

## Verification Snapshot

- `python -m pytest apps/api/tests/test_chat_prompt.py apps/api/tests/test_chat_streaming.py apps/api/tests/test_chat_service_agentic.py apps/api/tests/test_public_evidence_response.py -q` passed with `44 passed`.
- `python -m pytest apps/api/tests/test_evidence_contract.py apps/api/tests/test_hybrid_retrieval_service.py -q` passed with `16 passed`.
- `npm install` restored frontend dependencies; it reported two moderate audit findings, and no forced dependency changes were applied.
- `npm --prefix apps/web run typecheck` passed.

## Claim Boundary

This node demonstrates packet-visible, citation-bounded scoped chat and UI provenance over the current visual/hybrid retrieval stack. It is not a claim that PaperMemory now performs autonomous multi-pass research planning; that remains Node 7.
