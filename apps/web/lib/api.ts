import type {
  ApiChatRequest,
  ApiChatResponse,
  ApiChatStreamDone,
  ApiChatStreamError,
  ApiHealthResponse,
  ApiPageEvidence,
  ApiPaperListResponse,
  ApiPaperUploadResponse,
  ApiRetrievalResponse,
  ApiResearchConversation,
  ApiResearchLibrary,
  ApiPaperGroup,
  ApiWorkspaceMessage,
  ApiWorkspaceResponse,
} from "@/lib/types";

export const defaultApiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: BodyInit | Record<string, unknown>;
  baseUrl?: string;
};

async function requestJson<TResponse>(
  path: string,
  { body, headers, baseUrl, ...options }: RequestOptions = {}
): Promise<TResponse> {
  const isFormBody = body instanceof FormData;
  const apiBaseUrl = baseUrl?.trim() || defaultApiBaseUrl;
  const response = await fetch(`${apiBaseUrl.replace(/\/$/, "")}${path}`, {
    ...options,
    headers: {
      ...(isFormBody ? {} : { "Content-Type": "application/json" }),
      ...headers
    },
    body: isFormBody || typeof body === "string" ? body : JSON.stringify(body)
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`PaperMemory API ${response.status}: ${detail || response.statusText}`);
  }

  return response.json() as Promise<TResponse>;
}

async function requestVoid(
  path: string,
  { body, headers, baseUrl, ...options }: RequestOptions = {}
): Promise<void> {
  const isFormBody = body instanceof FormData;
  const apiBaseUrl = baseUrl?.trim() || defaultApiBaseUrl;
  const response = await fetch(`${apiBaseUrl.replace(/\/$/, "")}${path}`, {
    ...options,
    headers: {
      ...(isFormBody ? {} : { "Content-Type": "application/json" }),
      ...headers
    },
    body: isFormBody || typeof body === "string" ? body : body === undefined ? undefined : JSON.stringify(body)
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`PaperMemory API ${response.status}: ${detail || response.statusText}`);
  }
}

export const paperMemoryApi = {
  health(baseUrl?: string) {
    return requestJson<ApiHealthResponse>("/health", { baseUrl });
  },

  listPapers(baseUrl?: string) {
    return requestJson<ApiPaperListResponse>("/papers", { baseUrl });
  },

  getWorkspace(baseUrl?: string) {
    return requestJson<ApiWorkspaceResponse>("/workspace", { baseUrl });
  },

  createLibrary(request: { name: string; description?: string; paper_ids?: string[] }, baseUrl?: string) {
    return requestJson<ApiResearchLibrary>("/workspace/libraries", {
      method: "POST",
      body: request,
      baseUrl
    });
  },

  updateLibrary(
    libraryId: string,
    request: { name?: string; description?: string; paper_ids?: string[]; group_ids?: string[] },
    baseUrl?: string
  ) {
    return requestJson<ApiResearchLibrary>(`/workspace/libraries/${libraryId}`, {
      method: "PATCH",
      body: request,
      baseUrl
    });
  },

  deleteLibrary(libraryId: string, baseUrl?: string) {
    return requestVoid(`/workspace/libraries/${libraryId}`, {
      method: "DELETE",
      baseUrl
    });
  },

  createConversation(
    libraryId: string,
    request: { title?: string; description?: string; messages?: ApiWorkspaceMessage[] },
    baseUrl?: string
  ) {
    return requestJson<ApiResearchConversation>(`/workspace/libraries/${libraryId}/conversations`, {
      method: "POST",
      body: request,
      baseUrl
    });
  },

  updateConversation(
    conversationId: string,
    request: { title?: string; description?: string; messages?: ApiWorkspaceMessage[] },
    baseUrl?: string
  ) {
    return requestJson<ApiResearchConversation>(`/workspace/conversations/${conversationId}`, {
      method: "PATCH",
      body: request,
      baseUrl
    });
  },

  deleteConversation(conversationId: string, baseUrl?: string) {
    return requestVoid(`/workspace/conversations/${conversationId}`, {
      method: "DELETE",
      baseUrl
    });
  },

  createPaperGroup(
    libraryId: string,
    request: { name: string; description?: string; paper_ids?: string[] },
    baseUrl?: string
  ) {
    return requestJson<ApiPaperGroup>(`/workspace/libraries/${libraryId}/paper-groups`, {
      method: "POST",
      body: request,
      baseUrl
    });
  },

  updatePaperGroup(
    groupId: string,
    request: { name?: string; description?: string; paper_ids?: string[] },
    baseUrl?: string
  ) {
    return requestJson<ApiPaperGroup>(`/workspace/paper-groups/${groupId}`, {
      method: "PATCH",
      body: request,
      baseUrl
    });
  },

  deletePaperGroup(groupId: string, baseUrl?: string) {
    return requestVoid(`/workspace/paper-groups/${groupId}`, {
      method: "DELETE",
      baseUrl
    });
  },

  movePaperToGroup(groupId: string, paperId: string, baseUrl?: string) {
    return requestJson<ApiPaperGroup>(`/workspace/paper-groups/${groupId}/papers/${paperId}`, {
      method: "POST",
      baseUrl
    });
  },

  uploadPaper(file: File, metadata?: { title?: string }, baseUrl?: string) {
    const formData = new FormData();
    formData.append("file", file);

    if (metadata?.title) {
      formData.append("title", metadata.title);
    }

    return requestJson<ApiPaperUploadResponse>("/papers/upload", {
      method: "POST",
      body: formData,
      baseUrl
    });
  },

  deletePaper(paperId: string, baseUrl?: string) {
    return requestVoid(`/papers/${paperId}`, {
      method: "DELETE",
      baseUrl
    });
  },

  createChat(request: ApiChatRequest, baseUrl?: string) {
    return requestJson<ApiChatResponse>("/chat", {
      method: "POST",
      body: request as unknown as Record<string, unknown>,
      baseUrl
    });
  },

  searchEvidence(query: string, paperIds?: string[], topK = 5, baseUrl?: string) {
    return requestJson<ApiRetrievalResponse>("/retrieval/search", {
      method: "POST",
      body: {
        query,
        paper_ids: paperIds,
        top_k: topK
      },
      baseUrl
    });
  },

  async streamChat(
    request: ApiChatRequest,
    baseUrl: string,
    onDelta: (token: string) => void,
    onEvidence?: (evidence: ApiPageEvidence[], note: string | null) => void,
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
        let parsed: {
          type: string;
          content?: string;
          answer?: string;
          evidence?: ApiPageEvidence[];
          note?: string | null;
          stats?: Record<string, unknown>;
          summary_message?: import("@/lib/types").ApiWorkspaceMessage | null;
          status?: number;
          detail?: string;
        };
        try {
          parsed = JSON.parse(dataStr);
        } catch {
          // skip malformed SSE lines
          continue;
        }
        if (parsed.type === "delta" && parsed.content) {
          onDelta(parsed.content);
        } else if (parsed.type === "evidence") {
          onEvidence?.(parsed.evidence ?? [], parsed.note ?? null);
        } else if (parsed.type === "done") {
          result = {
            answer: parsed.answer ?? "",
            evidence: parsed.evidence ?? [],
            note: parsed.note ?? null,
            stats: parsed.stats ?? {},
            summary_message: parsed.summary_message ?? null,
          };
        } else if (parsed.type === "error") {
          const streamError = parsed as ApiChatStreamError;
          throw new Error(streamError.detail || `Chat stream failed with status ${streamError.status}.`);
        }
      }
    }

    if (!result) {
      throw new Error("Stream ended without a done frame.");
    }
    return result;
  },
};
