# Bounded Agentic Retrieval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let PaperMemory ask the LLM for a bounded retrieval plan before page retrieval so answers are grounded in the paper sections most relevant to the user's question.

**Architecture:** Add a narrow planner inside the chat retrieval path. The planner returns JSON-only search queries; the backend validates and clamps that plan, executes only page-search actions, deduplicates evidence by paper/page, and falls back to the existing query rewrite path on errors or empty plans.

**Tech Stack:** FastAPI/Pydantic backend, existing `ChatService`, existing `ModelGateway`, existing VisRAG embeddings and vector store, Next.js frontend request types.

---

### Task 1: Add Planner Tests

**Files:**
- Modify: `apps/api/tests/test_chat_service_agentic.py`

- [ ] Add tests proving `enable_agentic_retrieval=True` calls an LLM planner, embeds multiple planned queries, deduplicates repeated pages, and returns the highest-scoring top-k evidence.
- [ ] Add a fallback test proving invalid planner JSON falls back to current query rewrite behavior.
- [ ] Run `pytest apps/api/tests/test_chat_service_agentic.py -q` and confirm the new tests fail before implementation.

### Task 2: Add Prompt And Request Shape

**Files:**
- Modify: `apps/api/app/services/context_builder.py`
- Modify: `apps/api/app/schemas/chat.py`
- Modify: `apps/web/lib/types.ts`
- Modify: `apps/web/lib/use-chat-session.ts`

- [ ] Add `AGENTIC_RETRIEVAL_SYSTEM_PROMPT`.
- [ ] Add `build_agentic_retrieval_prompt(question, messages)` with recent conversation context and strict JSON output instructions.
- [ ] Add `enable_agentic_retrieval: bool = True` to `ChatRequest`.
- [ ] Add `enable_agentic_retrieval?: boolean` to `ApiChatRequest`.
- [ ] Send `enable_agentic_retrieval: true` from chat requests.

### Task 3: Implement Bounded Planner Execution

**Files:**
- Modify: `apps/api/app/services/chat_service.py`

- [ ] Add constants for max planned queries and query length.
- [ ] Add `_plan_retrieval_queries()` that calls the model with temperature 0, parses JSON, clamps to 1-4 non-empty strings, and returns `None` on any error.
- [ ] Add `_fallback_retrieval_query()` that preserves the current query rewrite / conversational query behavior.
- [ ] Add `_search_retrieval_query()` to embed one query and run existing vector search parameters.
- [ ] Change `_do_retrieval()` to use planned queries first when `enable_agentic_retrieval` is true, dedupe by `(paper_id, page_number)`, sort by score descending, and truncate to `top_k`.
- [ ] Preserve zero-result retry with the bare user question.

### Task 4: Verify

**Commands:**
- `pytest apps/api/tests/test_chat_service_agentic.py -q`
- `pytest apps/api/tests/test_chat_streaming.py apps/api/tests/test_chat_prompt.py apps/api/tests/test_empty_paper_scope.py -q`
- `npm --prefix apps/web run typecheck`
- `git -c safe.directory=D:/codex/papermemory -c core.whitespace=cr-at-eol diff --check`

**Expected:** all tests/typecheck pass; `diff --check` may print existing CRLF warnings only.
