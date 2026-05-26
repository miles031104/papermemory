# Chat UX Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add SSE streaming, Markdown rendering, and clickable citation chips to the PaperMemory chat UI.

**Architecture:** Backend gains a `?stream=true` query parameter on `POST /chat` that returns an SSE `StreamingResponse`; `ModelGateway` gets `generate_stream()` and `ChatService` gets `answer_stream()`. Frontend gains a `useChatSession` hook (extracted from `WorkspaceClient`) that drives a `streamChat()` API call, while `ChatPanel` renders assistant messages with `react-markdown` and makes citation chips scroll to `EvidencePanel` items.

**Tech Stack:** Python 3.11, FastAPI `StreamingResponse`, `httpx` async streaming, Next.js 15 / React 19, `react-markdown` 9, `remark-gfm` 4, TypeScript 5.

---

## File Map

| Action | Path |
|--------|------|
| Modify | `apps/api/app/services/model_gateway.py` |
| Modify | `apps/api/app/services/chat_service.py` |
| Modify | `apps/api/app/routers/chat.py` |
| Create | `apps/api/tests/test_model_gateway_streaming.py` |
| Create | `apps/api/tests/test_chat_streaming.py` |
| Modify | `apps/web/lib/types.ts` |
| Modify | `apps/web/lib/api.ts` |
| Create | `apps/web/lib/use-chat-session.ts` |
| Modify | `apps/web/components/evidence-panel.tsx` |
| Modify | `apps/web/components/chat-panel.tsx` |
| Modify | `apps/web/components/workspace-client.tsx` |
| Modify | `apps/web/app/globals.css` |

---

## Task 1: `generate_stream()` in ModelGateway

**Files:**
- Modify: `apps/api/app/services/model_gateway.py`
- Create: `apps/api/tests/test_model_gateway_streaming.py`

- [ ] **Step 1.1: Write the failing test**

Create `apps/api/tests/test_model_gateway_streaming.py`:

```python
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.core.config import Settings
from app.services.model_gateway import ModelGateway, ModelGatewayError


def _make_settings(base_url: str = "http://fake-provider.local/v1", api_key: str = "test-key") -> Settings:
    return Settings(
        PAPERMEMORY_BYOK_BASE_URL=base_url,
        PAPERMEMORY_BYOK_API_KEY=api_key,
        PAPERMEMORY_BYOK_MODEL="test-model",
        PAPERMEMORY_STORAGE_ROOT="./storage",
        PAPERMEMORY_QDRANT_MODE="local",
        PAPERMEMORY_QDRANT_LOCAL_PATH="./storage/qdrant_local",
    )


class FakeAiterLines:
    """Async iterator that yields a fixed list of SSE lines."""

    def __init__(self, lines: list[str]) -> None:
        self._lines = iter(lines)

    def __aiter__(self):
        return self

    async def __anext__(self) -> str:
        try:
            return next(self._lines)
        except StopIteration:
            raise StopAsyncIteration


class FakeStreamResponse:
    status_code = 200

    def __init__(self, lines: list[str]) -> None:
        self._lines = lines

    def raise_for_status(self) -> None:
        pass

    def aiter_lines(self) -> FakeAiterLines:
        return FakeAiterLines(self._lines)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class FakeHttpxClient:
    def __init__(self, lines: list[str]) -> None:
        self._response = FakeStreamResponse(lines)

    def stream(self, method: str, url: str, **kwargs):
        return self._response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


def _sse(content: str) -> str:
    return f"data: {json.dumps({'choices': [{'delta': {'content': content}}]})}"


@pytest.mark.asyncio
async def test_generate_stream_yields_deltas():
    """generate_stream() yields each delta content token from SSE lines."""
    gateway = ModelGateway(_make_settings())
    lines = [_sse("Hello"), _sse(", "), _sse("world"), "data: [DONE]"]

    with patch("httpx.AsyncClient", return_value=FakeHttpxClient(lines)):
        tokens = []
        async for token in gateway.generate_stream(messages=[{"role": "user", "content": "hi"}]):
            tokens.append(token)

    assert tokens == ["Hello", ", ", "world"]


@pytest.mark.asyncio
async def test_generate_stream_skips_empty_deltas():
    """generate_stream() does not yield empty-string deltas."""
    gateway = ModelGateway(_make_settings())
    lines = [_sse("A"), _sse(""), _sse("B"), "data: [DONE]"]

    with patch("httpx.AsyncClient", return_value=FakeHttpxClient(lines)):
        tokens = []
        async for token in gateway.generate_stream(messages=[{"role": "user", "content": "hi"}]):
            tokens.append(token)

    assert tokens == ["A", "B"]


@pytest.mark.asyncio
async def test_generate_stream_unconfigured_yields_error_message():
    """generate_stream() yields a single error message when not configured."""
    gateway = ModelGateway(Settings(
        PAPERMEMORY_BYOK_BASE_URL=None,
        PAPERMEMORY_BYOK_API_KEY=None,
        PAPERMEMORY_BYOK_MODEL="test-model",
        PAPERMEMORY_STORAGE_ROOT="./storage",
        PAPERMEMORY_QDRANT_MODE="local",
        PAPERMEMORY_QDRANT_LOCAL_PATH="./storage/qdrant_local",
    ))
    tokens = []
    async for token in gateway.generate_stream(messages=[{"role": "user", "content": "hi"}]):
        tokens.append(token)

    assert len(tokens) == 1
    assert "not configured" in tokens[0]
```

- [ ] **Step 1.2: Run the test to verify it fails**

```powershell
cd apps\api
.\.venv\Scripts\Activate.ps1
pytest tests/test_model_gateway_streaming.py -v
```

Expected: `FAILED` — `generate_stream` does not exist yet.

- [ ] **Step 1.3: Add `generate_stream()` to `model_gateway.py`**

At the top of the file, add `import json` after the existing `import re` line. Also add `from collections.abc import AsyncGenerator` after `from typing import Any`.

Then add this method to `ModelGateway` immediately after the existing `generate()` method (after line ~144):

