# Changelog

## Unreleased

### Added

- Added a Windows setup script that checks Python, npm, and Docker before installing PaperMemory locally.
- Added Qdrant local mode so users can run the vector database without Docker when they prefer a simpler local setup.
- Added a Windows start helper that explains how to launch Qdrant, the FastAPI backend, and the Next.js web app.
- Added a phase goals document that keeps the roadmap focused on the core PaperMemory MVP and paper manager before LLM Wiki expansion.

### Improved

- Documented the difference between Docker Qdrant server mode and embedded local Qdrant storage.
- Updated local setup guidance so users can open the web app through either `localhost:3000` or `127.0.0.1:3000`.
- Expanded default CORS origins to avoid false offline states when users open the app through the loopback address.

### Fixed

- Fixed misleading README guidance for Qdrant local mode by showing persistent `.env` configuration instead of invalid PowerShell assignments.

### Developer Notes

- Added tests for Qdrant local path resolution, local vector-store client construction, default CORS origins, and CORS environment overrides.
