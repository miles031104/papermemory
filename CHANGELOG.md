# Changelog

## Unreleased

### Added

- Added bounded LLM retrieval planning before RAG lookup so PaperMemory can rewrite and decompose user questions before searching selected group evidence.
- Added page-level retrieval evidence preview with scrollable evidence cards and expanded image/text detail.
- Added Paper Manager table mode for managing the local paper library.
- Added delete actions for papers, libraries, groups, and conversations.
- Added a one-slide PaperMemory AI technical route presentation artifact.
- Added a Phase 1A local smoke test that creates a PDF, renders page images with PyMuPDF, indexes into embedded Qdrant local mode, and retrieves page evidence with a stub VisRAG backend.
- Added a Phase 1B API integration test that uploads PDFs, assigns ready papers to libraries, and verifies retrieval does not cross active library paper scopes.
- Added a Phase 1C API integration test that verifies uploaded library-scoped papers can drive `/chat` through EVisRAG-style prompting and a fake recording BYOK gateway without external model calls.
- Added `scripts/smoke-phase1-local.ps1` so developers can verify the PDF-to-library-scoped-evidence-to-chat chain without Docker or an API key.
- Added a Windows setup script that checks Python, npm, and Docker before installing PaperMemory locally.
- Added Qdrant local mode so users can run the vector database without Docker when they prefer a simpler local setup.
- Added a Windows start helper that explains how to launch Qdrant, the FastAPI backend, and the Next.js web app.
- Added a phase goals document that keeps the roadmap focused on the core PaperMemory MVP and paper manager before LLM Wiki expansion.
- Added shared BYOK provider presets and documentation for mainstream OpenAI-compatible providers, including Gemini, DeepSeek, Kimi/Moonshot, MiniMax, OpenRouter, MiMo through OpenRouter, Together AI, DashScope/Qwen, Mistral, Groq, xAI, and Custom endpoints.
- Added `AGENT.md` to define PaperMemory's evidence-first assistant contract, answer format, and hidden-reasoning policy.

### Improved

- Reworked the workspace into separate Home, Chat, Paper Manager, and Settings surfaces.
- Made Paper Manager a full-height management surface with a wider central table and a narrower library panel.
- Compactified Settings around Model Settings and synchronized env-derived provider defaults.
- Kept the default chat experience multimodal-first, using extracted text or OCR as fallback for text-only models.
- Split the web UI into a focused research workspace and a separate settings view for model, provider, HF, and multimodal setup.
- Reworked model settings so provider company selection uses the shared preset list while keeping base URL and model editable.
- Tightened chat prompting so answers use a stable Answer/Evidence/Limits shape instead of narrating retrieval steps.
- Expanded the agent contract with session/event boundaries, process visibility rules, failure policy, canonical citation schema, provider quirks, and evaluation fixtures.
- Made retrieval optional for chat so users can have general BYOK research conversations when no ready papers are scoped, while keeping paper-grounded citations tied to retrieved evidence.
- Documented the difference between Docker Qdrant server mode and embedded local Qdrant storage.
- Updated local setup guidance so users can open the web app through either `localhost:3000` or `127.0.0.1:3000`.
- Expanded default CORS origins to avoid false offline states when users open the app through the loopback address.

### Fixed

- Fixed stale API route behavior after restart by confirming the live service exposes conversation deletion.
- Fixed upload and chat request failures caused by offline or stale local API processes during local testing.
- Fixed paper and group move state handling across the Paper Manager and library panels.
- Fixed the web app's initial API URL so Phase 1D isolated-port smokes follow `NEXT_PUBLIC_API_BASE_URL` while defaulting to `http://localhost:8000`.
- Fixed misleading README guidance for Qdrant local mode by showing persistent `.env` configuration instead of invalid PowerShell assignments.
- Stripped only leading provider reasoning traces such as `<think>...</think>` from final model text, preserved literal tags inside normal answers, and rejected think-only responses instead of returning blank answers.

### Developer Notes

- Phase 1A is validated through `apps/api/tests/test_phase1_local_pdf_to_evidence.py`; Phase 1B scoped evidence search is validated through `apps/api/tests/test_phase1b_library_scoped_retrieval.py`; Phase 1C scoped fake-BYOK chat is validated through `apps/api/tests/test_phase1c_library_scoped_chat.py`.
- Added tests for Qdrant local path resolution, local vector-store client construction, default CORS origins, and CORS environment overrides.