```python
async def generate_stream(
    self,
    messages: list[ChatCompletionMessage],
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    temperature: float = 0.2,
) -> AsyncGenerator[str, None]:
    """Stream delta tokens from the BYOK provider via OpenAI-compatible SSE.

    Yields raw delta strings. Reasoning-trace stripping is deferred to the
    caller (answer_stream) which assembles the full text before sending the
    done frame to the client.
    """
    target_model = model or self.model
    target_base_url = base_url or self.base_url
    target_api_key = api_key or self.api_key

    if not target_base_url or not target_api_key:
        yield (
            "BYOK model gateway is not configured yet. Add a provider base URL and API key "
            "in setup or model settings, then retry this question."
        )
        return

    image_bytes = self.estimate_request_image_bytes(messages)
    if image_bytes > self._REQUEST_IMAGE_WARN_BYTES:
        raise ModelGatewayError(
            f"Request image payload is {image_bytes // (1024 * 1024)} MB, which exceeds the "
            f"{self._REQUEST_IMAGE_WARN_BYTES // (1024 * 1024)} MB safety limit. "
            "Reduce max_evidence_images or switch to text-only mode.",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )

    url = f"{target_base_url.rstrip('/')}/chat/completions"
    payload = self.build_chat_completions_payload(
        messages=messages,
        model=target_model,
        temperature=temperature,
    )
    payload["stream"] = True
    headers = {
        "Authorization": f"Bearer {target_api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        return
                    try:
                        data = json.loads(data_str)
                        delta = data["choices"][0]["delta"].get("content") or ""
                    except (KeyError, IndexError, json.JSONDecodeError):
                        continue
                    if delta:
                        yield delta
    except httpx.HTTPStatusError as exc:
        provider_detail = self._safe_provider_error(exc.response)
        raise ModelGatewayError(
            f"provider returned HTTP {exc.response.status_code}: {provider_detail}",
            status_code=status.HTTP_502_BAD_GATEWAY,
        ) from exc
    except httpx.RequestError as exc:
        raise ModelGatewayError(f"request failed: {exc.__class__.__name__}") from exc
```

**Important:** The `generate_stream` function is an async generator (it uses `yield`), so its return type annotation `-> AsyncGenerator[str, None]` describes the object it returns. Python accepts this annotation on async generator functions.

- [ ] **Step 1.4: Run tests to verify they pass**

```powershell
pytest tests/test_model_gateway_streaming.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 1.5: Commit**

```powershell
git add apps/api/app/services/model_gateway.py apps/api/tests/test_model_gateway_streaming.py
git commit -m "feat(api): add generate_stream() to ModelGateway for SSE token streaming"
```

---

## Task 2: `answer_stream()` in ChatService

**Files:**
- Modify: `apps/api/app/services/chat_service.py`
- Create: `apps/api/tests/test_chat_streaming.py`

- [ ] **Step 2.1: Write the failing test**

Create `apps/api/tests/test_chat_streaming.py`:

```python
import pytest
from collections.abc import AsyncGenerator
from typing import Any

from app.core.config import Settings
from app.schemas.chat import ChatRequest
from app.schemas.retrieval import PageEvidence
from app.services.chat_service import ChatService
from app.services.model_gateway import GenerationResponse, ModelGateway
from app.services.page_image_resolver import PageImageResolver
from app.services.vector_store import VectorStore
from app.services.visrag_service import EmbeddingResult, VisRAGService


class StreamingGateway(ModelGateway):
    """Fake gateway that streams a fixed list of tokens."""

    def __init__(self, tokens: list[str]) -> None:
        self._tokens = tokens

    async def generate_stream(
        self,
        messages,
        model=None,
        base_url=None,
        api_key=None,
        temperature=0.2,
    ) -> AsyncGenerator[str, None]:
        for token in self._tokens:
            yield token

    def build_user_content(self, text, image_paths, enable_image_context=None, max_evidence_images=None):
        from app.services.model_gateway import BuiltUserContent
        return BuiltUserContent(content=text, included_image_count=0)


class StubVisRAG:
    model_name = "stub"

    async def embed_query(self, query: str) -> EmbeddingResult:
        return EmbeddingResult(vector=[1.0, 0.0], model="stub", instruction="stub")


class EmptyVectorStore:
    async def search_pages(self, embedding, top_k, paper_ids=None, score_threshold=None, max_per_paper=None):
        return []


def _make_chat_service(tokens: list[str]) -> ChatService:
    settings = Settings(
        PAPERMEMORY_BYOK_BASE_URL="http://fake.local/v1",
        PAPERMEMORY_BYOK_API_KEY="test",
        PAPERMEMORY_BYOK_MODEL="test-model",
        PAPERMEMORY_STORAGE_ROOT="./storage",
        PAPERMEMORY_QDRANT_MODE="local",
        PAPERMEMORY_QDRANT_LOCAL_PATH="./storage/qdrant_local",
        PAPERMEMORY_QDRANT_VECTOR_SIZE=2,
    )
    return ChatService(
        visrag=StubVisRAG(),
        vector_store=EmptyVectorStore(),
        model_gateway=StreamingGateway(tokens),
        page_image_resolver=None,
    )


@pytest.mark.asyncio
async def test_answer_stream_yields_token_strings_then_done_dict():
    """answer_stream() yields str tokens then a final dict with evidence/note/stats/answer."""
    service = _make_chat_service(["Hello", " world"])
    request = ChatRequest(
        question="What is this?",
        paper_ids=None,
        base_url="http://fake.local/v1",
        api_key="key",
        model="test-model",
    )

    results = []
    async for chunk in service.answer_stream(request):
        results.append(chunk)

    str_chunks = [c for c in results if isinstance(c, str)]
    done_chunks = [c for c in results if isinstance(c, dict)]

    assert str_chunks == ["Hello", " world"]
    assert len(done_chunks) == 1
    done = done_chunks[0]
    assert done["answer"] == "Hello world"
    assert "evidence" in done
    assert "note" in done
    assert "stats" in done


@pytest.mark.asyncio
async def test_answer_stream_done_frame_has_evidence_and_stats():
    """answer_stream() done frame includes evidence list and stats dict."""
    service = _make_chat_service(["Answer"])
    request = ChatRequest(question="Q?", paper_ids=None, base_url="http://fake.local/v1", api_key="k", model="m")

    done = None
    async for chunk in service.answer_stream(request):
        if isinstance(chunk, dict):
            done = chunk

    assert done is not None
    assert isinstance(done["evidence"], list)
    assert isinstance(done["stats"], dict)
    assert "evidence_count" in done["stats"]
