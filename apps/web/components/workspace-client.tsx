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
  mockResearchLibraries,
} from "@/lib/mock-data";
import type {
  ApiPaperMetadata,
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
  ResearchLibrary,
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
  failed: "error",
};

const initialInstallSettings: InstallSettings = {
  mode: "demo",
  apiBaseUrl: defaultApiBaseUrl,
  qdrantUrl: "http://localhost:6333",
  storageRoot: "./storage",
  hfToken: "",
  visragModel: "openbmb/VisRAG-Ret",
  visragBackend: "stub",
  visragDevice: "auto",
  visragDtype: "auto",
  trustRemoteCode: false,
  qdrantVectorSize: 8,
  useMultimodalContext: true,
  maxEvidenceImages: 4,
  providerCompany: "OpenAI",
  providerBaseUrl: "https://api.openai.com/v1",
  providerModel: "gpt-4o",
  providerApiKey: "",
};

const MODEL_SETTINGS_STORAGE_KEY = "papermemory.modelSettings.v1";
const INSTALL_SETTINGS_STORAGE_KEY = "papermemory.installSettings.v1";

function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Unknown PaperMemory API error.";
}

function readStoredSettings<T extends object>(key: string, defaults: T): T {
  if (typeof window === "undefined") {
    return defaults;
  }
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) {
      return defaults;
    }
    const parsed = JSON.parse(raw) as Partial<T>;
    return { ...defaults, ...parsed };
  } catch {
    return defaults;
  }
}

function writeStoredSettings<T extends object>(key: string, value: T) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Local storage can be unavailable in private or restricted browser contexts.
  }
}

function mapApiPaper(paper: ApiPaperMetadata): PaperSummary {
  const pages = paper.page_count ?? 0;
  const status = statusMap[paper.status];
  const progress =
    status === "ready" ? 100 : status === "error" ? 100 : status === "indexing" ? 55 : 12;

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
        : "Upload accepted; page rendering has not reported a count yet.",
  };
}

function mapApiCitation(citation: { paper_id: string; label: string; page: number }): Citation {
  return {
    paperId: citation.paper_id,
    label: citation.label,
    page: citation.page,
  };
}

function mapCitationToApi(citation: Citation) {
  return {
    paper_id: citation.paperId,
    label: citation.label,
    page: citation.page,
  };
}

function mapApiWorkspaceMessage(message: ApiWorkspaceMessage): ChatMessage {
  return {
    id: message.id,
    role: message.role,
    content: message.content,
    citations: message.citations.map(mapApiCitation),
  };
}

function mapMessageToApi(message: ChatMessage): ApiWorkspaceMessage {
  return {
    id: message.id,
    role: message.role,
    content: message.content,
    citations: message.citations.map(mapCitationToApi),
  };
}

function mapApiLibrary(library: ApiResearchLibrary): ResearchLibrary {
  return {
    id: library.id,
    name: library.name,
    description: library.description,
    paperIds: library.paper_ids,
    groupIds: library.group_ids,
    createdAt: library.created_at,
    updatedAt: library.updated_at,
  };
}

function mapApiConversation(conversation: ApiResearchConversation): ResearchConversation {
  return {
    id: conversation.id,
    libraryId: conversation.library_id,
    title: conversation.title,
    description: conversation.description,
    messages: conversation.messages.map(mapApiWorkspaceMessage),
    createdAt: conversation.created_at,
    updatedAt: conversation.updated_at,
  };
}

function mapApiPaperGroup(group: ApiPaperGroup): PaperGroup {
  return {
    id: group.id,
    libraryId: group.library_id,
    name: group.name,
    description: group.description,
    paperIds: group.paper_ids,
    createdAt: group.created_at,
    updatedAt: group.updated_at,
  };
}

function makeConversation(libraryId: string, title = "New research chat"): ResearchConversation {
  const now = new Date().toISOString();
  const id = `conversation-${Date.now()}`;

  return {
    id,
    libraryId,
    title,
    description: "A local chat scoped to the active paper database.",
    messages: [],
    createdAt: now,
    updatedAt: now,
  };
}

