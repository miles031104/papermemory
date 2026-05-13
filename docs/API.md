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

## Get Page Image

```http
GET /papers/{paper_id}/pages/{page_number}/image
```

Returns the locally rendered PNG for one indexed PDF page. The API validates `paper_id` and `page_number`, resolves the path under PaperMemory's rendered-pages storage, and returns `404` when the paper or page image is missing.

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

`paper_ids` has explicit scope semantics: omit it or send `null` for an unfiltered local collection search, and send `[]` for an intentionally empty scope. An empty scope returns no evidence and must not fall back to the full collection.

Response:

```json
{
  "query": "What method does the paper propose?",
  "evidence": [
    {
      "paper_id": "paper_123",
      "page_number": 1,
      "score": 0.82,
      "image_url": "/papers/paper_123/pages/1/image",
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

## Workspace

```http
GET /workspace
```

Returns local-first research workspace state from `storage/workspace/*.json`:

- `libraries`: research databases/document libraries.
- `conversations`: chats scoped to one library.
- `paper_groups`: lightweight paper organization groups scoped to one library.

The store creates a default `Inbox` library, default `Ungrouped uploads` paper group, and default conversation on first use. Existing local paper manifests are assigned to the Inbox.

```http
POST /workspace/libraries
PATCH /workspace/libraries/{library_id}
POST /workspace/libraries/{library_id}/conversations
PATCH /workspace/conversations/{conversation_id}
POST /workspace/libraries/{library_id}/paper-groups
PATCH /workspace/paper-groups/{group_id}
```

`PATCH /workspace/libraries/{library_id}` accepts `paper_ids`, so the web app can assign a newly uploaded PDF to the active database without introducing a hosted account or external metadata database.

Relationship updates are validated locally: library `paper_ids` must exist as paper manifests, library `group_ids` must belong to that library, and paper-group `paper_ids` must already belong to the same library.

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
      "image_url": "/papers/paper_123/pages/7/image",
      "caption": "Ablation results"
    }
  ],
  "model": "gpt-4o",
  "prompt_preview": "Use an EVisRAG-style evidence-first workflow...",
  "note": null
}
```

API keys should be accepted only for the active request/session unless the user explicitly opts into another storage model. They must never appear in logs or persisted chat records.

Frontend evidence cards should use `image_url` for browser-safe page previews. Public evidence responses must not expose local `image_path` values.