```

- [ ] **Step 2.2: Run the test to verify it fails**

```powershell
pytest tests/test_chat_streaming.py -v
```

Expected: `FAILED` — `answer_stream` does not exist yet.

- [ ] **Step 2.3: Add imports to `chat_service.py`**

At the top of `apps/api/app/services/chat_service.py`, add after the existing imports:

```python
from collections.abc import AsyncGenerator
from typing import Any
```

- [ ] **Step 2.4: Add `answer_stream()` to `ChatService`**

Add this method after `answer()` in `apps/api/app/services/chat_service.py` (after the closing of the `answer` method, before `build_evisrag_prompt`):

```python
async def answer_stream(self, request: ChatRequest) -> AsyncGenerator[str | dict[str, Any], None]:
    """Stream chat response as SSE-compatible chunks.

    Yields str tokens during generation, then one final dict with keys
    'answer', 'evidence', 'note', and 'stats' when generation is complete.
    The final 'answer' value has leading reasoning traces stripped.
    """
    paper_scope_count = len(request.paper_ids or [])
    if not request.paper_ids:
        evidence: list[PageEvidence] = []
        retrieval_attempted = False
        prompt = self.build_evisrag_prompt(
            question=request.question,
            evidence=evidence,
            retrieval_attempted=retrieval_attempted,
        )
    else:
        retrieval_attempted = True
        conversational_query = build_conversational_query(
            question=request.question,
            messages=request.messages,
        )
        query_embedding = await self.visrag.embed_query(conversational_query)
        effective_max_per_paper = request.max_per_paper
        if effective_max_per_paper is None and request.paper_ids and len(request.paper_ids) > 1:
            effective_max_per_paper = math.ceil(request.top_k / len(request.paper_ids))
        evidence = await self.vector_store.search_pages(
            embedding=query_embedding.vector,
            top_k=request.top_k,
            paper_ids=request.paper_ids,
            score_threshold=request.score_threshold,
            max_per_paper=effective_max_per_paper,
        )
        prompt = self.build_evisrag_prompt(
            question=request.question,
            evidence=evidence,
            retrieval_attempted=retrieval_attempted,
        )

    user_content = self.model_gateway.build_user_content(
        text=prompt,
        image_paths=self._resolve_authorized_image_paths(evidence),
        enable_image_context=request.enable_image_context,
        max_evidence_images=request.max_evidence_images,
    )
    selected_messages = select_recent_conversation_messages(request.messages)
    messages = [
        {"role": "system", "content": PAPERMEMORY_SYSTEM_PROMPT},
        *[message.model_dump() for message in selected_messages],
        {"role": "user", "content": user_content.content},
    ]

    raw_tokens: list[str] = []
    async for token in self.model_gateway.generate_stream(
        messages=messages,
        model=request.model,
        base_url=request.base_url,
        api_key=request.api_key,
        temperature=request.temperature,
    ):
        raw_tokens.append(token)
        yield token

    full_text = "".join(raw_tokens)
    try:
        from app.services.model_gateway import ModelGateway as _MG
        clean_answer = _MG._strip_reasoning_traces(full_text)
    except Exception:
        clean_answer = full_text

    included_image_count = user_content.included_image_count
    yield {
        "answer": clean_answer,
        "evidence": evidence,
        "note": self._build_generation_note(
            included_image_count=included_image_count,
            evidence_count=len(evidence),
            retrieval_attempted=retrieval_attempted,
        ),
        "stats": {
            "retrieval_attempted": retrieval_attempted,
            "paper_scope_count": paper_scope_count,
            "evidence_count": len(evidence),
            "included_image_count": included_image_count,
        },
    }
```

- [ ] **Step 2.5: Run tests to verify they pass**

```powershell
pytest tests/test_chat_streaming.py -v
```

Expected: 2 tests PASS.

- [ ] **Step 2.6: Commit**

```powershell
git add apps/api/app/services/chat_service.py apps/api/tests/test_chat_streaming.py
git commit -m "feat(api): add answer_stream() to ChatService for SSE streaming"
```

---

## Task 3: SSE Endpoint in `chat.py` Router

**Files:**
- Modify: `apps/api/app/routers/chat.py`

- [ ] **Step 3.1: Write the failing test**

Append to `apps/api/tests/test_chat_streaming.py`:

```python
import json as json_lib
from fastapi.testclient import TestClient
from app.main import create_app
from app.routers import chat as chat_router


class SseStreamingGateway(ModelGateway):
    async def generate_stream(self, messages, model=None, base_url=None, api_key=None, temperature=0.2):
        for token in ["SSE ", "token"]:
            yield token

    def build_user_content(self, text, image_paths, enable_image_context=None, max_evidence_images=None):
        from app.services.model_gateway import BuiltUserContent
        return BuiltUserContent(content=text, included_image_count=0)


def _make_sse_chat_service() -> ChatService:
    settings = Settings(
        PAPERMEMORY_BYOK_BASE_URL="http://fake.local/v1",
        PAPERMEMORY_BYOK_API_KEY="test",
        PAPERMEMORY_BYOK_MODEL="test-model",
        PAPERMEMORY_STORAGE_ROOT="./storage",
        PAPERMEMORY_QDRANT_MODE="local",
        PAPERMEMORY_QDRANT_LOCAL_PATH="./storage/qdrant_local",
        PAPERMEMORY_QDRANT_VECTOR_SIZE=2,
    )
    return ChatService(
        visrag=StubVisRAG(),
        vector_store=EmptyVectorStore(),
        model_gateway=SseStreamingGateway(settings),
        page_image_resolver=None,
    )


def test_chat_stream_endpoint_returns_sse_with_delta_and_done_frames():
    """POST /chat?stream=true returns SSE content with delta frames and a done frame."""
    app = create_app()
    app.dependency_overrides[chat_router.get_chat_service] = _make_sse_chat_service

    client = TestClient(app, raise_server_exceptions=True)
    response = client.post(
        "/chat?stream=true",
        json={"question": "Test streaming?", "paper_ids": None},
    )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    body = response.text
    lines = [line for line in body.split("\n") if line.startswith("data:")]
    frames = [json_lib.loads(line[5:].strip()) for line in lines]

    delta_frames = [f for f in frames if f.get("type") == "delta"]
    done_frames = [f for f in frames if f.get("type") == "done"]

    assert len(delta_frames) >= 1
    assert len(done_frames) == 1
    assert "answer" in done_frames[0]
    assert "evidence" in done_frames[0]