export function WorkspaceClient() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>({
    connection: "checking",
    label: "Checking API",
    detail: "Probing FastAPI before loading the local library.",
  });
  const [libraries, setLibraries] = useState<ResearchLibrary[]>(mockResearchLibraries);
  const [activeLibraryId, setActiveLibraryId] = useState(mockResearchLibraries[0]?.id ?? "");
  const [conversations, setConversations] = useState<ResearchConversation[]>(mockConversations);
  const [activeConversationId, setActiveConversationId] = useState(
    mockConversations[0]?.id ?? "",
  );
  const [paperGroups, setPaperGroups] = useState<PaperGroup[]>(mockPaperGroups);
  const [isWorkspacePersisted, setIsWorkspacePersisted] = useState(false);
  const [papers, setPapers] = useState<PaperSummary[]>(mockPapers);
  const [settings, setSettings] = useState<ModelSettings>(() =>
    readStoredSettings(MODEL_SETTINGS_STORAGE_KEY, mockModelSettings),
  );
  const [installSettings, setInstallSettings] = useState<InstallSettings>(() =>
    readStoredSettings(INSTALL_SETTINGS_STORAGE_KEY, initialInstallSettings),
  );
  const [uploadTitle, setUploadTitle] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileInputKey, setFileInputKey] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [activeView, setActiveView] = useState<WorkspaceView>("research");

  const paperTitles = useMemo(
    () => Object.fromEntries(papers.map((paper) => [paper.id, paper.title])),
    [papers],
  );

  const activeLibrary = useMemo(
    () => libraries.find((library) => library.id === activeLibraryId) ?? libraries[0],
    [activeLibraryId, libraries],
  );

  const activeConversation = useMemo(() => {
    const activeLibraryConversations = conversations.filter(
      (conversation) => conversation.libraryId === activeLibrary?.id,
    );
    return (
      activeLibraryConversations.find(
        (conversation) => conversation.id === activeConversationId,
      ) ?? activeLibraryConversations[0]
    );
  }, [activeConversationId, activeLibrary?.id, conversations]);

  const activeLibraryPapers = useMemo(() => {
    const paperIds = new Set(activeLibrary?.paperIds ?? []);
    return papers.filter((paper) => paperIds.has(paper.id));
  }, [activeLibrary?.paperIds, papers]);

  const readyPaperIds = useMemo(
    () =>
      activeLibraryPapers.filter((paper) => paper.status === "ready").map((paper) => paper.id),
    [activeLibraryPapers],
  );

  const activeLibraryGroups = useMemo(
    () => paperGroups.filter((group) => group.libraryId === activeLibrary?.id),
    [activeLibrary?.id, paperGroups],
  );

  const setConversationMessages = (conversationId: string, nextMessages: ChatMessage[]) => {
    const now = new Date().toISOString();
    setConversations((currentConversations) =>
      currentConversations.map((conversation) =>
        conversation.id === conversationId
          ? { ...conversation, messages: nextMessages, updatedAt: now }
          : conversation,
      ),
    );
  };

  const replaceConversation = (conversation: ResearchConversation) => {
    setConversations((currentConversations) => {
      const exists = currentConversations.some((item) => item.id === conversation.id);
      if (!exists) {
        return [conversation, ...currentConversations];
      }
      return currentConversations.map((item) =>
        item.id === conversation.id ? conversation : item,
      );
    });
  };

  const persistConversationMessages = async (
    conversationId: string,
    nextMessages: ChatMessage[],
  ) => {
    if (!isWorkspacePersisted) {
      return;
    }
    const updated = await paperMemoryApi.updateConversation(
      conversationId,
      { messages: nextMessages.map(mapMessageToApi) },
      installSettings.apiBaseUrl,
    );
    replaceConversation(mapApiConversation(updated));
  };

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

  const workspaceMetrics = useMemo(() => {
    const readyPapers = activeLibraryPapers.filter((paper) => paper.status === "ready").length;
    const indexedPages = activeLibraryPapers.reduce((total, paper) => total + paper.pages, 0);
    const activeEvidence = evidence.length;

    return [
      { label: "Ready papers", value: readyPapers.toString().padStart(2, "0") },
      { label: "Indexed pages", value: indexedPages.toLocaleString() },
      { label: "Evidence queue", value: activeEvidence.toString().padStart(2, "0") },
    ];
  }, [activeLibraryPapers, evidence.length]);

  const createConversation = async (libraryId = activeLibrary?.id ?? activeLibraryId) => {
    if (!libraryId) return;

    let conversation = makeConversation(libraryId);
    if (isWorkspacePersisted) {
      const created = await paperMemoryApi.createConversation(
        libraryId,
        {
          title: conversation.title,
          description: conversation.description,
          messages: [],
        },
        installSettings.apiBaseUrl,
      );
      conversation = mapApiConversation(created);
    }

    setConversations((currentConversations) => [conversation, ...currentConversations]);
    setActiveLibraryId(libraryId);
    setActiveConversationId(conversation.id);
  };

  const createLibrary = async (name: string, description: string) => {
    const trimmedName = name.trim();
    if (!trimmedName) {
      throw new Error("Database name is required.");
    }

    let library: ResearchLibrary;
    let conversation: ResearchConversation | null = null;

    if (isWorkspacePersisted) {
      const createdLibrary = await paperMemoryApi.createLibrary(
        {
          name: trimmedName,
          description: description.trim(),
        },
        installSettings.apiBaseUrl,
      );
      library = mapApiLibrary(createdLibrary);

      try {
        const createdConversation = await paperMemoryApi.createConversation(
          library.id,
          {
            title: "Research chat",
            description: "A local chat scoped to this paper database.",
            messages: [],
          },
          installSettings.apiBaseUrl,
        );
        conversation = mapApiConversation(createdConversation);
      } catch {
        setLibraries((currentLibraries) => [
          library,
          ...currentLibraries.filter((item) => item.id !== library.id),
        ]);
        setActiveLibraryId(library.id);
        setActiveConversationId("");
        await loadWorkspace({ paperId: "", libraryId: library.id });
        return;
      }
    } else {
      const now = new Date().toISOString();
      library = {
        id: `library-${Date.now()}`,
        name: trimmedName,
        description: description.trim(),
        paperIds: [],
        groupIds: [],
        createdAt: now,
        updatedAt: now,
      };
      conversation = makeConversation(library.id, "Research chat");
    }

    setLibraries((currentLibraries) => [library, ...currentLibraries]);
    setConversations((currentConversations) => [conversation, ...currentConversations]);
    setActiveLibraryId(library.id);
    setActiveConversationId(conversation.id);
  };

  const selectLibrary = async (libraryId: string) => {
    const existingConversation = conversations.find(
      (conversation) => conversation.libraryId === libraryId,
    );
    setActiveLibraryId(libraryId);

    if (existingConversation) {
      setActiveConversationId(existingConversation.id);
      return;
    }

    setActiveConversationId("");

    let conversation = makeConversation(libraryId);
    if (isWorkspacePersisted) {
      const created = await paperMemoryApi.createConversation(
        libraryId,
        {
          title: conversation.title,
          description: conversation.description,
          messages: [],
        },
        installSettings.apiBaseUrl,
      );
      conversation = mapApiConversation(created);
    }
    setConversations((currentConversations) => [conversation, ...currentConversations]);
    setActiveConversationId(conversation.id);
  };

  const loadWorkspace = async (assignment?: { paperId: string; libraryId: string }) => {
    setApiStatus({
      connection: "checking",
      label: "Checking API",
      detail: "Refreshing health and paper metadata.",
    });

    try {
      const [health, paperList, workspace] = await Promise.all([
        paperMemoryApi.health(installSettings.apiBaseUrl),
        paperMemoryApi.listPapers(installSettings.apiBaseUrl),
        paperMemoryApi.getWorkspace(installSettings.apiBaseUrl),
      ]);
      const mappedPapers = paperList.papers.map(mapApiPaper);
      setPapers(mappedPapers);
      const mappedLibraries = workspace.libraries.map(mapApiLibrary);
      const mappedConversations = workspace.conversations.map(mapApiConversation);
      const mappedGroups = workspace.paper_groups.map(mapApiPaperGroup);
      setLibraries(mappedLibraries);
      setConversations(mappedConversations);
      setPaperGroups(mappedGroups);
      setIsWorkspacePersisted(true);
      const nextActiveLibraryId =
        assignment?.libraryId &&
        mappedLibraries.some((library) => library.id === assignment.libraryId)
          ? assignment.libraryId
          : mappedLibraries.some((library) => library.id === activeLibraryId)
            ? activeLibraryId
            : (mappedLibraries[0]?.id ?? "");
      const nextConversation = assignment?.libraryId
        ? mappedConversations.find(
            (conversation) => conversation.libraryId === nextActiveLibraryId,
          )
        : (mappedConversations.find(
              (conversation) =>
                conversation.id === activeConversationId &&
                conversation.libraryId === nextActiveLibraryId,
            ) ??
            mappedConversations.find(
              (conversation) => conversation.libraryId === nextActiveLibraryId,
            ));
      setActiveLibraryId(nextActiveLibraryId);
      setActiveConversationId(nextConversation?.id ?? "");
      setApiStatus({
        connection: "online",
        label: "API online",
        detail: `${health.service} ${health.version} at ${health.storage_root}`,
      });
    } catch (error) {
      setPapers(mockPapers);
      setLibraries((currentLibraries) =>
        currentLibraries.length > 0 ? currentLibraries : mockResearchLibraries,
      );
      setConversations((currentConversations) =>
        currentConversations.length > 0 ? currentConversations : mockConversations,
      );
      setPaperGroups(mockPaperGroups);
      setIsWorkspacePersisted(false);
      setApiStatus({
        connection: "offline",
        label: "API offline",
        detail: `${getErrorMessage(error)} Mock workspace data is shown.`,
      });
    }
  };

  useEffect(() => {
    void loadWorkspace();
  }, []);

  useEffect(() => {
    writeStoredSettings(MODEL_SETTINGS_STORAGE_KEY, settings);
  }, [settings]);

  useEffect(() => {
    writeStoredSettings(INSTALL_SETTINGS_STORAGE_KEY, installSettings);
  }, [installSettings]);

  const handleUpload = async () => {
    if (!selectedFile) {
      setUploadError("Choose a PDF before starting ingest.");
      return;
    }

    setIsUploading(true);
    setUploadError(null);
    setUploadMessage(null);

    try {
      const response = await paperMemoryApi.uploadPaper(
        selectedFile,
        { title: uploadTitle.trim() || undefined },
        installSettings.apiBaseUrl,
      );
      const uploadedPaper = mapApiPaper(response.paper);
      const libraryId = activeLibrary?.id ?? activeLibraryId;
      const nextLibraryPaperIds = activeLibrary?.paperIds.includes(uploadedPaper.id)
        ? activeLibrary.paperIds
        : [uploadedPaper.id, ...(activeLibrary?.paperIds ?? [])];
      if (isWorkspacePersisted && libraryId) {
        await paperMemoryApi.updateLibrary(
          libraryId,
          { paper_ids: nextLibraryPaperIds },
          installSettings.apiBaseUrl,
        );
      }
      setPapers((currentPapers) => {
        const withoutUploadedPaper = currentPapers.filter((paper) => paper.id !== uploadedPaper.id);
        return [uploadedPaper, ...withoutUploadedPaper];
      });
      setLibraries((currentLibraries) =>
        currentLibraries.map((library) =>
          library.id === libraryId && !library.paperIds.includes(uploadedPaper.id)
            ? { ...library, paperIds: [uploadedPaper.id, ...library.paperIds] }
            : library,
        ),
      );
      setUploadMessage(response.message);
      setSelectedFile(null);
      setFileInputKey((currentKey) => currentKey + 1);
      setUploadTitle("");
      await loadWorkspace({ paperId: uploadedPaper.id, libraryId });
    } catch (error) {
      setUploadError(getErrorMessage(error));
      setApiStatus({
        connection: "offline",
        label: "Upload failed",
        detail:
          "The upload API could not be reached; mock library data is still displayed.",
      });
    } finally {
      setIsUploading(false);
    }
  };

  const handleSelectLibrary = (libraryId: string) => {
    const library = libraries.find((item) => item.id === libraryId);
    void selectLibrary(libraryId).catch((error) => {
      console.error(
        `${library?.name ?? "The database"} is active, but the default conversation could not be created. ${getErrorMessage(error)}`,
      );
    });
  };

  const handleSelectConversation = (conversationId: string) => {
    setActiveConversationId(conversationId);
  };

  const handleCreateConversation = () => {
    void createConversation().catch((error) => {
      console.error(getErrorMessage(error));
    });
  };

  return (
    <main className="app-shell">
      <nav className="product-nav" aria-label="PaperMemory navigation">
        <button className="brand-mark" type="button" onClick={() => setActiveView("research")}>
          <span className="brand-mark__glyph" aria-hidden="true">PM</span>
          <span>PaperMemory</span>
        </button>
        <div className="product-nav__links" role="tablist" aria-label="Workspace views">
          <button
            className={activeView === "research" ? "product-nav__link product-nav__link--active" : "product-nav__link"}
            type="button"
            role="tab"
            aria-selected={activeView === "research"}
            onClick={() => setActiveView("research")}
          >
            Workspace
          </button>
          <button
            className={activeView === "settings" ? "product-nav__link product-nav__link--active" : "product-nav__link"}
            type="button"
            role="tab"
            aria-selected={activeView === "settings"}
            onClick={() => setActiveView("settings")}
          >
            Settings
          </button>
        </div>
        <div className="product-nav__status" aria-label="API status">
          <span className={`status-dot status-dot--${apiStatus.connection}`} aria-hidden="true" />
          <span>{apiStatus.label}</span>
        </div>
      </nav>

      <section className="hero-section" aria-labelledby="hero-title">
        <div className="hero-section__copy">
          <p className="hero-kicker">Local-first visual RAG for serious reading</p>
          <h1 id="hero-title">A research memory that sees the page, not just the text.</h1>
          <p className="hero-section__lead">
            Upload papers, retrieve visual page evidence, and ask model-backed questions across a private local library.
          </p>
          <div className="hero-actions">
            <button className="button button--primary button--hero" type="button" onClick={() => setActiveView("research")}>
              Open workspace
            </button>
            <button className="button button--subtle button--hero" type="button" onClick={() => setActiveView("settings")}>
              Configure models
            </button>
          </div>
        </div>

        <div className="hero-command" aria-label="Active research command center">
          <div className="hero-command__top">
            <div>
              <p className="eyebrow">Active database</p>
              <h2>{activeLibrary?.name ?? "Research database"}</h2>
            </div>
            <span className="hero-command__pill">{isWorkspacePersisted ? "Local sync" : "Demo mode"}</span>
          </div>
          <div className="hero-command__prompt">
            <span aria-hidden="true">Ask</span>
            <p>{question.trim() || "What does this paper prove, and where is the evidence?"}</p>
          </div>
          <div className="hero-metrics">
            {workspaceMetrics.map((metric) => (
              <div className="hero-metric" key={metric.label}>
                <strong>{metric.value}</strong>
                <span>{metric.label}</span>
              </div>
            ))}
          </div>
          <div className="hero-evidence-strip" aria-hidden="true">
            <span />
            <span />
            <span />
            <span />
          </div>
        </div>
      </section>

      <section
        className={`workspace-grid workspace-grid--${activeView}`}
        aria-label="PaperMemory workspace"
      >
        <ResearchSidebar
          libraries={libraries}
          conversations={conversations}
          papers={papers}
          activeLibraryId={activeLibrary?.id ?? activeLibraryId}
          activeConversationId={activeConversation?.id ?? activeConversationId}
          activeView={activeView}
          apiLabel={apiStatus.label}
          apiConnection={apiStatus.connection}
          isPersisted={isWorkspacePersisted}
          onViewChange={setActiveView}
          onSelectLibrary={handleSelectLibrary}
          onSelectConversation={handleSelectConversation}
          onCreateConversation={handleCreateConversation}
          onCreateLibrary={createLibrary}
        />

        {activeView === "research" ? (
          <>
            <div className="workspace-main">
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
              <ChatPanel
                messages={messages}
                question={question}
                isSubmitting={isChatSubmitting}
                title={activeConversation?.title ?? "Research chat"}
                contextLabel={activeLibrary?.name ?? "Research database"}
                libraryDescription={
                  activeLibrary?.description ?? "Ask questions over the active paper database."
                }
                error={chatError}
                onQuestionChange={setQuestion}
                onSubmit={handleSubmitQuestion}
                onReset={resetChat}
                onSearchEvidence={handleSearchEvidence}
              />
            </div>

            <aside
              className="side-stack workspace-aside"
              aria-label="Active database and retrieval evidence"
            >
              <section
                className="panel active-library-panel"
                aria-labelledby="active-library-title"
              >
                <div className="panel__header">
                  <div>
                    <p className="eyebrow">Library scope</p>
                    <h2 id="active-library-title">{activeLibrary?.name ?? "Research database"}</h2>
                    <p>{apiStatus.detail}</p>
                    <p className="small-muted">
                      {activeLibraryGroups.length} paper groups in this local database.
                    </p>
                  </div>
                </div>
                <div className="panel__body">
                  <PaperLibrary papers={activeLibraryPapers} embedded />
                </div>
              </section>
              <EvidencePanel
                evidence={evidence}
                paperTitles={paperTitles}
                note={evidenceNote}
                apiBaseUrl={installSettings.apiBaseUrl}
              />
            </aside>
          </>
        ) : (
          <SettingsView
            modelSettings={settings}
            installSettings={installSettings}
            apiDetail={apiStatus.detail}
            onModelSettingsChange={setSettings}
            onInstallSettingsChange={setInstallSettings}
          />
        )}
      </section>
    </main>
  );
}
