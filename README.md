# PaperMemory

PaperMemory is a local-first, open-source research paper assistant. It is designed to run on a developer machine, index PDF pages into a local Qdrant vector database, retrieve visual page evidence with VisRAG-Ret, and answer questions through a bring-your-own-key multimodal model API.

The project goal is practical paper memory: upload papers, retrieve the most relevant page images, ask questions, and get evidence-grounded answers with page citations. The first release keeps user papers, rendered pages, embeddings, metadata, and API keys under local control.

## Architecture At A Glance

- Next.js frontend for upload, library, chat, settings, and evidence review.
- Python FastAPI backend for ingestion, retrieval, model calls, and orchestration.
- Qdrant for local page-image vector search.
- Local filesystem storage for PDFs and rendered page images.
- VisRAG-Ret as the first visual retriever for page-level embeddings.
- BYOK multimodal generation through OpenAI-compatible provider adapters.
- EVisRAG-style prompting that asks the model to inspect retrieved pages, cite evidence, and admit when evidence is insufficient.

Hosted collaboration is a future boundary, not the MVP default. Local mode should remain useful without accounts, billing, shared cloud storage, or centrally managed paper databases.

## Local Development

### Prerequisites

- Docker Desktop or another Docker Compose-compatible runtime.
- Python 3.11+ for the API.
- Node.js 20+ for the web app.
- A multimodal model API key from a provider you choose.

The API uses PyMuPDF for the first VisRAG ingestion step: rendering each uploaded PDF page into a local page image.

### Start Local Services

Copy the environment template and start Qdrant:

```powershell
Copy-Item .env.example .env
docker compose up -d qdrant
```

Qdrant will be available at `http://localhost:6333`.

### Run The Apps

The backend and frontend live under `apps/api` and `apps/web` as they are implemented. The intended local flow is:

```powershell
# API
cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000

# Web, in a second terminal
cd apps/web
npm install
npm run dev
```

The web app should talk to the local API at `http://localhost:8000`, and the API should talk to Qdrant at `http://localhost:6333`.

## Configuration

Use `.env.example` as the canonical list of local settings. PaperMemory should prefer session-only API keys for BYOK chat; environment keys are useful for local developer testing but must not be logged, committed, or sent to hosted services without explicit user consent.

The default retriever backend is `PAPERMEMORY_VISRAG_BACKEND=stub`, which keeps local development lightweight and uses `PAPERMEMORY_QDRANT_VECTOR_SIZE=8`. To use the real [`openbmb/VisRAG-Ret`](https://huggingface.co/openbmb/VisRAG-Ret) adapter, install the API extra with `pip install -e ".[visrag]"`, set `PAPERMEMORY_VISRAG_BACKEND=transformers`, set `PAPERMEMORY_VISRAG_TRUST_REMOTE_CODE=true`, and recreate the Qdrant collection with `PAPERMEMORY_QDRANT_VECTOR_SIZE=2304`.

Real VisRAG-Ret pulls large model weights from Hugging Face, uses custom model code loaded with `trust_remote_code`, and is best run with a CUDA GPU. The model card's example dependencies include PyTorch, torchvision, Transformers, sentencepiece, and Pillow; its query example prefixes text with `Represent this query for retrieving relevant documents:`. The model card also notes that it is not deployed by Hugging Face Inference Providers, so PaperMemory runs it locally through the Transformers adapter.

## Documentation

- [Implementation Path](docs/IMPLEMENTATION_PATH.md)
- [Architecture](docs/ARCHITECTURE.md)
- [API Contract](docs/API.md)
- [Security Model](docs/SECURITY.md)

## Project Status

PaperMemory is early-stage. The current branch is focused on building the local developer path first: scaffold, ingest PDFs, render pages, index page images, retrieve evidence, and then add BYOK multimodal chat.
