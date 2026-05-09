import type { ChatMessage, EvidenceItem, ModelSettings, PaperSummary } from "@/lib/types";

export const mockPapers: PaperSummary[] = [
  {
    id: "paper-visrag",
    title: "VisRAG-Ret for Page Image Retrieval",
    authors: ["Chen", "Ibrahim"],
    year: 2025,
    pages: 18,
    status: "ready",
    progress: 100,
    indexSummary: "18 page images embedded, 42 text chunks linked to Qdrant."
  },
  {
    id: "paper-evisrag",
    title: "Evidence-aware Visual Retrieval Augmented Generation",
    authors: ["Park", "Singh", "Mori"],
    year: 2026,
    pages: 24,
    status: "indexing",
    progress: 68,
    indexSummary: "Page thumbnails complete, multimodal embeddings still running."
  },
  {
    id: "paper-survey",
    title: "Local-first Research Agents: A Survey",
    authors: ["Alvarez"],
    year: 2024,
    pages: 31,
    status: "queued",
    progress: 12,
    indexSummary: "Waiting for OCR worker after metadata extraction."
  }
];

export const mockChatMessages: ChatMessage[] = [
  {
    id: "msg-1",
    role: "user",
    content: "Which evidence supports using page images instead of text-only chunks?",
    citations: []
  },
  {
    id: "msg-2",
    role: "assistant",
    content:
      "The strongest support is in the figure-heavy evaluation: page image retrieval keeps table structure and visual captions together, while the text-only baseline splits them across chunks.",
    citations: [
      { paperId: "paper-visrag", label: "VisRAG-Ret", page: 6 },
      { paperId: "paper-evisrag", label: "EVisRAG", page: 11 }
    ]
  }
];

export const mockEvidence: EvidenceItem[] = [
  {
    id: "ev-1",
    paperId: "paper-visrag",
    paperTitle: "VisRAG-Ret for Page Image Retrieval",
    page: 6,
    retriever: "VisRAG-Ret",
    confidence: 91,
    snippet: "Ablation table compares page image retrieval with text-only chunk retrieval."
  },
  {
    id: "ev-2",
    paperId: "paper-evisrag",
    paperTitle: "Evidence-aware Visual Retrieval Augmented Generation",
    page: 11,
    retriever: "Hybrid",
    confidence: 84,
    snippet: "Prompt template requires answer spans to cite retrieved page evidence."
  },
  {
    id: "ev-3",
    paperId: "paper-survey",
    paperTitle: "Local-first Research Agents: A Survey",
    page: 19,
    retriever: "Qdrant text",
    confidence: 72,
    snippet: "Local storage section discusses privacy constraints for BYOK workflows."
  }
];

export const mockModelSettings: ModelSettings = {
  provider: "openai-compatible",
  providerCompany: "OpenAI",
  baseUrl: "https://api.openai.com/v1",
  model: "gpt-4.1-mini",
  apiKey: "",
  temperature: 0.2,
  retrievalTopK: 6,
  requireEvidence: true
};
