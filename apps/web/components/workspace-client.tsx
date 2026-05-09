"use client";

import { useEffect, useMemo, useState } from "react";

import { ChatPanel } from "@/components/chat-panel";
import { EvidencePanel } from "@/components/evidence-panel";
import { ModelSettingsPanel } from "@/components/model-settings-panel";
import { PaperLibrary } from "@/components/paper-library";
import { PaperUploadPanel } from "@/components/paper-upload-panel";
import { SetupWizard } from "@/components/setup-wizard";
import { paperMemoryApi } from "@/lib/api";
import { mockChatMessages, mockEvidence, mockModelSettings, mockPapers } from "@/lib/mock-data";
import type {
  ApiChatResponse,
  ApiPageEvidence,
  ApiPaperMetadata,
  ChatMessage,
  EvidenceItem,
  InstallSettings,
  ModelSettings,
  PaperStatus,
  PaperSummary
} from "@/lib/types";

type ApiConnection = "checking" | "online" | "offline";

interface ApiStatus {
  connection: ApiConnection;
  label: string;
  detail: string;
}

const statusMap: Record<ApiPaperMetadata["status"], PaperStatus> = {
  queued: "queued",
  processing: "indexing",
  indexing: "indexing",
  ready: "ready",
  failed: "error"
};

const initialInstallSettings: InstallSettings = {
  mode: "demo",
  apiBaseUrl: "http://localhost:8000",
  qdrantUrl: "http://localhost:6333",
  storageRoot: "./storage",
  hfToken: "",
  visragModel: "openbmb/VisRAG-Ret",
  visragBackend: "stub",
  visragDevice: "auto",
  visragDtype: "auto",
  trustRemoteCode: false,
  qdrantVectorSize: 8,
  providerCompany: "OpenAI",
  providerBaseUrl: "https://api.openai.com/v1",
  providerModel: "gpt-4o",
  providerApiKey: ""
};

function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Unknown PaperMemory API error.";
}

function mapApiPaper(paper: ApiPaperMetadata): PaperSummary {
  const pages = paper.page_count ?? 0;
  const status = statusMap[paper.status];
  const progress = status === "ready" ? 100 : status === "error" ? 100 : status === "indexing" ? 55 : 12;

  return {
    id: paper.paper_id,
    title: paper.title ?? paper.filename,
    authors: ["Local PDF"],
    year: new Date(paper.created_at).getFullYear(),
    pages,
    status,
    progress,
    indexSummary:
      pages > 0
        ? `${pages} page images registered for VisRAG-style retrieval.`
        : "Upload accepted; page rendering has not reported a count yet."
  };
}

function citationsFromEvidence(evidence: ApiPageEvidence[], paperTitles: Record<string, string>) {
  return evidence.slice(0, 4).map((item) => ({
    paperId: item.paper_id,
    label: paperTitles[item.paper_id] ?? item.paper_id,
    page: item.page_number
  }));
}

