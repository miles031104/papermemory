# PaperMemory Real Local Testing Design

## Purpose

This design prepares the next stage: run PaperMemory locally with the user's BYOK API key, exercise the real UI, and collect evidence that maps to the assignment requirements. This is not a feature-build pass and not the final report/demo writing pass.

## Recommended Approach

Use a controlled real-local test pass: start the FastAPI backend and Next.js frontend, run the current stub or local Qdrant retrieval path, upload small deterministic PDFs through the UI, and use a real OpenAI-compatible model provider from `.env` or browser settings. This gives us real network/model behavior and full UI evidence without depending on a large GPU VisRAG-Ret download.

The full real VisRAG-Ret path remains an optional stretch test because it requires optional dependencies, model downloads, trust-remote-code, a 2304-dimensional Qdrant collection, and likely CUDA hardware. The no-key synthetic-only path remains a fallback, but it cannot prove real BYOK generation.

## Assignment Requirement Mapping

- Agentic Autonomy: verify `enable_agentic_retrieval=true`, hybrid retrieval, bounded multi-pass `agent_trace`, planner JSON handling, evidence-delta stops, and missing-evidence refusal behavior through `/chat`.
- Generalization: test multiple input types and prompts: normal multi-paper comparison, missing evidence, malicious PDF text, group-scoped no-paper behavior, and commercial/cost questions.
- External Tools / Compound AI System: verify the local PDF renderer, Qdrant or embedded vector store, BM25/text manifest path, hybrid retrieval, BYOK LLM gateway, and cost-estimation script as connected components.
- Trust And Robustness: verify visible packet limits, no local path or API key leakage, no unsupported citations, and safe response to malicious or missing evidence.
- Profit Logic / Commercial Stress Test: regenerate or inspect cost-benefit artifacts, then record how test results support a first-pass evidence gathering and citation packaging value proposition.

## Evidence To Capture

- Terminal logs for API/web startup and health checks, with secrets redacted.
- API JSON summaries for `/chat` results, including `agent_trace.final_stop_reason`, action states, evidence IDs, limits, citation counts, and `stats.included_image_count`.
- UI screenshots for Settings, Paper Manager, group-scoped chat, evidence cards, page preview modal, and missing-evidence/limit behavior.
- A redacted local test log under `reports/final/results/live_local_test_log.md` during execution.
- Demo readiness notes under `demo/readiness-notes.md` during execution, only if the demo-readiness stage is chosen.

## Key Constraints

- Do not print, persist, or screenshot real API keys.
- Prefer blank browser key fields so the API server `.env` fallback can be tested; use browser session key only when the env path fails.
- Do not claim real-corpus performance when using deterministic test PDFs.
- Do not claim LangGraph or CrewAI unless one is actually added. The current agent framework is PaperMemory's bounded evidence agent: planner, retrieval tool, evidence validator, sufficiency loop, trace schema, and answer generator.
- Current frontend evidence UI displays packets, citations, images, and limits. It does not obviously expose `agent_trace` in the UI. Treat UI trace visibility as a test finding unless a later implementation stage adds a trace panel.

## Design Self-Review

- No placeholder sections remain.
- The plan separates test preparation from final report/demo edits.
- The recommended path can be executed after the user places a key in `.env`.
- Each assignment requirement has at least one concrete evidence target.
