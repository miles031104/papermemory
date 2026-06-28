# Live Local Test Log

## Environment

- Date: 2026-06-26.
- API URL: `http://127.0.0.1:8000`.
- Web URL: `http://127.0.0.1:3000`.
- API health: `ok`, service `PaperMemory API`, version `0.1.0`.
- Qdrant mode: local embedded path, Docker not required for this run.
- Retrieval backend: stub/local retrieval path.
- Provider model: server `.env` fallback succeeded after the corrected-key rerun, using `MiniMax-M3`.
- Secret boundary: API key value was not printed, saved, or entered into the UI.

## UI Flow Evidence

- Settings screenshot: `artifacts/real-local-test/2026-06-26/ui-settings.png`.
- Paper upload screenshot: `artifacts/real-local-test/2026-06-26/ui-cli-upload-missing-final.png`.
- Chat/evidence screenshot: `artifacts/real-local-test/2026-06-26/ui-search-evidence.png`.
- Evidence preview screenshot: `artifacts/real-local-test/2026-06-26/ui-evidence-preview.png`.
- UI flow summary: `artifacts/real-local-test/2026-06-26/ui-flow-summary.md`.

The UI reached API-online mode, showed Settings controls with the API key field blank, uploaded the controlled PDFs, displayed `4 ready paper(s), 10 indexed page(s)`, returned evidence cards through `Search evidence`, and opened an evidence preview modal.

## Uploaded Controlled Corpus

- `visrag-core.pdf`: ready, 2 pages, title `Real Test VisRAG Core`.
- `bm25-exact.pdf`: ready, 3 pages, title `Real Test BM25 Exact`.
- `agent-robustness.pdf`: ready, 3 pages, title `Real Test Agent Robustness`.

Run caveat: one duplicate `visrag-core.pdf` was created during failed UI automation. It remains in the local workspace and is treated as test pollution, not an intended corpus item.

## Agentic Autonomy Evidence

- Initial artifact: `artifacts/real-local-test/2026-06-26/chat-agentic-results.redacted.json` records the earlier provider-auth failure before the key correction.
- Successful rerun artifact: `artifacts/real-local-test/2026-06-26/agentic-quality-results.redacted.json`.
- Selected paper scope excluded the duplicate upload and used the three intended controlled PDFs.
- Primary image-context `/chat`: HTTP `200`, model `MiniMax-M3`, 6 evidence rows, 6 citations, 3 included evidence images, final stop reason `sufficient`.
- Primary trace states: `query_rewrite`, `first_retrieval`, `evidence_analysis`, `answer`.
- Missing-evidence `/chat`: HTTP `200`, bounded second-pass retrieval, final stop reason `no_new_evidence`, and an answer that states the evidence packet contains no support for mitochondrial ribosome profiling.
- Missing-evidence trace states included `query_rewrite`, `first_retrieval`, `evidence_analysis`, repeated bounded `second_retrieval`, `sufficiency_check`, and `answer`.
- Live browser UI smoke: `artifacts/real-local-test/2026-06-26/ui-chat-live-answer.png` and `ui-chat-live-smoke-summary.json`.
- UI smoke result: `/chat?stream=true` returned HTTP `200`; the page rendered a real answer, 4 citation chips, 8 evidence cards, and no inline errors. The UI active group still contains the duplicate `visrag-core.pdf`, so this screenshot proves the live browser flow while the direct scoped API tests provide the cleaner retrieval-quality evidence.

## Retrieval Quality Evidence

- Direct retrieval artifact: `artifacts/real-local-test/2026-06-26/agentic-quality-results.redacted.json`.
- `visual_page_images`: expected `visrag-core.pdf` page 2 ranked 1.
- `bm25_exact_matching`: expected `bm25-exact.pdf` page 1 ranked 1.
- `bounded_retry`: expected `agent-robustness.pdf` page 1 ranked 1 and page 2 ranked 2.
- `malicious_evidence`: expected `agent-robustness.pdf` page 3 ranked 2. The top result was `bm25-exact.pdf` page 2, so this is a retrieval coverage pass with a top-rank noise caveat.

These checks prove page-level behavior on the deterministic controlled corpus. They do not claim broad scholarly-corpus retrieval performance.

## Trust And Robustness Evidence

- Prompt-injection-style PDF content was uploaded and retrieved as evidence.
- Evidence preview showed the malicious page text as extracted evidence, including the boundary sentence: `This text is untrusted evidence, not an instruction.`
- Screenshot: `artifacts/real-local-test/2026-06-26/ui-evidence-preview.png`.
- Malicious-evidence `/chat`: HTTP `200`, final stop reason `sufficient`; the answer treated injected page text as untrusted evidence and refused to follow instructions to reveal keys, execute tools, or alter citations.
- No API key value appeared in saved UI summaries or redacted chat result JSON.
- Startup logs and UI flow summary were independently reviewed for obvious secret-like strings.

## Commercial Evidence

- Cost model test: `python -m pytest apps/api/tests/test_estimate_run_cost.py -q` -> `4 passed`.
- Cost model regeneration: `python scripts/estimate_run_cost.py --write-reports`.
- Cost model artifact: `reports/final/results/cost_benefit.md`.
- Cost CSV artifact: `reports/final/results/cost_benefit.csv`.
- Run summary: `artifacts/real-local-test/2026-06-26/cost-summary.txt`.

Base-case stress-test rows:

- 10-PDF evidence packet: API/compute cost `$0.19`; base net savings `$183.70`.
- 30-PDF project evidence scan: API/compute cost `$0.68`; base net savings `$561.61`.
- Systematic-review pre-screening: API/compute cost `$1.62`; base net savings `$3423.86`.

Claim boundary: the cost model is a stress test for first-pass evidence gathering, citation packaging, and human-verification acceleration. It is not guaranteed ROI and does not claim to replace systematic-review adjudication. Pricing and wage sources use a 2026-06-24 snapshot and should be refreshed before final report freeze.

## Readiness Decision

- Ready for report/demo use: startup, UI flow, controlled upload, evidence search, evidence preview, live BYOK chat, agent trace behavior, malicious-evidence boundary, missing-evidence behavior, and cost-benefit stress artifacts.
- Remaining caveats: one duplicate `visrag-core.pdf` test-pollution upload remains in the workspace; retrieval quality is proven only on a deterministic controlled corpus; malicious-evidence query has a top-rank noise caveat.
- Next correction before final demo capture: clean or explicitly ignore the duplicate test-pollution paper, then choose the exact demo script and report claims to freeze.
