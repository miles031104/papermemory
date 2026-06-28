# UI Upload Worker Summary

## Commands / Tool Used

- Tool: Playwright via temporary `@playwright/test` spec.
- Command: `npx --yes --package @playwright/test playwright test artifacts/real-local-test/2026-06-26/ui-upload-complete.spec.cjs --headed --project=chromium --reporter=line`
- Web: `http://127.0.0.1:3000`
- API: `http://127.0.0.1:8000`

## Upload Results

- Real Test VisRAG Core: ready via api; API status 200; paper status ready; file `D:\codex\llm_paper_assis\papermemory\tmp\real-local-test-corpus\visrag-core.pdf`
- Real Test BM25 Exact: not attempted because an earlier upload did not become ready; file `D:\codex\llm_paper_assis\papermemory\tmp\real-local-test-corpus\bm25-exact.pdf`
- Real Test Agent Robustness: not attempted because an earlier upload did not become ready; file `D:\codex\llm_paper_assis\papermemory\tmp\real-local-test-corpus\agent-robustness.pdf`

## Final /papers

- Initial /papers count: 1 (HTTP 200)
- Final /papers count: 1 (HTTP 200)
- Real Test VisRAG Core: ready

## Console / Network Errors

- Console: error: Failed to load resource: the server responded with a status of 404 (Not Found)

## Artifacts

- Screenshot: `D:\codex\llm_paper_assis\papermemory\artifacts\real-local-test\2026-06-26\ui-upload-complete.png`
