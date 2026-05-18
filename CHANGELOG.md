# Changelog

## Unreleased

### Added

- Added a Phase 1A local smoke test that creates a PDF, renders page images with PyMuPDF, indexes into embedded Qdrant local mode, and retrieves page evidence with a stub VisRAG backend.
- Added a Phase 1B API integration test that uploads PDFs, assigns ready papers to libraries, and verifies retrieval does not cross active library paper scopes.
- Added a Phase 1C API integration test that verifies uploaded library-scoped papers can drive `/chat` through EVisRAG-style prompting and a fake recording BYOK gateway without external model calls.
- Added `scripts/smoke-phase1-local.ps1` so developers can verify the PDF-to-library-scoped-evidence-to-chat chain without Docker or an API key.
- Added a Windows setup script that checks Python, npm, and Docker before installing PaperMemory locally.
- Added Qdrant local mode so users can run the vector database without Docker when they prefer a simpler local setup.
- Added a Windows start helper that explains how to launch Qdrant, the FastAPI backend, and the Next.js web app.
- Added a phase goals document that keeps the roadmap focused on the core PaperMemory MVP and paper manager before LLM Wiki expansion.

### Improved

- Documented the difference between Docker Qdrant server mode and embedded local Qdrant storage.
- Updated local setup guidance so users can open the web app through either `localhost:3000` or `127.0.0.1:3000`.
- Expanded default CORS origins to avoid false offline states when users open the app through the loopback address.

### Fixed

- Fixed the web app's initial API URL so Phase 1D isolated-port smokes follow `NEXT_PUBLIC_API_BASE_URL` while defaulting to `http://localhost:8000`.
- Fixed misleading README guidance for Qdrant local mode by showing persistent `.env` configuration instead of invalid PowerShell assignments.

### Developer Notes

- Phase 1A is validated through `apps/api/tests/test_phase1_local_pdf_to_evidence.py`; Phase 1B scoped evidence search is validated through `apps/api/tests/test_phase1b_library_scoped_retrieval.py`; Phase 1C scoped fake-BYOK chat is validated through `apps/api/tests/test_phase1c_library_scoped_chat.py`.
- Added tests for Qdrant local path resolution, local vector-store client construction, default CORS origins, and CORS environment overrides.
