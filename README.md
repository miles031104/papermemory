# PaperMemory

PaperMemory is a local-first, open-source research paper assistant for PDF-heavy
work. It uploads papers from your machine, renders pages as images, indexes page
evidence with a VisRAG-style retriever, and answers questions with your own model
API key.

The product idea is simple: your paper library should remember the pages, figures,
tables, and conversations that matter, without forcing you to send private PDFs
to a hosted service.

## What It Does

PaperMemory currently focuses on the local MVP path:

- Upload local PDF papers through the web UI.
- Store original PDFs and rendered page images under local storage.
- Render PDF pages with PyMuPDF for page-image retrieval.
- Index page evidence into Qdrant.
- Run either a lightweight stub retriever for development or real
  [`openbmb/VisRAG-Ret`](https://huggingface.co/openbmb/VisRAG-Ret) as an
  opt-in local backend.
- Search evidence inside the active research database/library.
- Keep multiple local paper databases, paper groups, and conversations.
- Ask general research questions, or evidence-grounded questions over the active database.
- Call generation models through bring-your-own-key OpenAI-compatible APIs.
- Optionally attach retrieved page images to multimodal model requests.
- Show page-level evidence and citations next to the answer.
- Keep API keys in browser/session state by default instead of writing them to
  project files.

PaperMemory is not trying to be a hosted collaboration platform in the MVP. Shared
databases, team workspaces, billing, and cloud indexing are future extensions; the
local mode should remain useful without accounts or centralized storage.

## Current Status

PaperMemory is early-stage but usable as a local developer MVP. The backend has
repeatable smokes for:

- PDF upload -> page rendering -> local storage.
- Qdrant local indexing with the development retriever.
- Active-library-scoped evidence retrieval.
- BYOK chat orchestration through an EVisRAG-style prompt boundary.
- Isolated frontend API-base configuration.

The real VisRAG-Ret path is implemented as an explicit opt-in backend because it
downloads large Hugging Face model weights and needs a Qdrant collection sized for
2304-dimensional embeddings. The default mode stays lightweight so contributors
can install and test the app without a GPU or external model key.

## Architecture

- `apps/web`: Next.js frontend for upload, libraries, conversations, settings,
  provider setup, and evidence review.
- `apps/api`: FastAPI backend for ingestion, retrieval, workspace persistence,
  and model gateway orchestration.
- `storage`: local PDFs, rendered page images, metadata, and embedded Qdrant data
  when local vector mode is used.
- Qdrant: vector store for page-level evidence, either through Docker/server mode
  or embedded local mode.
- BYOK gateway: OpenAI-compatible Chat Completions adapter that sends requests to
  `{base_url.rstrip("/")}/chat/completions`.

## Requirements

- Python 3.11+.
- Node.js 20+ and npm.
- Docker Desktop or another Docker Compose-compatible runtime if you want Qdrant
  server mode.
- Optional: CUDA-capable GPU for real VisRAG-Ret.
- Optional: Hugging Face token if your model download requires it.
- Optional: an API key from your chosen OpenAI-compatible model provider.

Docker is not mandatory. If Docker is unavailable or unwanted, PaperMemory can use
embedded Qdrant local mode through `qdrant-client`.

## Quick Start On Windows

From the repo root:

```powershell
.\scripts\setup-windows.ps1
```

The setup script will:

- Check Python and npm.
- Create `.env` from `.env.example` if needed.
- Detect whether Docker is installed and running.
- Use Docker Qdrant when available.
- Ask whether to install Docker Desktop with `winget` if Docker is missing.
- Fall back to Qdrant local mode if you decline Docker.
- Create the API virtual environment.
- Install API and web dependencies.

Then start the app:

```powershell
.\scripts\start-windows.ps1
```

The start script prepares Qdrant according to `.env` and prints the two app
commands. Run them in separate terminals:

```powershell
# Terminal 1: API
cd apps\api
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000

# Terminal 2: Web
cd apps\web
npm run dev
```

Open the web app at:

```text
http://localhost:3000
```

or:

```text
http://127.0.0.1:3000
```

## Setup Modes

Use the default auto mode for most local installs:

```powershell
.\scripts\setup-windows.ps1
```

Force Docker/server Qdrant:

```powershell
.\scripts\setup-windows.ps1 -VectorMode docker
```

Force embedded local Qdrant:

```powershell
.\scripts\setup-windows.ps1 -VectorMode local
```

Ask the script to install Docker Desktop through `winget` when Docker is missing:

```powershell
.\scripts\setup-windows.ps1 -InstallDocker
```

The setup script does not write Hugging Face tokens or model-provider API keys.

## Manual Install

If you prefer to run each step yourself:

```powershell
Copy-Item .env.example .env
```

For Docker Qdrant:

```powershell
docker compose up -d qdrant
```

For Qdrant local mode, edit `.env`:

```dotenv
PAPERMEMORY_QDRANT_MODE=local
PAPERMEMORY_QDRANT_LOCAL_PATH=storage/qdrant_local
```

Install and run the API:

```powershell
cd apps\api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Install and run the web app in a second terminal:

```powershell
cd apps\web
npm install
npm run dev
```

## Using PaperMemory

1. Open the web app.
2. Go to Settings and choose your install mode.
3. Configure Hugging Face settings if you plan to use real VisRAG-Ret.
4. Choose a generation provider preset or use Custom for any OpenAI-compatible
   endpoint.
5. Enter your API key in the settings UI. It is kept in browser state and sent
   with chat requests.
6. Return to Workspace.
7. Upload a PDF into the active database.
8. Wait for indexing to finish.
9. Ask a general research question, ask over the active papers, or search evidence.
10. Inspect the answer, cited pages, and retrieved evidence when paper context is used.

## BYOK Model Providers

PaperMemory's current model gateway supports OpenAI-compatible Chat Completions.
The frontend includes presets for:

- OpenAI.
- Google Gemini.
- DeepSeek.
- Kimi / Moonshot.
- MiniMax.
- OpenRouter.
- MiMo through OpenRouter.
- Together AI.
- Alibaba DashScope / Qwen.
- Mistral.
- Groq.
- xAI.
- Custom local or hosted endpoints.

See [BYOK Provider Presets](docs/BYOK_PROVIDERS.md) for base URLs, default models,
image-context notes, and protocol boundaries.

When image context is enabled, PaperMemory attaches retrieved page images as
OpenAI-style `image_url` data URLs. Use that only with a provider and model that
accepts image input. For text-only models, leave image context disabled and rely
on text snippets plus the evidence prompt.

Anthropic-native APIs are intentionally not listed as supported yet because they
use a different request shape. They can be added later through a separate gateway
adapter instead of pretending they are Chat Completions-compatible.

Some reasoning-oriented providers may place hidden traces in the visible content
field. PaperMemory redacts leading provider reasoning blocks before showing an
answer, preserves literal `<think>` text inside normal answers, and treats
think-only responses as provider errors instead of displaying a blank answer.

Retrieval is optional for chat. When the active database has no ready papers,
PaperMemory can still use your BYOK provider for general research conversation.
It simply marks the turn as not grounded in retrieved paper evidence. This leaves
room for later local memory layers such as paper notes, LLM Wiki pages, and a
knowledge graph to make conversation smarter without making PDF retrieval a hard
requirement for every message.

## Real VisRAG-Ret Mode

The default retriever is:

```dotenv
PAPERMEMORY_VISRAG_BACKEND=stub
PAPERMEMORY_QDRANT_VECTOR_SIZE=8
```

This keeps local development fast. To use real VisRAG-Ret:

```powershell
cd apps\api
.\.venv\Scripts\Activate.ps1
pip install -e ".[visrag]"
```

Then update `.env`:

```dotenv
PAPERMEMORY_VISRAG_BACKEND=transformers
PAPERMEMORY_VISRAG_MODEL_NAME=openbmb/VisRAG-Ret
PAPERMEMORY_VISRAG_TRUST_REMOTE_CODE=true
PAPERMEMORY_QDRANT_VECTOR_SIZE=2304
```

Recreate or clear the Qdrant collection before switching from the 8D development
stub to 2304D real embeddings. Qdrant collection dimensions are fixed.

Real VisRAG-Ret pulls model weights from Hugging Face, uses custom model code via
`trust_remote_code`, and is best run on a CUDA GPU. The model card's query example
prefixes text with:

```text
Represent this query for retrieving relevant documents:
```

## Configuration

Use `.env.example` as the canonical local configuration reference.

Important values:

- `NEXT_PUBLIC_API_BASE_URL`: URL used by the web app to call FastAPI.
- `PAPERMEMORY_STORAGE_ROOT`: local storage directory.
- `PAPERMEMORY_QDRANT_MODE`: `server` for Docker/server Qdrant, `local` for
  embedded storage.
- `PAPERMEMORY_QDRANT_URL`: server-mode Qdrant URL.
- `PAPERMEMORY_QDRANT_LOCAL_PATH`: embedded local Qdrant path.
- `PAPERMEMORY_VISRAG_BACKEND`: `stub` or `transformers`.
- `PAPERMEMORY_BYOK_BASE_URL`: default model provider base URL.
- `PAPERMEMORY_BYOK_MODEL`: default generation model.
- `PAPERMEMORY_BYOK_API_KEY`: optional developer fallback; prefer entering keys
  in the UI for normal local use.
- `PAPERMEMORY_BYOK_ENABLE_IMAGE_CONTEXT`: attach retrieved page images to model
  requests when the selected model supports image input.

Never commit real API keys, Hugging Face tokens, private PDFs, rendered page
images, or local vector storage.

## Verification

Run the Phase 1 local smoke without Docker or a real API key:

```powershell
.\scripts\smoke-phase1-local.ps1
```

Run backend tests:

```powershell
npm run test:api
```

Run frontend typecheck:

```powershell
npm run typecheck:web
```

Run the frontend production build:

```powershell
npm --prefix apps/web run build
```

If `npm run typecheck:web` complains about missing `.next/types`, run the Next.js
build once and then rerun typecheck.

## Roadmap

Near-term:

- Finish the core install -> upload -> index -> retrieve -> answer loop.
- Polish real VisRAG-Ret setup and error handling.
- Expand the paper manager page with real backend-backed paper groups, metadata,
  summaries, and paper detail panels.
- Improve ingestion job reliability and retry behavior.

Later:

- Generate durable paper notes with evidence links.
- Add LLM Wiki-style topic pages and cross-paper synthesis.
- Add optional shared workspaces and hosted collaboration without weakening the
  local-first baseline.

## Documentation

- [Agent Contract](AGENT.md)
- [Implementation Path](docs/IMPLEMENTATION_PATH.md)
- [Phase Goals](docs/PHASE_GOALS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [API Contract](docs/API.md)
- [BYOK Provider Presets](docs/BYOK_PROVIDERS.md)
- [Security Model](docs/SECURITY.md)

## Security And Privacy Notes

- Paper files and page images are stored locally by default.
- Qdrant can run locally through Docker or embedded local storage.
- Provider API keys should normally stay in the browser session.
- Environment API keys are for local developer testing and should not be
  committed.
- Hosted collaboration will require a separate security and data-retention design.
