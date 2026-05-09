# PaperMemory Implementation Path

## 1. Current Branch Goal

Branch: `miles`

The goal of this branch is to turn PaperMemory into a local-first, open-source paper assistant agent.

The first usable version should let users:

- Run the app locally from GitHub.
- Upload PDF papers.
- Index paper pages with a VisRAG-style visual retriever.
- Store page embeddings in a local vector database.
- Ask questions through a web UI.
- Use their own multimodal model API key for generation.
- Receive answers with page-level evidence and citations.

The commercial direction can be kept in mind, but the initial implementation should optimize for a clean local developer experience and a useful self-hosted product.

## 2. Product Boundary

### MVP

- Local web frontend.
- Local backend API.
- Local file storage.
- Local Qdrant vector database.
- User-provided model API key.
- Visual page retrieval as the main retrieval path.
- Evidence-first answer formatting inspired by EVisRAG.

### Not MVP

- Hosted SaaS accounts.
- Billing.
- Shared team workspace.
- Shared public paper database.
- Default self-hosted EVisRAG generation.
- Complex multi-agent orchestration.

## 3. Recommended Tech Stack

### Frontend

- Next.js App Router.
- TypeScript.
- Tailwind CSS.
- shadcn/ui or a small local component layer.

The frontend should provide upload, library, chat, settings, and evidence viewing screens.

### Backend

- Python FastAPI.
- Pydantic settings and schemas.
- Background ingestion jobs.
- Provider adapters for OpenAI-compatible multimodal APIs.

Python should own PDF rendering, model embedding, Qdrant operations, and BYOK model calls.

### Retrieval

- `openbmb/VisRAG-Ret` as the first primary retriever.
- One vector per rendered PDF page.
- Qdrant as the vector database.
- Keep `stub` retrieval as the safe default with 8-dimensional vectors.
- Enable real VisRAG-Ret through the `transformers` backend, optional `visrag` API extra, `trust_remote_code=true`, and Qdrant vector size `2304`.

### Storage

- Local filesystem for PDFs and rendered page images.
- SQLite for local metadata in MVP.
- PostgreSQL-compatible schema later for hosted and collaboration modes.

## 4. Target Repository Structure

```text
papermemory/
  README.md
  docker-compose.yml
  .env.example

  apps/
    web/
      package.json
      src/
        app/
        components/
        lib/

    api/
      pyproject.toml
      app/
        main.py
        core/
        models/
        routers/
        services/
        workers/

  packages/
    shared/
      schemas/

  docs/
    IMPLEMENTATION_PATH.md
    API.md
    ARCHITECTURE.md
    SECURITY.md

  storage/
    .gitkeep
```

This keeps frontend, backend, and shared interface documentation separated while remaining easy to run locally.

## 5. Backend Service Boundaries

### Ingestion Service

Responsibilities:

- Accept uploaded PDFs.
- Save original PDF files.
- Render PDF pages to images.
- Create paper and page metadata records.
- Queue embedding jobs.

Suggested module:

```text
apps/api/app/services/ingestion_service.py
```

### Visual Retrieval Service

Responsibilities:

- Load `openbmb/VisRAG-Ret`.
- Encode page images.
- Encode user queries.
- Normalize embeddings.
- Search Qdrant.

Suggested module:

```text
apps/api/app/services/visrag_service.py
```

### Vector Store Service

Responsibilities:

- Create Qdrant collections.
- Upsert page vectors.
- Search by user, paper, collection, or workspace filter.
- Return page metadata and retrieval scores.

Suggested module:

```text
apps/api/app/services/vector_store.py
```

### Model Gateway

Responsibilities:

- Call the user's configured multimodal API from the backend.
- Support OpenAI-compatible chat completions first.
- Hide provider-specific formatting behind adapters.
- Redact API keys from logs and error messages.

Suggested module:

```text
apps/api/app/services/model_gateway.py
```

### Chat Orchestrator

Responsibilities:

- Receive user question.
- Retrieve top-k paper pages.
- Build EVisRAG-style multimodal prompt.
- Call the model gateway.
- Parse structured answer and evidence.
- Return citations to the frontend.

Suggested module:

```text
apps/api/app/services/chat_service.py
```

## 6. Core API Draft

### Upload Paper

