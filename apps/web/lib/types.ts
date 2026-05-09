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

export interface EvidenceItem {
  id: string;
  paperId: string;
  paperTitle: string;
  page: number;
  retriever: "VisRAG-Ret" | "Qdrant text" | "Hybrid";
  confidence: number;
  snippet: string;
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
  image_path: string | null;
  title?: string | null;
  caption: string | null;
  metadata?: Record<string, string> | null;
}

export interface ApiRetrievalResponse {
  query: string;
  evidence: ApiPageEvidence[];
  retrieval_model: string;
  note: string | null;
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
  messages?: Array<{
    role: "system" | "user" | "assistant";
    content: string;
  }>;
}

export interface ApiChatResponse {
  answer: string;
  evidence: ApiPageEvidence[];
  model: string;
  prompt_preview: string;
  note: string | null;
}
