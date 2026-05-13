import type {
  ChatMessage,
  EvidenceItem,
  ModelSettings,
  PaperSummary,
  ResearchConversation,
  ResearchLibrary,
  PaperGroup
} from "@/lib/types";

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

export const mockResearchLibraries: ResearchLibrary[] = [
  {
    id: "library-visrag",
    name: "Visual RAG Reading",
    description: "Papers about page-image retrieval, evidence prompts, and BYOK multimodal QA.",
    paperIds: ["paper-visrag", "paper-evisrag"],
    groupIds: ["group-visrag-core"],
    createdAt: "2026-05-04T10:00:00.000Z",
    updatedAt: "2026-05-11T08:10:00.000Z"
  },
  {
    id: "library-local-agents",
    name: "Local Research Agents",
    description: "Local-first agent memory, privacy boundaries, and personal paper workspaces.",
    paperIds: ["paper-survey"],
    groupIds: ["group-local-boundary"],
    createdAt: "2026-05-05T10:00:00.000Z",
    updatedAt: "2026-05-09T16:45:00.000Z"
  },
  {
    id: "library-inbox",
    name: "Inbox",
    description: "Fresh uploads before they are organized into a research database.",
    paperIds: [],
    groupIds: ["group-inbox"],
    createdAt: "2026-05-04T10:00:00.000Z",
    updatedAt: "2026-05-04T10:00:00.000Z"
  }
];

export const mockPaperGroups: PaperGroup[] = [
  {
    id: "group-visrag-core",
    libraryId: "library-visrag",
    name: "Core visual retrieval",
    description: "Primary VisRAG and EVisRAG papers.",
    paperIds: ["paper-visrag", "paper-evisrag"],
    createdAt: "2026-05-04T10:00:00.000Z",
    updatedAt: "2026-05-11T08:10:00.000Z"
  },
  {
    id: "group-local-boundary",
    libraryId: "library-local-agents",
    name: "Privacy boundary",
    description: "Local-first design references.",
    paperIds: ["paper-survey"],
    createdAt: "2026-05-05T10:00:00.000Z",
    updatedAt: "2026-05-09T16:45:00.000Z"
  },
  {
    id: "group-inbox",
    libraryId: "library-inbox",
    name: "Ungrouped uploads",
    description: "Fresh local PDFs before organization.",
    paperIds: [],
    createdAt: "2026-05-04T10:00:00.000Z",
    updatedAt: "2026-05-04T10:00:00.000Z"
  }
];

export const mockConversations: ResearchConversation[] = [
  {
    id: "conversation-visrag-main",
    libraryId: "library-visrag",
    title: "Why page images?",
    description: "Compare visual retrieval evidence with text-only chunks.",
    messages: mockChatMessages,
    createdAt: "2026-05-04T10:30:00.000Z",
    updatedAt: "2026-05-11T08:10:00.000Z"
  },
  {
    id: "conversation-prompting",
    libraryId: "library-visrag",
    title: "EVisRAG prompt shape",
    description: "Draft prompt rules for grounded visual answers.",
    messages: [
      {
        id: "msg-prompt-1",
        role: "assistant",
        content:
          "Start from retrieved page images, cite page numbers, and explicitly say when evidence is insufficient.",
        citations: [{ paperId: "paper-evisrag", label: "EVisRAG", page: 3 }]
      }
    ],
    createdAt: "2026-05-06T12:00:00.000Z",
    updatedAt: "2026-05-10T18:20:00.000Z"
  },
  {
    id: "conversation-local-boundary",
    libraryId: "library-local-agents",
    title: "Local-first boundary",
    description: "Track what must stay local before hosted collaboration exists.",
    messages: [
      {
        id: "msg-local-1",
        role: "assistant",
        content:
          "For the open-source MVP, PDFs, rendered pages, embeddings, API keys, and provider choices should remain under user control.",
        citations: [{ paperId: "paper-survey", label: "Local-first Research Agents", page: 19 }]
      }
    ],
    createdAt: "2026-05-07T09:15:00.000Z",
    updatedAt: "2026-05-09T16:45:00.000Z"
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
  requireEvidence: true,
  useMultimodalContext: true,
  maxEvidenceImages: 4
};
