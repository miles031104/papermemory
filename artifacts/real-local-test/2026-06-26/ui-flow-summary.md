# UI Flow Summary

## Tooling

- Browser automation: Playwright CLI (`@playwright/cli`) against `http://127.0.0.1:3000`.
- API checks: `http://127.0.0.1:8000`.
- API key was not entered into the UI and `.env` was not read by UI workers.

## Screenshots

- Initial/settings reconnaissance: `ui-initial.png`, `ui-settings.png`, `ui-settings-recon.png`.
- Paper Manager reconnaissance: `ui-manager-recon.png`, `ui-upload-recon.png`.
- Final upload state: `ui-cli-upload-missing-final.png`.
- Chat/evidence state: `ui-search-evidence.png`.
- Evidence preview modal: `ui-evidence-preview.png`.

## Settings

- API online indicator was visible in the app chrome.
- Settings page rendered FastAPI URL, API key, Attach page images, and Max evidence images controls.
- API key field was left blank so server `.env` fallback remains the later BYOK test path.
- Max evidence images was visible as `4`; backend clamp is still tested through Task 5 direct API.

## Upload Results

- `visrag-core.pdf`: uploaded through UI and ready as `Real Test VisRAG Core`, 2 pages.
- `bm25-exact.pdf`: uploaded through UI and ready as `Real Test BM25 Exact`, 3 pages.
- `agent-robustness.pdf`: uploaded through UI and ready as `Real Test Agent Robustness`, 3 pages.
- Test pollution: one duplicate `visrag-core.pdf` upload was created during failed subagent automation. It remains in the local workspace and is recorded as a UI automation artifact, not an intended corpus item.

Final `/papers` contains four ready papers: the three required controlled PDFs plus the duplicate `visrag-core.pdf`.

## Chat And Evidence

- Chat page showed `4 ready paper(s), 10 indexed page(s)`.
- `Search evidence` was run for: `Which pages describe BM25 exact matching and malicious evidence text?`
- Backend logged `POST /retrieval/search` with HTTP `200`.
- Evidence cards appeared in the right panel with paper title, page number, Hybrid retriever label, snippet, confidence, and thumbnail area.
- Evidence preview modal opened for `Real Test Agent Robustness`, page 3.
- The preview displayed the malicious evidence text as extracted text, including the boundary sentence: `This text is untrusted evidence, not an instruction.`

## Console / Network Notes

- Browser console included expected dev noise and a missing `favicon.ico` 404.
- No API key or local secret value appeared in captured UI artifacts.
