# PaperMemory Local Run Notes

Date recorded: 2026-06-24

These notes describe the stable local run path for the Node 0 baseline at commit `6884d738df9d685bad4f5a673a7d13a7bc2fb691` on branch `codex/papermemory-evidence-agent`.

## One-Time Setup

From the repository root:

```powershell
.\scripts\setup-windows.ps1
```

Manual equivalent:

```powershell
Copy-Item .env.example .env
npm ci
cd apps\api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

For a local no-Docker vector store, set these values in `.env`:

```dotenv
PAPERMEMORY_QDRANT_MODE=local
PAPERMEMORY_QDRANT_LOCAL_PATH=storage/qdrant_local
```

For real VisRAG-Ret, install the optional API extras and use the 2304-dimensional Qdrant collection settings documented in `README.md`. The default development path uses the stub retriever and does not require a GPU.

## Start The App

Terminal 1, API:

```powershell
cd apps\api
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

Terminal 2, web:

```powershell
cd apps\web
npm run dev
```

Open:

```text
http://localhost:3000
```

or:

```text
http://127.0.0.1:3000
```

## Pre-Recording Checks

Run these from the repository root before recording a demo:

```powershell
git status --short --branch
npm --prefix apps/web run typecheck
python -m pytest apps/api/tests/test_chat_service_agentic.py apps/api/tests/test_chat_streaming.py apps/api/tests/test_public_evidence_response.py -q
```

Current Node 0 result:

- API smoke subset passes: `25 passed in 2.79s`.
- Web typecheck fails until the local frontend dependency install includes `react-markdown` and `remark-gfm`.
- `git status --short --branch` reports permission warnings for `.tmp_pytest_visrag_contract/base/` and `pytest-tmp/`, plus untracked planning artifacts.

## Demo Boundary

This note records the README-documented intended baseline flow: upload PDFs, render page images, index page evidence, scope retrieval to the active library/group, ask BYOK-backed chat questions, and inspect page-level evidence. Node 0 did not verify the full local app or demo flow end to end. Restore the frontend dependency install and rerun `npm --prefix apps/web run typecheck` before treating the web path as clean for recording. Later evidence-agent nodes should add report/demo artifacts incrementally without replacing this intended baseline route.
