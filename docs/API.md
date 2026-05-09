# PaperMemory API Contract

This document is the repository-level API shape for the local-first MVP. Exact schemas may evolve with implementation, but the evidence and secret-handling boundaries should remain stable.

## Health

```http
GET /health
```

Returns service status and dependency readiness.

```json
{
  "status": "ok",
  "service": "PaperMemory API",
  "version": "0.1.0",
  "storage_root": "storage"
}
```

## Upload Paper

```http
POST /papers/upload
Content-Type: multipart/form-data
```

Fields:

- `file`: PDF file.
- `title`: optional display title.

Returns:

```json
{
  "paper": {
    "paper_id": "paper_123",
    "title": "Optional title",
    "filename": "paper.pdf",
    "status": "ready",
    "page_count": 12,
    "created_at": "2026-05-08T00:00:00Z"
  },
  "message": "PDF accepted, rendered into local page images, and indexed for VisRAG-style retrieval."
}
```

## List Papers

```http
GET /papers
```

Returns local paper metadata and ingestion status.

## Get Paper Status

```http
GET /papers/{paper_id}/status
```

Returns page rendering, embedding, and indexing progress.

## Search Pages

```http
POST /retrieval/search
Content-Type: application/json
```

Request:

```json
{
  "query": "What method does the paper propose?",
  "paper_ids": ["paper_123"],
  "top_k": 5
}
```

Response:

```json
{
  "query": "What method does the paper propose?",
  "evidence": [
    {
      "paper_id": "paper_123",
      "page_number": 1,
      "score": 0.82,
      "image_path": "storage/rendered_pages/paper_123/page-0001.png",
      "title": "Optional title",
      "caption": null,
      "metadata": {
        "embedding_model": "openbmb/VisRAG-Ret"
      }
    }
  ],
  "retrieval_model": "openbmb/VisRAG-Ret",
  "note": null
}
```

## Chat

```http
POST /chat
Content-Type: application/json
```

Request:

```json
{
  "question": "How does the evaluation compare to baselines?",
  "paper_ids": ["paper_123"],
  "top_k": 5,
  "provider": "openai-compatible",
  "base_url": "https://api.openai.com/v1",
  "model": "gpt-4o",
  "api_key": "session-only-secret"
}
```

Response:

```json
{
  "answer": "The paper reports stronger results than the listed baselines on...",
  "evidence": [
    {
      "paper_id": "paper_123",
      "page_number": 7,
      "score": 0.91,
      "image_path": "storage/rendered_pages/paper_123/page-0007.png",
      "caption": "Ablation results"
    }
  ],
  "model": "gpt-4o",
  "prompt_preview": "Use an EVisRAG-style evidence-first workflow...",
  "note": null
}
```

API keys should be accepted only for the active request/session unless the user explicitly opts into another storage model. They must never appear in logs or persisted chat records.
