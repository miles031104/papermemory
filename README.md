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

- Python 3.11+ for the API.
- Node.js 20+ for the web app.
- Docker Desktop or another Docker Compose-compatible runtime if you want the default Qdrant server mode.
- A multimodal model API key from a provider you choose.

The API uses PyMuPDF for the first VisRAG ingestion step: rendering each uploaded PDF page into a local page image.

### Windows Setup

The Windows setup script checks Python, npm, Docker availability, prepares `.env`, installs the API and web dependencies, and configures the vector database mode:

```powershell
.\scripts\setup-windows.ps1
```

By default, `-VectorMode auto` uses Docker Qdrant when Docker is installed and running. If Docker is not usable, the script asks whether to install Docker Desktop with `winget`; declining switches PaperMemory to Qdrant local mode. You can also choose explicitly:

```powershell
.\scripts\setup-windows.ps1 -VectorMode docker
.\scripts\setup-windows.ps1 -VectorMode local
.\scripts\setup-windows.ps1 -InstallDocker
```

The script only updates Qdrant-related environment values. It does not write API keys or Hugging Face tokens.

### Start Local Services

Copy the environment template and start Qdrant server mode:

```powershell
Copy-Item .env.example .env
docker compose up -d qdrant
```

Qdrant will be available at `http://localhost:6333`.

If Docker is unavailable or unwanted, edit `.env` and add or update these lines:

```dotenv
PAPERMEMORY_QDRANT_MODE=local
PAPERMEMORY_QDRANT_LOCAL_PATH=storage/qdrant_local
```

The default local database path is `storage/qdrant_local`. A relative `PAPERMEMORY_QDRANT_LOCAL_PATH` that starts with `storage` is resolved from the repo root; other relative local paths are resolved under `PAPERMEMORY_STORAGE_ROOT`. Local mode uses qdrant-client embedded storage and does not require Docker.

To prepare Qdrant according to `.env` and see the startup commands:

```powershell
.\scripts\start-windows.ps1
```

To verify the Phase 1 local evidence chain without Docker or an API key:

```powershell
.\scripts\smoke-phase1-local.ps1
```

The smoke creates temporary PDFs, renders them with PyMuPDF, indexes page images into embedded Qdrant local mode with the stub VisRAG backend, associates ready papers with libraries, verifies retrieval only returns evidence from the active library paper scope, and exercises `/chat` through a fake recording BYOK gateway without calling an external model.

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

Open the web app at `http://localhost:3000` or `http://127.0.0.1:3000`; API CORS defaults allow both. The web app should talk to the local API at `http://localhost:8000`. In server/Docker mode, the API talks to Qdrant at `http://localhost:6333`; in local mode, it uses `PAPERMEMORY_QDRANT_LOCAL_PATH` and does not start an HTTP Qdrant service.

## Configuration

Use `.env.example` as the canonical list of local settings. PaperMemory should prefer session-only API keys for BYOK chat; environment keys are useful for local developer testing but must not be logged, committed, or sent to hosted services without explicit user consent.

The default retriever backend is `PAPERMEMORY_VISRAG_BACKEND=stub`, which keeps local development lightweight and uses `PAPERMEMORY_QDRANT_VECTOR_SIZE=8`. To use the real [`openbmb/VisRAG-Ret`](https://huggingface.co/openbmb/VisRAG-Ret) adapter, install the API extra with `pip install -e ".[visrag]"`, set `PAPERMEMORY_VISRAG_BACKEND=transformers`, set `PAPERMEMORY_VISRAG_TRUST_REMOTE_CODE=true`, and recreate the Qdrant collection with `PAPERMEMORY_QDRANT_VECTOR_SIZE=2304`.

Real VisRAG-Ret pulls large model weights from Hugging Face, uses custom model code loaded with `trust_remote_code`, and is best run with a CUDA GPU. The model card's example dependencies include PyTorch, torchvision, Transformers, sentencepiece, and Pillow; its query example prefixes text with `Represent this query for retrieving relevant documents:`. The model card also notes that it is not deployed by Hugging Face Inference Providers, so PaperMemory runs it locally through the Transformers adapter.

## Documentation

- [Implementation Path](docs/IMPLEMENTATION_PATH.md)
- [Phase Goals](docs/PHASE_GOALS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [API Contract](docs/API.md)
- [Security Model](docs/SECURITY.md)

## Project Status

PaperMemory is early-stage. Phase 1A has a repeatable local smoke for PDF -> page images -> Qdrant local -> evidence retrieval, Phase 1B verifies upload -> active library association -> library-scoped evidence search, and Phase 1C verifies the scoped BYOK chat path with a fake recording model gateway. The current branch is still focused on completing the rest of the local developer path: real VisRAG opt-in, evidence review polish, and frontend BYOK chat integration.
