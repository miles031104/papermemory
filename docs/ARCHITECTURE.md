# PaperMemory Architecture

PaperMemory is a local-first paper assistant. The MVP keeps user papers, page images, embeddings, metadata, and model-provider configuration on the user's machine.

## Runtime Components

```text
Next.js web app
      -> FastAPI backend
      -> local filesystem storage
      -> JSON paper metadata manifests
      -> JSON workspace store
      -> VisRAG-Ret page/query encoder
      -> Qdrant local vector database
      -> BYOK multimodal model provider
```

## VisRAG-Ret Backend Modes

PaperMemory has two retriever backend modes:

- `stub`: default local-development mode. It avoids model downloads and uses 8-dimensional deterministic vectors.
- `transformers`: real local [`openbmb/VisRAG-Ret`](https://huggingface.co/openbmb/VisRAG-Ret) mode. Use `PAPERMEMORY_QDRANT_VECTOR_SIZE=2304` and recreate the Qdrant collection before indexing.

The real adapter should expose `PAPERMEMORY_VISRAG_DEVICE` as `auto`, `cpu`, or `cuda`; `PAPERMEMORY_VISRAG_DTYPE` as `auto`, `float32`, `float16`, or `bfloat16`; `PAPERMEMORY_VISRAG_BATCH_SIZE`; and `PAPERMEMORY_VISRAG_TRUST_REMOTE_CODE`. The Hugging Face model card loads the tokenizer/model with `trust_remote_code=True`, shows BF16/CUDA usage, lists PyTorch, torchvision, Transformers, sentencepiece, and Pillow among its example requirements, and uses the query prefix `Represent this query for retrieving relevant documents:`. Because the model is not hosted by Hugging Face Inference Providers, this mode runs locally and a GPU is recommended.

## Ingestion Flow

1. User uploads a PDF through the web app.
2. The API stores the original PDF under local storage.
3. The API renders each PDF page to a local PNG image with PyMuPDF.
4. A paper metadata manifest is written beside the stored PDF.
5. The indexing service encodes each page image with `openbmb/VisRAG-Ret`.
6. Page vectors are upserted into Qdrant with payload metadata.

Payload metadata should include paper ID, page ID, page number, title when known, and internal local paths needed for server-side retrieval. Public API responses expose browser-safe `image_url` values instead of local paths. The MVP writes paper manifests as JSON files beside stored PDFs; SQLite or PostgreSQL can replace this layer once background jobs and collaboration are added.

## Workspace Store

The local workspace model is persisted under `storage/workspace/` as JSON:

- `libraries.json`: research databases/document libraries with `paper_ids` and `group_ids`.
- `conversations.json`: chat threads scoped to one library, including messages and citations.
- `paper_groups.json`: lightweight groups for organizing papers inside a library.

On first use, PaperMemory creates an Inbox library, an Ungrouped uploads paper group, and a default research conversation. Existing uploaded paper manifests are assigned to Inbox so the left-side Codex-style workspace has a real backend state immediately. API keys and Hugging Face tokens remain frontend runtime state and are not written to this workspace store.

## Retrieval And Answering Flow

1. User asks a question and optionally filters papers.
2. The API encodes the text query with the VisRAG retrieval service.
3. Qdrant returns top-k page candidates.
4. The chat orchestrator builds an EVisRAG-style evidence prompt with retrieved page images.
5. The model gateway calls the user's configured multimodal API.
6. The API returns an answer, evidence records, and page citations to the frontend.

The model should be instructed to reason from retrieved page images, cite page-level evidence, and state when the evidence is insufficient.

The frontend treats `image_url` as the browser-safe evidence image contract. When multimodal BYOK is enabled, users should choose a vision-capable OpenAI-compatible provider/model and cap the number of attached page images to keep requests predictable. Moving from the 8D stub retriever to real 2304D VisRAG-Ret requires recreating the Qdrant collection and reindexing PDFs because collection vector dimensions are fixed.

## Local-First Boundary

The default product must work without PaperMemory-operated infrastructure. Hosted collaboration can be added later, but should require explicit decisions for:

- Account and workspace identity.
- Server-side paper and image storage.
- Secret storage and provider-key delegation.
- Data retention and deletion.
- Access control on papers, embeddings, and chat history.
- Migration from SQLite to PostgreSQL-compatible metadata storage.

Local-first behavior is not a prototype detail; it is the baseline trust model.
