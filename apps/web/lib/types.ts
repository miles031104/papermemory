export type PaperStatus = "queued" | "indexing" | "ready" | "error";
export type ApiPaperStatus = "queued" | "processing" | "indexing" | "ready" | "failed";

export interface PaperSummary {
  id: string;
  title: string;
  authors: string[];
  year: number;
  pages: number;
  status: PaperStatus;
  progress: number;
  indexSummary: string;
}

export interface Citation {
  paperId: string;
  label: string;
  page: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
}

export interface ResearchLibrary {
  id: string;
  name: string;
  description: string;
  paperIds: string[];
  groupIds: string[];
  createdAt: string;
  updatedAt: string;
}

export interface ResearchConversation {
  id: string;
  libraryId: string;
  title: string;
  description: string;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
}

export interface PaperGroup {
  id: string;
  libraryId: string;
  name: string;
  description: string;
  paperIds: string[];
  createdAt: string;
  updatedAt: string;
}

export type WorkspaceView = "home" | "chat" | "papers" | "settings";

export interface EvidenceItem {
  id: string;
  paperId: string;
  paperTitle: string;
  page: number;
  retriever: "VisRAG-Ret" | "Qdrant text" | "Hybrid";
  confidence: number;
  snippet: string;
  imageUrl?: string | null;
}

export interface ModelSettings {
  provider: "openai-compatible";
  providerCompany: string;
  baseUrl: string;
  model: string;
  apiKey: string;
  temperature: number;
  retrievalTopK: number;
  requireEvidence: boolean;
  useMultimodalContext: boolean;
  maxEvidenceImages: number;
}

export type InstallMode = "demo" | "local-visrag" | "custom";

export interface InstallSettings {
  mode: InstallMode;
  apiBaseUrl: string;
  qdrantUrl: string;
  storageRoot: string;
  hfToken: string;
  visragModel: string;
  visragBackend: "stub" | "transformers";
  visragDevice: "auto" | "cpu" | "cuda";
  visragDtype: "auto" | "float32" | "float16" | "bfloat16";
  trustRemoteCode: boolean;
  qdrantVectorSize: number;
  useMultimodalContext: boolean;
  maxEvidenceImages: number;
  providerCompany: string;
  providerBaseUrl: string;
  providerModel: string;
  providerApiKey: string;
}

export interface ChatRequest {
  question: string;
  paperIds?: string[];
  settings?: Partial<ModelSettings>;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  evidence: EvidenceItem[];
}

export interface UploadPaperResponse {
  paper: PaperSummary;
}

export interface ApiPaperMetadata {
  paper_id: string;
  title: string | null;
  filename: string;
  status: ApiPaperStatus;
  page_count: number | null;
  created_at: string;
}

export interface ApiPaperListResponse {
  papers: ApiPaperMetadata[];
}

export interface ApiPaperUploadResponse {
  paper: ApiPaperMetadata;
  message: string;
}

export interface ApiHealthResponse {
  status: string;
  service: string;
  version: string;
  storage_root: string;
}

export interface ApiPageEvidence {
  paper_id: string;
  page_number: number;
  score: number;
  image_url?: string | null;
  title?: string | null;
  caption: string | null;
  metadata?: Record<string, string> | null;
}

export type ApiResponseStatus = "success" | "partial" | "error";

export interface ApiRetrievalStats {
  retrieval_attempted: boolean;
  paper_scope_count: number;
  evidence_count: number;
}

export interface ApiRetrievalResponse {
  status: ApiResponseStatus;
  query: string;
  evidence: ApiPageEvidence[];
  retrieval_model: string;
  note: string | null;
  stats: ApiRetrievalStats;
  limits: string[];
}

export interface ApiChatRequest {
  question: string;
  paper_ids?: string[];
  top_k?: number;
  provider?: "openai-compatible";
  base_url?: string;
  model?: string;
  api_key?: string;
  temperature?: number;
  enable_image_context?: boolean;
  max_evidence_images?: number;
  enable_query_rewrite?: boolean;
  enable_agentic_retrieval?: boolean;
  messages?: Array<{
    role: "system" | "user" | "assistant";
    content: string;
  }>;
}

export interface ApiChatResponse {
  status: ApiResponseStatus;
  answer: string;
  evidence: ApiPageEvidence[];
  model: string;
  prompt_preview: string;
  note: string | null;
  stats: ApiRetrievalStats & {
    included_image_count: number;
  };
  limits: string[];
}

export interface ApiWorkspaceCitation {
  paper_id: string;
  label: string;
  page: number;
}

export interface ApiWorkspaceMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: ApiWorkspaceCitation[];
}

export interface ApiChatSummaryMessage {
  id?: string;
  role: "user" | "assistant";
  content: string;
  citations?: ApiWorkspaceCitation[];
}

export interface ApiResearchLibrary {
  id: string;
  name: string;
  description: string;
  paper_ids: string[];
  group_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface ApiResearchConversation {
  id: string;
  library_id: string;
  title: string;
  description: string;
  messages: ApiWorkspaceMessage[];
  created_at: string;
  updated_at: string;
}

export interface ApiPaperGroup {
  id: string;
  library_id: string;
  name: string;
  description: string;
  paper_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface ApiWorkspaceResponse {
  libraries: ApiResearchLibrary[];
  conversations: ApiResearchConversation[];
  paper_groups: ApiPaperGroup[];
}

export interface ApiChatStreamDone {
  answer: string;
  evidence: ApiPageEvidence[];
  note: string | null;
  stats: Record<string, unknown>;
  summary_message?: ApiChatSummaryMessage | null;
}

export interface ApiChatStreamError {
  status: number;
  detail: string;
}
