# Chat UX Optimization Design

**Date:** 2026-05-26  
**Status:** Approved  
**Scope:** Streaming responses, Markdown rendering, clickable citation chips

---

## Goals

1. Stream assistant responses token-by-token instead of waiting for the full reply.
2. Render assistant messages with Markdown (headings, bold, code blocks, lists, tables).
3. Make citation chips clickable — clicking scrolls to the matching evidence panel item.

## Non-Goals

- Paper deletion, metadata extraction, or any other feature area.
- Changing `ChatRequest` / `ChatResponse` schema.
- Touching `ResearchSidebar`, `PaperUploadPanel`, or `SettingsView`.

---

## Backend Changes (3 files)

### 1. `apps/api/app/services/model_gateway.py`

Add `generate_stream()` as an async generator alongside the existing `generate()`. The existing method is untouched.

```python
async def generate_stream(
    self,
    messages: list[ChatCompletionMessage],
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    temperature: float = 0.2,
) -> AsyncGenerator[str, None]:
    """Stream delta tokens from the BYOK provider via OpenAI-compatible SSE."""
```

Implementation: uses `httpx.AsyncClient.stream("POST", url, ...)` with `"stream": True` in the payload. Parses `data:` lines, extracts `choices[0].delta.content`, yields each non-empty string. Applies `_strip_reasoning_traces` on the fully assembled text at stream end only if a `<think>` pattern was seen.

### 2. `apps/api/app/services/chat_service.py`

Add `answer_stream()` as an async generator. Retrieval logic is **identical** to `answer()` — same scope check, same `embed_query` + `search_pages` call, same `build_evisrag_prompt`. Only the generation step differs: calls `model_gateway.generate_stream()` and yields delta strings. After the stream ends, yields one final dict with `evidence`, `note`, and `stats`. The existing `answer()` is untouched.

```python
async def answer_stream(self, request: ChatRequest) -> AsyncGenerator[str | dict, None]:
    # ... same retrieval as answer() ...
    async for delta in self.model_gateway.generate_stream(...):
        yield delta
    yield {"evidence": evidence, "note": note, "stats": stats}
```

### 3. `apps/api/app/routers/chat.py`

Add a `?stream=true` query parameter to the existing `POST /chat` endpoint. When present, return a `StreamingResponse` with `media_type="text/event-stream"`. The existing non-streaming path is unchanged.

SSE wire format:
- Token chunks: `data: {"type":"delta","content":"<token>"}\n\n`
- Final frame: `data: {"type":"done","evidence":[...],"note":"...","stats":{...}}\n\n`

No new endpoint is created — `?stream=true` is an additive query parameter.

---

## Frontend Changes (5 files)

### 1. `apps/web/lib/api.ts`

Add `streamChat()` alongside existing methods:

```ts
streamChat(
  request: ApiChatRequest,
  baseUrl: string,
  onDelta: (token: string) => void,
): Promise<ApiChatStreamDone>
```

Uses `fetch` + `response.body.getReader()`. Decodes UTF-8, splits on `\n\n`, parses `data:` lines as JSON. `delta` events call `onDelta`; `done` event resolves the Promise with `{ evidence, note, stats }`. Throws on non-2xx or reader error.

Add type `ApiChatStreamDone` to `lib/types.ts`:
```ts
interface ApiChatStreamDone {
  evidence: ApiPageEvidence[];
  note: string | null;
  stats: Record<string, unknown>;
}
```

### 2. `apps/web/lib/use-chat-session.ts` (new file)

Extracts from `WorkspaceClient` into a hook:

**Owned state:** `question`, `isSubmitting`, `chatError`, `evidence`, `evidenceNote`, `streamingContent` (string built up during streaming).

**Props (inputs):**
- `activeConversation: ResearchConversation | undefined`
- `readyPaperIds: string[]`
- `settings: ModelSettings`
- `installSettings: InstallSettings`
- `paperTitles: Record<string, string>`
- `isWorkspacePersisted: boolean`
- `activeLibrary: ResearchLibrary | undefined`
- `onMessagesChange: (conversationId: string, messages: ChatMessage[]) => void`
- `onPersistMessages: (conversationId: string, messages: ChatMessage[]) => Promise<void>`

