import type {
  ApiChatRequest,
  ApiChatResponse,
  ApiHealthResponse,
  ApiPaperListResponse,
  ApiPaperUploadResponse,
  ApiRetrievalResponse,
  ApiResearchConversation,
  ApiResearchLibrary,
  ApiPaperGroup,
  ApiWorkspaceMessage,
  ApiWorkspaceResponse,
} from "@/lib/types";

const defaultBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: BodyInit | Record<string, unknown>;
  baseUrl?: string;
};

async function requestJson<TResponse>(
  path: string,
  { body, headers, baseUrl, ...options }: RequestOptions = {}
): Promise<TResponse> {
  const isFormBody = body instanceof FormData;
  const apiBaseUrl = baseUrl?.trim() || defaultBaseUrl;
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
  }
};
