# PaperMemory Security Model

PaperMemory handles private papers, rendered page images, embeddings, prompts, and user-provided model API keys. The MVP security model is local-first and explicit-consent oriented.

## Local Data

By default, the following data stays on the user's machine:

- Uploaded PDFs.
- Rendered page images.
- SQLite metadata.
- Qdrant vectors and payloads.
- Retrieval results.
- Chat history, if enabled.

The app should make local storage paths visible to developers and should provide a deletion path for papers, page images, metadata rows, and vectors.

## BYOK Provider Keys

PaperMemory should prefer session-only keys entered by the user for multimodal generation. Environment variables are acceptable for local developer testing, but real keys must not be committed, logged, included in error messages, or returned to the frontend after submission.

Provider calls may send retrieved page images and prompt text to the user's chosen API provider. The UI and docs should make that boundary clear: local-first storage does not mean third-party model calls are local.

## Prompt And Evidence Handling

EVisRAG-style prompts should:

- Include only retrieved pages needed for the answer.
- Ask the model to cite page-level evidence.
- Ask the model to state when evidence is insufficient.
- Avoid hidden chain-of-thought requirements.

Logs should avoid storing prompts that contain private paper text, page images, or provider secrets.

## Future Hosted Collaboration

Hosted collaboration is outside the MVP trust boundary. Before enabling hosted mode, the project should define:

- Authentication and authorization.
- Workspace membership and role checks.
- Server-side encryption and key management.
- Provider-key delegation or vault storage.
- Paper, image, embedding, and chat retention.
- Export and deletion workflows.
- Audit logging that redacts private content and secrets.

Until those controls exist, local mode should remain the recommended path for private research material.