```http
POST /papers/upload
Content-Type: multipart/form-data
```

Returns:

```json
{
  "paper_id": "string",
  "status": "queued"
}
```

### List Papers

```http
GET /papers
```

### Get Ingestion Status

```http
GET /papers/{paper_id}/status
```

### Retrieve Pages

```http
POST /retrieval/search
```

Body:

```json
{
  "question": "string",
  "paper_ids": ["string"],
  "top_k": 5
}
```

### Chat

```http
POST /chat
```

Body:

```json
{
  "question": "string",
  "paper_ids": ["string"],
  "top_k": 5,
  "provider": "openai-compatible",
  "base_url": "https://api.openai.com/v1",
  "model": "gpt-4o",
  "api_key": "session-only-secret"
}
```

## 7. EVisRAG-Style Prompt Contract

The generation prompt should require the model to:

1. Observe each retrieved page image.
2. Record evidence page by page.
3. Reason only from the evidence.
4. Return an answer with citations.
5. State when evidence is insufficient.

Expected response shape:

```json
{
  "answer": "string",
  "evidence": [
    {
      "image_index": 1,
      "paper_id": "string",
      "paper_title": "string",
      "page_number": 1,
      "relevance": "high",
      "evidence": "string"
    }
  ],
  "insufficient": false,
  "suggested_next_retrieval": null
}
```

This keeps the product usable with BYOK multimodal APIs before self-hosted EVisRAG is added.

## 8. Development Phases

### Phase 1: Repo Scaffold

- Add `apps/web`.
- Add `apps/api`.
- Add `.env.example`.
- Add `docker-compose.yml` with Qdrant.
- Add basic setup instructions.

### Phase 2: Paper Ingestion

- Implement PDF upload endpoint.
- Store PDFs locally.
- Render pages to images.
- Save paper/page metadata in SQLite.
- Show uploaded papers in the frontend.

### Phase 3: VisRAG Indexing

- Load `openbmb/VisRAG-Ret`.
- Use the [`openbmb/VisRAG-Ret`](https://huggingface.co/openbmb/VisRAG-Ret) Transformers path with custom code enabled only when `PAPERMEMORY_VISRAG_TRUST_REMOTE_CODE=true`.
- Resolve `auto` device/dtype settings, preferring CUDA/BF16 when available and falling back to CPU-compatible settings.
- Encode rendered page images.
- Prefix text queries with `Represent this query for retrieving relevant documents:`.
- Create Qdrant collection.
- Use vector size `2304` for real VisRAG-Ret embeddings; keep size `8` only for stub mode.
- Upsert page vectors with payload metadata.
- Add ingestion status UI.

### Phase 4: Retrieval

- Encode text queries with the VisRAG query instruction.
- Search Qdrant.
- Return top-k page previews.
- Add paper filter and top-k controls.

### Phase 5: BYOK Chat

- Add model settings UI.
- Implement OpenAI-compatible multimodal adapter.
- Build EVisRAG-style prompt and image input.
- Return structured answer, evidence, and citations.

### Phase 6: Local Release Polish

- Add README quickstart.
- Add example workflow.
- Add smoke tests.
- Add secret-handling notes.
- Add troubleshooting for GPU/CPU and provider API limits.

### Phase 7: Collaboration-Ready Foundation

- Add `user_id` and `workspace_id` concepts to metadata.
- Keep local mode as default.
- Prepare migration path from SQLite to PostgreSQL.
- Document future shared database and hosted deployment boundaries.

## 9. Early Engineering Decisions

- Use visual page retrieval as the default path.
- Add text extraction only as fallback or hybrid enhancement.
- Start with OpenAI-compatible APIs because many providers expose this shape.
- Keep provider adapters modular.
- Keep API keys session-only by default.
- Do not log prompts containing user paper images or API keys.
- Avoid LangGraph until there is a real multi-step workflow that needs state, loops, or human approval.

## 10. First Concrete Coding Task

The next implementation step should be repository scaffolding:

1. Create `apps/api` FastAPI skeleton.
2. Create `apps/web` Next.js skeleton.
3. Add `docker-compose.yml` for Qdrant.
4. Add `.env.example`.
5. Add a README quickstart for local development.

After that, implement upload and page rendering before touching VisRAG model loading. This gives the project a working product shell early and keeps model integration isolated.
