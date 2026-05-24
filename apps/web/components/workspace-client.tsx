"use client";

import { useEffect, useMemo, useState } from "react";

import { ChatPanel } from "@/components/chat-panel";
import { EvidencePanel } from "@/components/evidence-panel";
import { PaperLibrary } from "@/components/paper-library";
import { PaperUploadPanel } from "@/components/paper-upload-panel";
import { ResearchSidebar, type WorkspaceView } from "@/components/research-sidebar";
import { SettingsView } from "@/components/settings-view";
import { defaultApiBaseUrl, paperMemoryApi } from "@/lib/api";
import {
  mockConversations,
  mockEvidence,
  mockModelSettings,
  mockPaperGroups,
  mockPapers,
  mockResearchLibraries
} from "@/lib/mock-data";
import type {
  ApiChatResponse,
  ApiPageEvidence,
  ApiPaperMetadata,
  ApiPaperGroup,
  ApiResearchConversation,
  ApiResearchLibrary,
  ApiWorkspaceMessage,
  ChatMessage,
  Citation,
  EvidenceItem,
  InstallSettings,
  ModelSettings,
  PaperGroup,
  PaperStatus,
  PaperSummary,
  ResearchConversation,
  ResearchLibrary
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

function mapApiCitation(citation: { paper_id: string; label: string; page: number }): Citation {
  return {
    paperId: citation.paper_id,
    label: citation.label,
    page: citation.page
  };
}

function mapCitationToApi(citation: Citation) {
  return {
    paper_id: citation.paperId,
    label: citation.label,
    page: citation.page
  };
}

function mapApiWorkspaceMessage(message: ApiWorkspaceMessage): ChatMessage {
  return {
    id: message.id,
    role: message.role,
    content: message.content,
    citations: message.citations.map(mapApiCitation)
  };
}

function mapMessageToApi(message: ChatMessage): ApiWorkspaceMessage {
  return {
    id: message.id,
    role: message.role,
    content: message.content,
    citations: message.citations.map(mapCitationToApi)
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
    updatedAt: library.updated_at
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
    updatedAt: conversation.updated_at
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
    updatedAt: group.updated_at
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
    updatedAt: now
  };
}

function scopedEvidenceNote(libraryName?: string) {
  return libraryName
    ? `No evidence loaded for ${libraryName} yet. Search inside this database to populate page evidence.`
    : "No evidence loaded for this conversation yet. Search inside the active database to populate page evidence.";
}

export function WorkspaceClient() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>({
    connection: "checking",
    label: "Checking API",
    detail: "Probing FastAPI before loading the local library."
  });
  const [libraries, setLibraries] = useState<ResearchLibrary[]>(mockResearchLibraries);
  const [activeLibraryId, setActiveLibraryId] = useState(mockResearchLibraries[0]?.id ?? "");
  const [conversations, setConversations] = useState<ResearchConversation[]>(mockConversations);
  const [activeConversationId, setActiveConversationId] = useState(mockConversations[0]?.id ?? "");
  const [paperGroups, setPaperGroups] = useState<PaperGroup[]>(mockPaperGroups);
  const [isWorkspacePersisted, setIsWorkspacePersisted] = useState(false);
  const [papers, setPapers] = useState<PaperSummary[]>(mockPapers);
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
  const [activeView, setActiveView] = useState<WorkspaceView>("research");

  const paperTitles = useMemo(
    () => Object.fromEntries(papers.map((paper) => [paper.id, paper.title])),
    [papers]
  );

  const activeLibrary = useMemo(
    () => libraries.find((library) => library.id === activeLibraryId) ?? libraries[0],
    [activeLibraryId, libraries]
  );

  const activeConversation = useMemo(
    () => {
      const activeLibraryConversations = conversations.filter(
        (conversation) => conversation.libraryId === activeLibrary?.id
      );
      return (
        activeLibraryConversations.find((conversation) => conversation.id === activeConversationId) ??
        activeLibraryConversations[0]
      );
    },
    [activeConversationId, activeLibrary?.id, conversations]
  );

  const messages = activeConversation?.messages ?? [];

  const activeLibraryPapers = useMemo(() => {
    const paperIds = new Set(activeLibrary?.paperIds ?? []);
    return papers.filter((paper) => paperIds.has(paper.id));
  }, [activeLibrary?.paperIds, papers]);

  const readyPaperIds = useMemo(
    () => activeLibraryPapers.filter((paper) => paper.status === "ready").map((paper) => paper.id),
    [activeLibraryPapers]
  );

  const activeLibraryGroups = useMemo(
    () => paperGroups.filter((group) => group.libraryId === activeLibrary?.id),
    [activeLibrary?.id, paperGroups]
  );

  const setConversationMessages = (conversationId: string, nextMessages: ChatMessage[]) => {
    const now = new Date().toISOString();

    setConversations((currentConversations) =>
      currentConversations.map((conversation) =>
        conversation.id === conversationId
          ? { ...conversation, messages: nextMessages, updatedAt: now }
          : conversation
      )
    );
  };

  const replaceConversation = (conversation: ResearchConversation) => {
    setConversations((currentConversations) => {
      const exists = currentConversations.some((item) => item.id === conversation.id);
      if (!exists) {
        return [conversation, ...currentConversations];
      }
      return currentConversations.map((item) => (item.id === conversation.id ? conversation : item));
    });
  };

  const persistConversationMessages = async (conversationId: string, nextMessages: ChatMessage[]) => {
    if (!isWorkspacePersisted) {
      return;
    }

    const updated = await paperMemoryApi.updateConversation(
      conversationId,
      { messages: nextMessages.map(mapMessageToApi) },
      installSettings.apiBaseUrl
    );
    replaceConversation(mapApiConversation(updated));
  };

  const createConversation = async (libraryId = activeLibrary?.id ?? activeLibraryId) => {
    if (!libraryId) {
      return;
    }

    let conversation = makeConversation(libraryId);
    if (isWorkspacePersisted) {
      const created = await paperMemoryApi.createConversation(
        libraryId,
        {
          title: conversation.title,
          description: conversation.description,
          messages: []
        },
        installSettings.apiBaseUrl
      );
      conversation = mapApiConversation(created);
    }

    setConversations((currentConversations) => [conversation, ...currentConversations]);
    setActiveLibraryId(libraryId);
    setActiveConversationId(conversation.id);
    setQuestion("");
    setChatError(null);
    setEvidence([]);
    setEvidenceNote(scopedEvidenceNote(activeLibrary?.name));
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
          description: description.trim()
        },
        installSettings.apiBaseUrl
      );
      library = mapApiLibrary(createdLibrary);

      try {
        const createdConversation = await paperMemoryApi.createConversation(
          library.id,
          {
            title: "Research chat",
            description: "A local chat scoped to this paper database.",
            messages: []
          },
          installSettings.apiBaseUrl
        );
        conversation = mapApiConversation(createdConversation);
      } catch (error) {
        setLibraries((currentLibraries) => [library, ...currentLibraries.filter((item) => item.id !== library.id)]);
        setActiveLibraryId(library.id);
        setActiveConversationId("");
        setQuestion("");
        setEvidence([]);
        setEvidenceNote(scopedEvidenceNote(library.name));
        setChatError(
          `${library.name} was created, but the default conversation could not be created. Use + in Conversations to retry. ${getErrorMessage(error)}`
        );
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
        updatedAt: now
      };
      conversation = makeConversation(library.id, "Research chat");
    }

    setLibraries((currentLibraries) => [library, ...currentLibraries]);
    setConversations((currentConversations) => [conversation, ...currentConversations]);
    setActiveLibraryId(library.id);
    setActiveConversationId(conversation.id);
    setQuestion("");
    setChatError(null);
    setEvidence([]);
    setEvidenceNote(scopedEvidenceNote(library.name));
  };

  const selectLibrary = async (libraryId: string) => {
    const existingConversation = conversations.find((conversation) => conversation.libraryId === libraryId);
    setActiveLibraryId(libraryId);

    if (existingConversation) {
      setActiveConversationId(existingConversation.id);
      setQuestion("");
      setChatError(null);
      return;
    }

    setActiveConversationId("");
    setQuestion("");
    setChatError(null);

    let conversation = makeConversation(libraryId);
    if (isWorkspacePersisted) {
      const created = await paperMemoryApi.createConversation(
        libraryId,
        {
          title: conversation.title,
          description: conversation.description,
          messages: []
        },
        installSettings.apiBaseUrl
      );
      conversation = mapApiConversation(created);
    }
    setConversations((currentConversations) => [conversation, ...currentConversations]);
    setActiveConversationId(conversation.id);
    setQuestion("");
    setChatError(null);
  };

  const loadWorkspace = async (assignment?: { paperId: string; libraryId: string }) => {
    setApiStatus({
      connection: "checking",
      label: "Checking API",
      detail: "Refreshing health and paper metadata."
    });

    try {
      const [health, paperList, workspace] = await Promise.all([
        paperMemoryApi.health(installSettings.apiBaseUrl),
        paperMemoryApi.listPapers(installSettings.apiBaseUrl),
        paperMemoryApi.getWorkspace(installSettings.apiBaseUrl)
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
        assignment?.libraryId && mappedLibraries.some((library) => library.id === assignment.libraryId)
          ? assignment.libraryId
          : mappedLibraries.some((library) => library.id === activeLibraryId)
            ? activeLibraryId
            : mappedLibraries[0]?.id ?? "";
      const nextConversation = assignment?.libraryId
        ? mappedConversations.find((conversation) => conversation.libraryId === nextActiveLibraryId)
        : mappedConversations.find(
            (conversation) =>
              conversation.id === activeConversationId && conversation.libraryId === nextActiveLibraryId
          ) ??
          mappedConversations.find((conversation) => conversation.libraryId === nextActiveLibraryId);
      setActiveLibraryId(nextActiveLibraryId);
      setActiveConversationId(nextConversation?.id ?? "");
      const nextActiveLibrary = mappedLibraries.find((library) => library.id === nextActiveLibraryId);
      setEvidence([]);
      setEvidenceNote(scopedEvidenceNote(nextActiveLibrary?.name));
      setApiStatus({
        connection: "online",
        label: "API online",
        detail: `${health.service} ${health.version} at ${health.storage_root}`
      });
    } catch (error) {
      setPapers(mockPapers);
      setLibraries((currentLibraries) => (currentLibraries.length > 0 ? currentLibraries : mockResearchLibraries));
      setConversations((currentConversations) =>
        currentConversations.length > 0 ? currentConversations : mockConversations
      );
      setPaperGroups(mockPaperGroups);
      setIsWorkspacePersisted(false);
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
    if (readyPaperIds.length === 0) {
      const message = `No ready papers in ${activeLibrary?.name ?? "the active database"}. Upload and index a PDF before searching.`;
      setEvidence([]);
      setEvidenceNote(message);
      throw new Error(message);
    }

    const response = await paperMemoryApi.searchEvidence(
      query,
      readyPaperIds,
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
      const uploadedPaper = mapApiPaper(response.paper);
      const libraryId = activeLibrary?.id ?? activeLibraryId;
      const nextLibraryPaperIds = activeLibrary?.paperIds.includes(uploadedPaper.id)
        ? activeLibrary.paperIds
        : [uploadedPaper.id, ...(activeLibrary?.paperIds ?? [])];
      if (isWorkspacePersisted && libraryId) {
        await paperMemoryApi.updateLibrary(
          libraryId,
          { paper_ids: nextLibraryPaperIds },
          installSettings.apiBaseUrl
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
            : library
        )
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
      setEvidence([]);
      setEvidenceNote(getErrorMessage(error));
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

    if (!activeConversation) {
      setChatError("Create a conversation inside the active database before asking questions.");
      return;
    }

    const nextUserMessages = [...messages, userMessage];
    setConversationMessages(activeConversation.id, nextUserMessages);
    setQuestion("");
    setChatError(null);
    setIsChatSubmitting(true);

    let chatPaperIds = readyPaperIds;
    let fallbackEvidenceNote: string | null = null;

    try {
      if (readyPaperIds.length > 0) {
        try {
          await searchEvidence(trimmedQuestion);
        } catch (error) {
          chatPaperIds = [];
          fallbackEvidenceNote = `Conversation mode: retrieval failed for the active paper scope, so this answer is not paper-grounded. ${getErrorMessage(error)}`;
          setEvidence([]);
          setEvidenceNote(fallbackEvidenceNote);
        }
      } else {
        setEvidence([]);
        setEvidenceNote("Conversation mode: no ready papers are scoped for retrieval in this database.");
      }

      const response: ApiChatResponse = await paperMemoryApi.createChat({
        question: trimmedQuestion,
        paper_ids: chatPaperIds,
        top_k: settings.retrievalTopK,
        messages: priorMessages,
        provider: settings.provider,
        base_url: settings.baseUrl.trim() || undefined,
        model: settings.model.trim() || undefined,
        api_key: settings.apiKey || undefined,
        temperature: settings.temperature,
        enable_image_context: settings.useMultimodalContext,
        max_evidence_images: settings.maxEvidenceImages
      }, installSettings.apiBaseUrl);

      setEvidence(response.evidence);
      setEvidenceNote(fallbackEvidenceNote ?? response.note);
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: response.answer,
        citations: citationsFromEvidence(response.evidence, paperTitles)
      };
      const nextMessages: ChatMessage[] = [...nextUserMessages, assistantMessage];
      setConversationMessages(activeConversation.id, nextMessages);
      await persistConversationMessages(activeConversation.id, nextMessages);
      setApiStatus((currentStatus) => ({
        ...currentStatus,
        connection: "online",
        label: "API online"
      }));
    } catch (error) {
      setChatError(getErrorMessage(error));
      setEvidence([]);
      setEvidenceNote("Chat failed before PaperMemory could return an answer for this conversation.");
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
    if (activeConversation) {
      setConversationMessages(activeConversation.id, []);
      void persistConversationMessages(activeConversation.id, []);
    }
    setEvidence([]);
    setEvidenceNote(scopedEvidenceNote(activeLibrary?.name));
    setChatError(null);
    setQuestion("");
  };

  const handleSelectLibrary = (libraryId: string) => {
    const library = libraries.find((item) => item.id === libraryId);
    void selectLibrary(libraryId).catch((error) => {
      setChatError(
        `${library?.name ?? "The database"} is active, but the default conversation could not be created. Use + in Conversations to retry. ${getErrorMessage(error)}`
      );
    });
    setEvidence([]);
    setEvidenceNote(scopedEvidenceNote(library?.name));
  };

  const handleSelectConversation = (conversationId: string) => {
    setActiveConversationId(conversationId);
    setQuestion("");
    setChatError(null);
    setEvidence([]);
    setEvidenceNote(scopedEvidenceNote(activeLibrary?.name));
  };

  const handleCreateConversation = () => {
    void createConversation().catch((error) => {
      setChatError(getErrorMessage(error));
    });
    setEvidence([]);
    setEvidenceNote(scopedEvidenceNote(activeLibrary?.name));
  };

  return (
    <main className="app-shell">
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
                libraryDescription={activeLibrary?.description ?? "Ask questions over the active paper database."}
                error={chatError}
                onQuestionChange={setQuestion}
                onSubmit={handleSubmitQuestion}
                onReset={resetChat}
                onSearchEvidence={handleSearchEvidence}
              />
            </div>

            <aside className="side-stack workspace-aside" aria-label="Active database and retrieval evidence">
              <section className="panel active-library-panel" aria-labelledby="active-library-title">
                <div className="panel__header">
                  <div>
                    <p className="eyebrow">Active database</p>
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