```

```powershell
pytest tests/test_chat_streaming.py::test_chat_stream_endpoint_returns_sse_with_delta_and_done_frames -v
```

Expected: `FAILED` — streaming endpoint does not exist yet.

- [ ] **Step 3.2: Update `chat.py` to add streaming branch**

Replace the entire content of `apps/api/app/routers/chat.py` with:

```python
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.core.config import Settings, get_settings
from app.core.paths import StoragePaths
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.services.model_gateway import ModelGateway
from app.services.page_image_resolver import PageImageResolver
from app.services.vector_store import VectorStore
from app.services.visrag_service import VisRAGService, VisRAGUnavailable

router = APIRouter()


def get_chat_service(settings: Settings = Depends(get_settings)) -> ChatService:
    return ChatService(
        visrag=VisRAGService(settings=settings),
        vector_store=VectorStore(settings=settings),
        model_gateway=ModelGateway(settings=settings),
        page_image_resolver=PageImageResolver(paths=StoragePaths(settings)),
    )


async def _sse_stream(service: ChatService, request: ChatRequest):
    """Async generator that yields SSE-formatted byte strings."""
    async for chunk in service.answer_stream(request):
        if isinstance(chunk, str):
            payload = json.dumps({"type": "delta", "content": chunk})
        else:
            payload = json.dumps({"type": "done", **chunk}, default=str)
        yield f"data: {payload}\n\n"


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    stream: Annotated[bool, Query()] = False,
    service: ChatService = Depends(get_chat_service),
) -> ChatResponse | StreamingResponse:
    try:
        if stream:
            return StreamingResponse(
                _sse_stream(service, request),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
        return await service.answer(request)
    except VisRAGUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
```

- [ ] **Step 3.3: Run all streaming tests**

```powershell
pytest tests/test_model_gateway_streaming.py tests/test_chat_streaming.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 3.4: Run the full test suite to check for regressions**

```powershell
pytest --tb=short -q
```

Expected: all existing tests still PASS.

- [ ] **Step 3.5: Commit**

```powershell
git add apps/api/app/routers/chat.py apps/api/tests/test_chat_streaming.py
git commit -m "feat(api): add ?stream=true SSE endpoint to POST /chat"
```

---

## Task 4: Frontend Types, Package Install, and `streamChat()`

**Files:**
- Modify: `apps/web/lib/types.ts`
- Modify: `apps/web/lib/api.ts`
- Modify: `apps/web/package.json` (via npm install)

- [ ] **Step 4.1: Install `react-markdown` and `remark-gfm`**

```powershell
cd apps\web
npm install react-markdown remark-gfm
```

Expected output: packages added to `node_modules` and `package.json` updated.

- [ ] **Step 4.2: Add `ApiChatStreamDone` to `types.ts`**

Open `apps/web/lib/types.ts`. Add the following at the end of the file (after the last `}` of `ApiWorkspaceResponse`):

```typescript
export interface ApiChatStreamDone {
  answer: string;
  evidence: ApiPageEvidence[];
  note: string | null;
  stats: Record<string, unknown>;
}
```

- [ ] **Step 4.3: Add `streamChat()` to `api.ts`**

Open `apps/web/lib/api.ts`. At the top, add the import:

```typescript
import type {
  ApiChatRequest,
  ApiChatResponse,
  ApiChatStreamDone,
  // ... rest of existing imports unchanged
```

Then add `streamChat` as a new method inside the `paperMemoryApi` object, after the existing `searchEvidence` method:

```typescript
  async streamChat(
    request: ApiChatRequest,
    baseUrl: string,
    onDelta: (token: string) => void,
  ): Promise<ApiChatStreamDone> {
    const apiBaseUrl = baseUrl?.trim() || defaultApiBaseUrl;
    const response = await fetch(
      `${apiBaseUrl.replace(/\/$/, "")}/chat?stream=true`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      },
    );

    if (!response.ok) {
      const detail = await response.text();
      throw new Error(`PaperMemory API ${response.status}: ${detail || response.statusText}`);
    }

    if (!response.body) {
      throw new Error("Streaming response body is unavailable.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let result: ApiChatStreamDone | null = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? "";

      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith("data:")) continue;
        const dataStr = line.slice(5).trim();
        try {
          const parsed = JSON.parse(dataStr) as {
            type: string;
            content?: string;
            answer?: string;
            evidence?: ApiPageEvidence[];
            note?: string | null;
            stats?: Record<string, unknown>;
          };
          if (parsed.type === "delta" && parsed.content) {
            onDelta(parsed.content);
          } else if (parsed.type === "done") {
            result = {
              answer: parsed.answer ?? "",
              evidence: parsed.evidence ?? [],
              note: parsed.note ?? null,
              stats: parsed.stats ?? {},
            };
          }
        } catch {
          // skip malformed SSE lines
        }
      }
    }

    if (!result) {
      throw new Error("Stream ended without a done frame.");
    }
    return result;
  },
```

- [ ] **Step 4.4: Run typecheck**

```powershell
npm run typecheck
```

Expected: no TypeScript errors. If `.next/types` errors appear, run `npm run build` first, then rerun typecheck.

- [ ] **Step 4.5: Commit**

```powershell
cd apps\web
git add package.json package-lock.json lib/types.ts lib/api.ts
git commit -m "feat(web): add ApiChatStreamDone type and streamChat() API method"
```

---

## Task 5: `useChatSession` Hook

**Files:**
- Create: `apps/web/lib/use-chat-session.ts`

- [ ] **Step 5.1: Create `apps/web/lib/use-chat-session.ts`**

```typescript
"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { paperMemoryApi } from "@/lib/api";
import type {
  ApiChatRequest,
  ApiPageEvidence,
  ChatMessage,
  EvidenceItem,
  InstallSettings,
  ModelSettings,
  ResearchConversation,
  ResearchLibrary,
} from "@/lib/types";

interface UseChatSessionOptions {
  activeConversation: ResearchConversation | undefined;
  activeLibrary: ResearchLibrary | undefined;
  readyPaperIds: string[];
  settings: ModelSettings;
  installSettings: InstallSettings;
  paperTitles: Record<string, string>;
  isWorkspacePersisted: boolean;
  onMessagesChange: (conversationId: string, messages: ChatMessage[]) => void;
  onPersistMessages: (conversationId: string, messages: ChatMessage[]) => Promise<void>;
}

interface UseChatSessionReturn {
  messages: ChatMessage[];
  question: string;
  setQuestion: (q: string) => void;
  isSubmitting: boolean;
  error: string | null;
  evidence: Array<EvidenceItem | ApiPageEvidence>;
  evidenceNote: string | null;
  submit: () => void;
  reset: () => void;
  searchEvidence: () => void;
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Unknown error.";
}

export function useChatSession({
  activeConversation,
  activeLibrary,
  readyPaperIds,
  settings,
  installSettings,
  paperTitles,
  isWorkspacePersisted,
  onMessagesChange,
  onPersistMessages,
}: UseChatSessionOptions): UseChatSessionReturn {
  const [question, setQuestion] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [evidence, setEvidence] = useState<Array<EvidenceItem | ApiPageEvidence>>([]);
  const [evidenceNote, setEvidenceNote] = useState<string | null>(null);
  const [streamingContent, setStreamingContent] = useState("");

  // Auto-reset when the active conversation or library changes.
  useEffect(() => {
    setEvidence([]);
    setEvidenceNote(
      activeLibrary
        ? `No evidence loaded for ${activeLibrary.name} yet. Search inside this database to populate page evidence.`
        : null,
    );
    setStreamingContent("");
    setQuestion("");
    setError(null);
  }, [activeConversation?.id, activeLibrary?.id]);

  // Merge stored messages with any in-progress streaming content.
  const messages = useMemo<ChatMessage[]>(() => {
    const base = activeConversation?.messages ?? [];
    if (!streamingContent) return base;
    return [
      ...base,
      {
        id: "streaming-assistant",
        role: "assistant" as const,
        content: streamingContent,
        citations: [],
      },
    ];
  }, [activeConversation?.messages, streamingContent]);

  const doSearchEvidence = useCallback(
    async (query: string): Promise<Array<ApiPageEvidence>> => {
      const response = await paperMemoryApi.searchEvidence(
        query,
        readyPaperIds,
        settings.retrievalTopK,
        installSettings.apiBaseUrl,
      );
      setEvidence(response.evidence);
      setEvidenceNote(response.note);
      return response.evidence;
    },
    [readyPaperIds, settings.retrievalTopK, installSettings.apiBaseUrl],
  );

  const submit = useCallback(async () => {
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || isSubmitting) return;

    const conversationId = activeConversation?.id;
    if (!conversationId) {
      setError("Create a conversation inside the active database before asking questions.");
      return;
    }

    const currentMessages = activeConversation?.messages ?? [];
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: trimmedQuestion,
      citations: [],
    };
    const nextUserMessages = [...currentMessages, userMessage];
    onMessagesChange(conversationId, nextUserMessages);
    setQuestion("");
    setError(null);
    setIsSubmitting(true);
    setStreamingContent("");

    const priorMessages = currentMessages.map((m) => ({
      role: m.role as "user" | "assistant",
      content: m.content,
    }));

    // Pre-search to populate the evidence panel while the LLM streams.
    if (readyPaperIds.length > 0) {
      try {
        await doSearchEvidence(trimmedQuestion);
      } catch {
        setEvidence([]);
        setEvidenceNote("Retrieval failed before generation; answer will not be paper-grounded.");
      }
    } else {
      setEvidence([]);
      setEvidenceNote("Conversation mode: no ready papers in the active database.");
    }

    try {
      const chatRequest: ApiChatRequest = {
        question: trimmedQuestion,
        paper_ids: readyPaperIds.length > 0 ? readyPaperIds : undefined,
        top_k: settings.retrievalTopK,
        messages: priorMessages,
        provider: settings.provider,
        base_url: settings.baseUrl.trim() || undefined,
        model: settings.model.trim() || undefined,
        api_key: settings.apiKey || undefined,
        temperature: settings.temperature,
        enable_image_context: settings.useMultimodalContext,
        max_evidence_images: settings.maxEvidenceImages,
      };

      const done = await paperMemoryApi.streamChat(
        chatRequest,
        installSettings.apiBaseUrl,
        (token) => {
          setStreamingContent((prev) => prev + token);
        },
      );

      setEvidence(done.evidence);
      setEvidenceNote(done.note);

      const citations = (done.evidence as ApiPageEvidence[]).slice(0, 4).map((item) => ({
        paperId: item.paper_id,
        label: paperTitles[item.paper_id] ?? item.paper_id,
        page: item.page_number,
      }));

      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: done.answer,
        citations,
      };

      const nextMessages = [...nextUserMessages, assistantMessage];
      onMessagesChange(conversationId, nextMessages);
      if (isWorkspacePersisted) {
        await onPersistMessages(conversationId, nextMessages);
      }
    } catch (err) {
      setError(getErrorMessage(err));
      setEvidence([]);
      setEvidenceNote("Chat failed before PaperMemory could return an answer.");
    } finally {
      setStreamingContent("");
      setIsSubmitting(false);
    }
  }, [
    question,
    isSubmitting,
    activeConversation,
    readyPaperIds,
    settings,
    installSettings.apiBaseUrl,
    paperTitles,
    isWorkspacePersisted,
    onMessagesChange,
    onPersistMessages,
    doSearchEvidence,
  ]);

  const reset = useCallback(() => {
    if (activeConversation) {
      onMessagesChange(activeConversation.id, []);
      if (isWorkspacePersisted) {
        void onPersistMessages(activeConversation.id, []);
      }
    }
    setEvidence([]);
    setEvidenceNote(
      activeLibrary
        ? `No evidence loaded for ${activeLibrary.name} yet. Search inside this database to populate page evidence.`
        : null,
    );
    setError(null);
    setQuestion("");
    setStreamingContent("");
  }, [activeConversation, activeLibrary, isWorkspacePersisted, onMessagesChange, onPersistMessages]);

  const searchEvidence = useCallback(async () => {
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion) return;

    if (readyPaperIds.length === 0) {
      const msg = `No ready papers in ${activeLibrary?.name ?? "the active database"}. Upload and index a PDF before searching.`;
      setEvidence([]);
      setEvidenceNote(msg);
      setError(msg);
      return;
    }

    setError(null);
    try {
      await doSearchEvidence(trimmedQuestion);
    } catch (err) {
      setEvidence([]);
      setEvidenceNote(getErrorMessage(err));
      setError(getErrorMessage(err));
    }
  }, [question, readyPaperIds, activeLibrary, doSearchEvidence]);

  return {
    messages,
    question,
    setQuestion,
    isSubmitting,
    error,
    evidence,
    evidenceNote,
    submit,
    reset,
    searchEvidence,
  };
}
```

- [ ] **Step 5.2: Run typecheck**

```powershell
cd apps\web
npm run typecheck
```

Expected: no TypeScript errors.

- [ ] **Step 5.3: Commit**

```powershell
git add lib/use-chat-session.ts
git commit -m "feat(web): add useChatSession hook with streaming, evidence, and error state"
```

---

## Task 6: Evidence Panel ID Attributes and Highlight CSS

**Files:**
- Modify: `apps/web/components/evidence-panel.tsx`
- Modify: `apps/web/app/globals.css`

- [ ] **Step 6.1: Add `id` attribute to each evidence list item**

Open `apps/web/components/evidence-panel.tsx`. Find the `<li>` inside the evidence list:

```tsx
          <li className="evidence-item" key={item.id}>
```

Replace it with:

```tsx
          <li
            className="evidence-item"
            id={`evidence-${item.paperId}-${item.page}`}
            key={item.id}
          >
```

No other changes to this file.

- [ ] **Step 6.2: Add highlight CSS class to `globals.css`**

Open `apps/web/app/globals.css`. Find the `.confidence-meter` block (search for `.confidence-meter`). Add the following immediately after the closing `}` of whatever block is last before `.confidence-meter` (or at the very end of the file if that is easier to locate):

```css
.evidence-item--highlight {
  box-shadow: 0 0 0 2px var(--accent);
  border-radius: var(--radius);
  transition: box-shadow 0.2s;
}
```

- [ ] **Step 6.3: Run typecheck**

```powershell
cd apps\web
npm run typecheck
```

Expected: no errors.

- [ ] **Step 6.4: Commit**

```powershell
git add components/evidence-panel.tsx app/globals.css
git commit -m "feat(web): add evidence item IDs and highlight CSS for citation scrolling"
```

---

## Task 7: Markdown Rendering, Streaming Cursor, and Clickable Citation Chips

**Files:**
- Modify: `apps/web/components/chat-panel.tsx`
- Modify: `apps/web/app/globals.css`

- [ ] **Step 7.1: Update `chat-panel.tsx`**

Replace the entire content of `apps/web/components/chat-panel.tsx` with:

```tsx
"use client";

import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import type { ChatMessage } from "@/lib/types";

interface ChatPanelProps {
  messages: ChatMessage[];
  question: string;
  isSubmitting: boolean;
  title: string;
  contextLabel: string;
  libraryDescription: string;
  error?: string | null;
  onQuestionChange: (question: string) => void;
  onSubmit: () => void;
  onReset: () => void;
  onSearchEvidence: () => void;
}

function scrollToEvidence(paperId: string, page: number) {
  const el = document.getElementById(`evidence-${paperId}-${page}`);
  if (!el) return;
  el.scrollIntoView({ behavior: "smooth", block: "center" });
  el.classList.add("evidence-item--highlight");
  setTimeout(() => el.classList.remove("evidence-item--highlight"), 1500);
}

export function ChatPanel({
  messages,
  question,
  isSubmitting,
  title,
  contextLabel,
  libraryDescription,
  error,
  onQuestionChange,
  onSubmit,
  onReset,
  onSearchEvidence,
}: ChatPanelProps) {
  const canSubmit = question.trim().length > 0 && !isSubmitting;
  const listRef = useRef<HTMLOListElement>(null);

  useEffect(() => {
    const list = listRef.current;
    if (list) {
      list.scrollTop = list.scrollHeight;
    }
  }, [messages]);

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      event.preventDefault();
      if (canSubmit) onSubmit();
    }
  };

  const lastIsStreaming =
    isSubmitting &&
    messages.length > 0 &&
    messages[messages.length - 1]?.role === "assistant";

  return (
    <section className="panel chat-panel" aria-labelledby="chat-title">
      <div className="panel__header">
        <div>
          <p className="eyebrow">{contextLabel}</p>
          <h2 id="chat-title">{title}</h2>
          <p>{libraryDescription}</p>
        </div>
        <button className="button button--subtle" type="button" onClick={onReset}>
          Clear
        </button>
      </div>

      <div className="panel__body">
        <ol className="message-list" aria-label="Chat transcript" ref={listRef}>
          {messages.map((message, index) => {
            const isStreamingMessage =
              isSubmitting && index === messages.length - 1 && message.role === "assistant";
            return (
              <li className={`message message--${message.role}`} key={message.id}>
                {message.role === "assistant" ? (
                  <span className="message__avatar" aria-hidden="true">PM</span>
                ) : null}
                <div className="message__bubble">
                  {message.role === "assistant" ? (
                    <div className="message__body message__body--markdown">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {message.content}
                      </ReactMarkdown>
                      {isStreamingMessage ? (
                        <span className="streaming-cursor" aria-hidden="true" />
                      ) : null}
                    </div>
                  ) : (
                    <p className="message__body">{message.content}</p>
                  )}
                  {message.citations.length > 0 ? (
                    <div className="citation-chips" aria-label="Cited pages">
                      {message.citations.map((citation) => (
                        <button
                          type="button"
                          className="citation-chip"
                          key={`${citation.paperId}-${citation.page}`}
                          onClick={() => scrollToEvidence(citation.paperId, citation.page)}
                        >
                          {citation.label} p.{citation.page}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              </li>
            );
          })}
        </ol>
      </div>

      <form
        className="composer"
        aria-label="Ask a question"
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit();
        }}
      >
        {error ? (
          <p className="inline-alert inline-alert--error" role="alert">
            {error}
          </p>
        ) : null}
        <div className="field">
          <label htmlFor="question">
            <span>Question</span>
            <span className="shortcut-hint">⌘↵ to send</span>
          </label>
          <textarea
            id="question"
            name="question"
            rows={3}
            value={question}
            onChange={(event) => onQuestionChange(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about the active papers…"
          />
        </div>
        <div className="button-row">
          <button className="button button--primary" type="submit" disabled={!canSubmit}>
            {isSubmitting ? "Thinking…" : "Ask"}
          </button>
          <button
            className="button"
            type="button"
            disabled={!canSubmit}
            onClick={onSearchEvidence}
          >
            Search evidence
          </button>
        </div>
      </form>
    </section>
  );
}
```

- [ ] **Step 7.2: Add Markdown and streaming cursor CSS to `globals.css`**

Open `apps/web/app/globals.css`. Add the following at the end of the file:

```css
/* Markdown content inside assistant messages */
.message__body--markdown {
  color: var(--text);
}

.message__body--markdown p {
  margin: 0 0 6px;
}

.message__body--markdown p:last-child {
  margin-bottom: 0;
}

.message__body--markdown h1,
.message__body--markdown h2,
.message__body--markdown h3 {
  margin: 10px 0 4px;
  font-weight: 600;
  color: var(--text);
}

.message__body--markdown code {
  background: var(--surface-muted);
  border-radius: var(--radius-sm);
  font-family: ui-monospace, "Cascadia Code", "Fira Code", monospace;
  font-size: 0.88em;
  padding: 1px 4px;
}

.message__body--markdown pre {
  background: var(--surface-muted);
  border-radius: var(--radius);
  padding: 10px 12px;
  overflow-x: auto;
  margin: 6px 0;
}

.message__body--markdown pre code {
  background: none;
  padding: 0;
  font-size: 0.86em;
}

.message__body--markdown ul,
.message__body--markdown ol {
  padding-left: 18px;
  margin: 0 0 6px;
}

.message__body--markdown li {
  margin-bottom: 2px;
}

.message__body--markdown blockquote {
  border-left: 3px solid var(--accent-soft);
  padding-left: 12px;
  margin: 6px 0;
  color: var(--text-muted);
}

.message__body--markdown table {
  border-collapse: collapse;
  width: 100%;
  margin: 6px 0;
  font-size: 0.9em;
}

.message__body--markdown th,
.message__body--markdown td {
  border: 1px solid var(--border);
  padding: 4px 8px;
  text-align: left;
}

.message__body--markdown th {
  background: var(--surface-muted);
  font-weight: 600;
}

/* Citation chips are now buttons */
.citation-chip {
  display: inline-flex;
  align-items: center;
  border: none;
  background: var(--accent-soft);
  color: var(--accent-strong);
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  transition: background-color var(--transition-fast);
}

.citation-chip:hover {
  background: var(--surface-strong);
}

/* Blinking cursor shown during SSE streaming */
.streaming-cursor {
  display: inline-block;
  width: 2px;
  height: 1em;
  background: var(--accent);
  margin-left: 2px;
  vertical-align: text-bottom;
  animation: blink 0.9s step-end infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
```

- [ ] **Step 7.3: Run typecheck**

```powershell
cd apps\web
npm run typecheck
```

Expected: no errors.

- [ ] **Step 7.4: Commit**

```powershell
git add components/chat-panel.tsx app/globals.css
git commit -m "feat(web): add Markdown rendering, streaming cursor, and clickable citation chips"
```

---

## Task 8: Wire `useChatSession` into `WorkspaceClient`

**Files:**
- Modify: `apps/web/components/workspace-client.tsx`

- [ ] **Step 8.1: Update imports at the top of `workspace-client.tsx`**

Replace the existing import block at the top with the following (the key additions are `useChatSession` and removing the mock-evidence/mock-model-settings that are no longer needed):

```typescript
"use client";

import { useEffect, useMemo, useState } from "react";

import { ChatPanel } from "@/components/chat-panel";
import { EvidencePanel } from "@/components/evidence-panel";
import { PaperLibrary } from "@/components/paper-library";
import { PaperUploadPanel } from "@/components/paper-upload-panel";
import { ResearchSidebar, type WorkspaceView } from "@/components/research-sidebar";
import { SettingsView } from "@/components/settings-view";
import { defaultApiBaseUrl, paperMemoryApi } from "@/lib/api";
import { useChatSession } from "@/lib/use-chat-session";
import {
  mockConversations,
  mockModelSettings,
  mockPaperGroups,
  mockPapers,
  mockResearchLibraries
} from "@/lib/mock-data";
import type {
  ApiPaperMetadata,
  ApiPageEvidence,
  ApiPaperGroup,
  ApiResearchConversation,
  ApiResearchLibrary,
  ApiWorkspaceMessage,
  ChatMessage,
  Citation,
  InstallSettings,
  ModelSettings,
  PaperGroup,
  PaperStatus,
  PaperSummary,
  ResearchConversation,
  ResearchLibrary
} from "@/lib/types";
```

Note: `mockEvidence` is removed from the import (evidence is now owned by the hook). `ApiChatResponse`, `EvidenceItem` are also removed from imports since they are no longer referenced directly in this file.

- [ ] **Step 8.2: Remove standalone chat state declarations**

In `WorkspaceClient`, find the block of `useState` calls. Remove these five lines:

```typescript
  const [evidence, setEvidence] = useState<Array<EvidenceItem | ApiPageEvidence>>(mockEvidence);
  const [evidenceNote, setEvidenceNote] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [isChatSubmitting, setIsChatSubmitting] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
```

- [ ] **Step 8.3: Add the `useChatSession` hook call**

After the `readyPaperIds` useMemo (which computes ready paper IDs from `activeLibraryPapers`), add:

```typescript
  const {
    messages,
    question,
    setQuestion,
    isSubmitting: isChatSubmitting,
    error: chatError,
    evidence,
    evidenceNote,
    submit: handleSubmitQuestion,
    reset: resetChat,
    searchEvidence: handleSearchEvidence,
  } = useChatSession({
    activeConversation,
    activeLibrary,
    readyPaperIds,
    settings,
    installSettings,
    paperTitles,
    isWorkspacePersisted,
    onMessagesChange: setConversationMessages,
    onPersistMessages: persistConversationMessages,
  });
```

- [ ] **Step 8.4: Remove the standalone `searchEvidence`, `handleSearchEvidence`, `handleSubmitQuestion`, and `resetChat` functions**

Delete the following functions from `WorkspaceClient` (they are now provided by the hook):
- `const searchEvidence = async (query: string) => { ... }`
- `const handleSearchEvidence = async () => { ... }`
- `const handleSubmitQuestion = async () => { ... }`
- `const resetChat = () => { ... }`

- [ ] **Step 8.5: Remove `setEvidence` and `setEvidenceNote` calls from `loadWorkspace`**

In the `loadWorkspace` function, find and delete these two lines in the try-block:

```typescript
      setEvidence([]);
      setEvidenceNote(scopedEvidenceNote(nextActiveLibrary?.name));
```

And delete these two lines in the catch-block:

```typescript
      setEvidence(mockEvidence);
      setEvidenceNote("Using mock evidence until the local API is reachable.");
```

- [ ] **Step 8.6: Remove `setEvidence` and `setEvidenceNote` from library/conversation handlers**

Find and delete the following lines from these handlers (they are now handled by the hook's useEffect):

In `handleSelectLibrary`:
```typescript
    setEvidence([]);
    setEvidenceNote(scopedEvidenceNote(library?.name));
```

In `handleSelectConversation`:
```typescript
    setEvidence([]);
    setEvidenceNote(scopedEvidenceNote(activeLibrary?.name));
```

In `handleCreateConversation`:
```typescript
    setEvidence([]);
    setEvidenceNote(scopedEvidenceNote(activeLibrary?.name));
```

In `createLibrary` (two places — in the catch block and after success):
```typescript
    setEvidence([]);
    setEvidenceNote(scopedEvidenceNote(library.name));
```

In `createConversation`:
```typescript
    setEvidence([]);
    setEvidenceNote(scopedEvidenceNote(activeLibrary?.name));
```

In `selectLibrary`:
```typescript
    setEvidence([]);
    setEvidenceNote(scopedEvidenceNote(library?.name));
```

- [ ] **Step 8.7: Remove the `scopedEvidenceNote` helper function**

Find and delete:

```typescript
function scopedEvidenceNote(libraryName?: string) {
  return libraryName
    ? `No evidence loaded for ${libraryName} yet. Search inside this database to populate page evidence.`
    : "No evidence loaded for this conversation yet. Search inside the active database to populate page evidence.";
}
```

- [ ] **Step 8.8: Remove the `messages` local variable**

Find and delete:

```typescript
  const messages = activeConversation?.messages ?? [];
```

The hook now provides `messages` directly.

- [ ] **Step 8.9: Run typecheck**

```powershell
cd apps\web
npm run typecheck
```

If there are any remaining references to removed state (e.g., `setEvidence`, `setChatError`, `setQuestion`, etc.) that TypeScript catches, remove those calls. They should all have been removed in the steps above.

Expected: no TypeScript errors.

- [ ] **Step 8.10: Run frontend build to verify production build succeeds**

```powershell
npm run build
```

Expected: Build completes without errors.

- [ ] **Step 8.11: Commit**

```powershell
cd apps\web
git add components/workspace-client.tsx
git commit -m "refactor(web): extract chat state into useChatSession hook, wire streaming"
```

---

## Task 9: Final Verification

- [ ] **Step 9.1: Run full backend test suite**

```powershell
cd apps\api
.\.venv\Scripts\Activate.ps1
pytest --tb=short -q
```

Expected: all tests PASS, no failures.

- [ ] **Step 9.2: Run frontend typecheck one final time**

```powershell
cd apps\web
npm run typecheck
```

Expected: 0 errors.

- [ ] **Step 9.3: Start the app and verify end-to-end**

Terminal 1 (API):
```powershell
cd apps\api
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

Terminal 2 (Web):
```powershell
cd apps\web
npm run dev
```

Open `http://localhost:3000`. Verify:
1. A question with a configured BYOK provider shows the answer streaming in token by token.
2. The streaming cursor blinks while the answer arrives.
3. After streaming completes, the answer renders with Markdown formatting (bold, code, etc.).
4. Citation chips (if evidence was retrieved) are clickable and scroll to the matching evidence panel card, which briefly highlights with an accent border.
5. User messages remain as plain text.
6. Switching libraries/conversations clears the chat and evidence panel.

- [ ] **Step 9.4: Final commit tag**

```powershell
git tag v0.2.0-chat-ux
```

---

## Self-Review Notes

**Spec coverage:**
- ✅ `generate_stream()` — Task 1
- ✅ `answer_stream()` — Task 2  
- ✅ `?stream=true` SSE endpoint — Task 3
- ✅ `streamChat()` + `ApiChatStreamDone` type — Task 4
- ✅ `useChatSession` hook — Task 5
- ✅ Evidence panel `id` attributes + highlight CSS — Task 6
- ✅ Markdown rendering + streaming cursor + citation chip `onClick` — Task 7
- ✅ CSS Markdown + cursor + chip button styles — Task 7
- ✅ `WorkspaceClient` integration — Task 8
- ✅ `react-markdown` + `remark-gfm` packages — Task 4

**Type consistency check:**
- `ApiChatStreamDone.evidence` is `ApiPageEvidence[]` — matches what `answer_stream()` yields in the done dict
- `ApiChatStreamDone.answer` — matches the `"answer"` key in `_sse_stream()`
- `useChatSession` returns `submit`, `reset`, `searchEvidence` — all wired in Task 8 as `handleSubmitQuestion`, `resetChat`, `handleSearchEvidence`
- Citation chip `onClick` calls `scrollToEvidence(citation.paperId, citation.page)` which builds `evidence-${paperId}-${page}` — matches the `id` set in Task 6

**Non-streaming path:** `POST /chat` without `?stream=true` is unchanged — confirmed in Task 3, the existing `service.answer(request)` path is preserved.