**Returns:** `{ messages, question, setQuestion, isSubmitting, error, evidence, evidenceNote, submit, reset, searchEvidence }`

The `messages` in the return value is `activeConversation?.messages ?? []` merged with a synthetic in-progress assistant message when `streamingContent` is non-empty. This avoids any duplication of conversation state.

### 3. `apps/web/components/chat-panel.tsx`

Replace the assistant message body:

```tsx
// Before
<p className="message__body">{message.content}</p>

// After (assistant only)
<ReactMarkdown className="message__body" remarkPlugins={[remarkGfm]}>
  {message.content}
</ReactMarkdown>
```

User messages stay as `<p>` (plain text). Add a pulsing cursor element shown only when `isSubmitting` and the last message is assistant role (streaming in progress).

Citation chips: add `onClick`:
```ts
onClick={() => {
  const el = document.getElementById(`evidence-${citation.paperId}-${citation.page}`);
  el?.scrollIntoView({ behavior: "smooth", block: "center" });
  el?.classList.add("evidence-item--highlight");
  setTimeout(() => el?.classList.remove("evidence-item--highlight"), 1500);
}}
```

### 4. `apps/web/components/evidence-panel.tsx`

Add `id` to each list item:
```tsx
<li
  className="evidence-item"
  id={`evidence-${item.paperId}-${item.page}`}
  key={item.id}
>
```

No other changes.

### 5. `apps/web/components/workspace-client.tsx`

Replace the ~100 lines of chat state and handlers with:
```ts
const {
  messages, question, setQuestion,
  isSubmitting: isChatSubmitting,
  error: chatError,
  evidence, evidenceNote,
  submit: handleSubmitQuestion,
  reset: resetChat,
  searchEvidence: handleSearchEvidence,
} = useChatSession({ activeConversation, readyPaperIds, ... });
```

All other state (libraries, conversations, papers, apiStatus, installSettings, upload) stays in `WorkspaceClient`.

---

## CSS additions (`apps/web/app/globals.css`)

Inside `.message--assistant .message__body`:
- `h1, h2, h3`: font-weight 600, margin-bottom 6px, using existing `--text` color
- `code`: `background: var(--surface-muted)`, `border-radius: var(--radius-sm)`, monospace font, 0.88em
- `pre`: same background, padding 10px, overflow-x auto
- `ul, ol`: left padding 18px, margin-bottom 8px
- `blockquote`: left border 3px solid `--accent-soft`, padding-left 12px, color `--text-muted`
- `table`: border-collapse collapse, `th/td`: border 1px solid `--border`, padding 4px 8px

`.evidence-item--highlight`: `box-shadow: 0 0 0 2px var(--accent)`, `transition: box-shadow 0.2s`

---

## Packages

- `react-markdown` — rendering only, no server calls
- `remark-gfm` — tables, strikethrough, task lists

Add to `apps/web/package.json` dependencies.

---

## What is NOT changed

| Component | Reason |
|-----------|--------|
| `ChatRequest` / `ChatResponse` schema | Streaming is additive via query param |
| Existing `POST /chat` (non-streaming path) | Kept for backward compat |
| `ResearchSidebar`, `PaperUploadPanel`, `SettingsView` | Out of scope |
| `EvidencePanel` display logic | Only `id` attribute added |
| `conversations` state in `WorkspaceClient` | Hook reads/writes via callbacks |

---

## Error handling

- If `streamChat` fails mid-stream (network drop), the partially assembled content is discarded and `chatError` is set.
- If `?stream=true` is not supported by the running backend version (e.g. older deploy), the frontend falls back to `createChat()` (non-streaming) for that request.
- `generate_stream()` propagates `ModelGatewayError` the same way `generate()` does.