export function WorkspaceClient() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>({
    connection: "checking",
    label: "Checking API",
    detail: "Probing FastAPI before loading the local library."
  });
  const [papers, setPapers] = useState<PaperSummary[]>(mockPapers);
  const [messages, setMessages] = useState<ChatMessage[]>(mockChatMessages);
  const [evidence, setEvidence] = useState<Array<EvidenceItem | ApiPageEvidence>>(mockEvidence);
  const [evidenceNote, setEvidenceNote] = useState<string | null>(null);
  const [settings, setSettings] = useState<ModelSettings>(mockModelSettings);
  const [installSettings, setInstallSettings] = useState<InstallSettings>(initialInstallSettings);
  const [question, setQuestion] = useState("");
  const [uploadTitle, setUploadTitle] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileInputKey, setFileInputKey] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [isChatSubmitting, setIsChatSubmitting] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [chatError, setChatError] = useState<string | null>(null);

  const paperTitles = useMemo(
    () => Object.fromEntries(papers.map((paper) => [paper.id, paper.title])),
    [papers]
  );

  const readyPaperIds = useMemo(
    () => papers.filter((paper) => paper.status === "ready").map((paper) => paper.id),
    [papers]
  );

  const loadWorkspace = async () => {
    setApiStatus({
      connection: "checking",
      label: "Checking API",
      detail: "Refreshing health and paper metadata."
    });

    try {
      const health = await paperMemoryApi.health(installSettings.apiBaseUrl);
      const paperList = await paperMemoryApi.listPapers(installSettings.apiBaseUrl);
      setPapers(paperList.papers.map(mapApiPaper));
      setApiStatus({
        connection: "online",
        label: "API online",
        detail: `${health.service} ${health.version} at ${health.storage_root}`
      });
    } catch (error) {
      setPapers(mockPapers);
      setEvidence(mockEvidence);
      setEvidenceNote("Using mock evidence until the local API is reachable.");
      setApiStatus({
        connection: "offline",
        label: "API offline",
        detail: `${getErrorMessage(error)} Mock workspace data is shown.`
      });
    }
  };

  useEffect(() => {
    void loadWorkspace();
  }, []);

  const searchEvidence = async (query: string) => {
    const response = await paperMemoryApi.searchEvidence(
      query,
      readyPaperIds.length > 0 ? readyPaperIds : undefined,
      settings.retrievalTopK,
      installSettings.apiBaseUrl
    );
    setEvidence(response.evidence);
    setEvidenceNote(response.note);
    return response.evidence;
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setUploadError("Choose a PDF before starting ingest.");
      return;
    }

    setIsUploading(true);
    setUploadError(null);
    setUploadMessage(null);

    try {
      const response = await paperMemoryApi.uploadPaper(selectedFile, {
        title: uploadTitle.trim() || undefined
      }, installSettings.apiBaseUrl);
      setUploadMessage(response.message);
      setSelectedFile(null);
      setFileInputKey((currentKey) => currentKey + 1);
      setUploadTitle("");
      await loadWorkspace();
    } catch (error) {
      setUploadError(getErrorMessage(error));
      setApiStatus({
        connection: "offline",
        label: "Upload failed",
        detail: "The upload API could not be reached; mock library data is still displayed."
      });
    } finally {
      setIsUploading(false);
    }
  };

  const handleSearchEvidence = async () => {
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion) {
      return;
    }

    setChatError(null);
    try {
      await searchEvidence(trimmedQuestion);
    } catch (error) {
      setEvidence(mockEvidence);
      setEvidenceNote("Search failed; mock evidence is displayed.");
      setChatError(getErrorMessage(error));
    }
  };

  const handleSubmitQuestion = async () => {
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion) {
      return;
    }

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: trimmedQuestion,
      citations: []
    };

    const priorMessages = messages.map((message) => ({
      role: message.role,
      content: message.content
    }));

    setMessages((currentMessages) => [...currentMessages, userMessage]);
    setQuestion("");
    setChatError(null);
    setIsChatSubmitting(true);

    try {
      await searchEvidence(trimmedQuestion);

      const response: ApiChatResponse = await paperMemoryApi.createChat({
        question: trimmedQuestion,
        paper_ids: readyPaperIds.length > 0 ? readyPaperIds : undefined,
        top_k: settings.retrievalTopK,
        messages: priorMessages,
        provider: settings.provider,
        base_url: settings.baseUrl.trim() || undefined,
        model: settings.model.trim() || undefined,
        api_key: settings.apiKey || undefined,
        temperature: settings.temperature
      }, installSettings.apiBaseUrl);

      setEvidence(response.evidence);
      setEvidenceNote(response.note);
      setMessages((currentMessages) => [
        ...currentMessages,
        {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          content: response.answer,
          citations: citationsFromEvidence(response.evidence, paperTitles)
        }
      ]);
      setApiStatus((currentStatus) => ({
        ...currentStatus,
        connection: "online",
        label: "API online"
      }));
    } catch (error) {
      setChatError(getErrorMessage(error));
      setEvidence(mockEvidence);
      setEvidenceNote("Chat failed; mock evidence remains visible.");
      setApiStatus({
        connection: "offline",
        label: "Chat API error",
        detail: "The chat request failed; mock workspace data is still available."
      });
    } finally {
      setIsChatSubmitting(false);
    }
  };

  const resetChat = () => {
    setMessages(mockChatMessages);
    setEvidence(mockEvidence);
    setEvidenceNote(apiStatus.connection === "offline" ? "Using mock evidence until the local API is reachable." : null);
    setChatError(null);
    setQuestion("");
  };

  return (
    <main className="app-shell">
      <header className="topbar" aria-label="Workspace summary">
        <div>
          <p className="eyebrow">Local workspace</p>
          <h1>PaperMemory</h1>
          <p className="topbar__detail">{apiStatus.detail}</p>
        </div>
        <div className="topbar__meta" aria-label="System status">
          <span className={`status-dot status-dot--${apiStatus.connection}`} aria-hidden="true" />
          <span>{apiStatus.label}</span>
          <span>Qdrant local</span>
          <span>VisRAG-Ret ready</span>
        </div>
      </header>

      <SetupWizard
        settings={installSettings}
        onChange={setInstallSettings}
        onApplyModelSettings={setSettings}
      />

      <section className="workspace-grid" aria-label="PaperMemory workspace">
        <div className="rail">
          <PaperUploadPanel
            title={uploadTitle}
            selectedFile={selectedFile}
            fileInputKey={fileInputKey}
            isUploading={isUploading}
            message={uploadMessage}
            error={uploadError}
            onTitleChange={setUploadTitle}
            onFileChange={setSelectedFile}
            onUpload={handleUpload}
          />
          <PaperLibrary papers={papers} />
        </div>

        <ChatPanel
          messages={messages}
          question={question}
          isSubmitting={isChatSubmitting}
          error={chatError}
          onQuestionChange={setQuestion}
          onSubmit={handleSubmitQuestion}
          onReset={resetChat}
          onSearchEvidence={handleSearchEvidence}
        />

        <aside className="side-stack" aria-label="Retrieval and model controls">
          <ModelSettingsPanel settings={settings} onChange={setSettings} />
          <EvidencePanel evidence={evidence} paperTitles={paperTitles} note={evidenceNote} />
        </aside>
      </section>
    </main>
  );
}
