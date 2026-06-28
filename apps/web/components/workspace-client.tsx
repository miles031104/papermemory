"use client";

import { useEffect, useMemo, useState } from "react";

import { ChatView } from "@/components/chat-view";
import { HomeView } from "@/components/home-view";
import { PaperManagerView } from "@/components/paper-manager-view";
import { PricingView } from "@/components/pricing-view";
import { ResearchSidebar } from "@/components/research-sidebar";
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
  WorkspaceView,
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
const DEFAULT_GROUP_NAME = "Ungrouped uploads";
const DEFAULT_GROUP_DESCRIPTION = "Default local-first group for papers that have not been organized yet.";

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
    reliability_report: message.reliability_report ?? null,
  };
}

function mapMessageToApi(message: ChatMessage): ApiWorkspaceMessage {
  return {
    id: message.id,
    role: message.role,
    content: message.content,
    citations: message.citations.map(mapCitationToApi),
    reliability_report: message.reliability_report ?? null,
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
  const [activeGroupId, setActiveGroupId] = useState(mockPaperGroups[0]?.id ?? "");
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
  const [activeView, setActiveView] = useState<WorkspaceView>("home");

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

  const activeLibraryGroups = useMemo(
    () => paperGroups.filter((group) => group.libraryId === activeLibrary?.id),
    [activeLibrary?.id, paperGroups],
  );

  const activeGroup = useMemo(
    () =>
      activeLibraryGroups.find((group) => group.id === activeGroupId) ??
      activeLibraryGroups[0],
    [activeGroupId, activeLibraryGroups],
  );

  const activeGroupPapers = useMemo(() => {
    const paperIds = new Set(activeGroup?.paperIds ?? []);
    return activeLibraryPapers.filter((paper) => paperIds.has(paper.id));
  }, [activeGroup?.paperIds, activeLibraryPapers]);

  const readyPaperIds = useMemo(
    () =>
      activeGroupPapers.filter((paper) => paper.status === "ready").map((paper) => paper.id),
    [activeGroupPapers],
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
    evidencePacket,
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
    let defaultGroup: PaperGroup | null = null;

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
      const groupId = `group-${Date.now()}`;
      library = {
        id: `library-${Date.now()}`,
        name: trimmedName,
        description: description.trim(),
        paperIds: [],
        groupIds: [groupId],
        createdAt: now,
        updatedAt: now,
      };
      defaultGroup = {
        id: groupId,
        libraryId: library.id,
        name: "Ungrouped uploads",
        description: "Default local-first group for papers that have not been organized yet.",
        paperIds: [],
        createdAt: now,
        updatedAt: now,
      };
      conversation = makeConversation(library.id, "Research chat");
    }

    setLibraries((currentLibraries) => [library, ...currentLibraries]);
    setConversations((currentConversations) => [conversation, ...currentConversations]);
    if (defaultGroup) {
      setPaperGroups((currentGroups) => [defaultGroup, ...currentGroups]);
      setActiveGroupId(defaultGroup.id);
    }
    setActiveLibraryId(library.id);
    setActiveConversationId(conversation.id);
    if (isWorkspacePersisted) {
      await loadWorkspace({ paperId: "", libraryId: library.id });
    }
  };

  const createGroup = async (libraryId: string, name: string, description: string) => {
    if (!libraryId) {
      throw new Error("Select a library before creating a group.");
    }

    if (isWorkspacePersisted) {
      const created = await paperMemoryApi.createPaperGroup(
        libraryId,
        { name: name.trim(), description: description.trim() },
        installSettings.apiBaseUrl,
      );
      const group = mapApiPaperGroup(created);
      setPaperGroups((currentGroups) => [group, ...currentGroups.filter((item) => item.id !== group.id)]);
      setLibraries((currentLibraries) =>
        currentLibraries.map((library) =>
          library.id === libraryId && !library.groupIds.includes(group.id)
            ? { ...library, groupIds: [group.id, ...library.groupIds], updatedAt: group.updatedAt }
            : library,
        ),
      );
      setActiveLibraryId(libraryId);
      setActiveGroupId(group.id);
      return;
    }

    const now = new Date().toISOString();
    const group: PaperGroup = {
      id: `group-${Date.now()}`,
      libraryId,
      name: name.trim(),
      description: description.trim(),
      paperIds: [],
      createdAt: now,
      updatedAt: now,
    };
    setPaperGroups((currentGroups) => [group, ...currentGroups]);
    setLibraries((currentLibraries) =>
      currentLibraries.map((library) =>
        library.id === libraryId
          ? { ...library, groupIds: [group.id, ...library.groupIds], updatedAt: now }
          : library,
      ),
    );
    setActiveLibraryId(libraryId);
    setActiveGroupId(group.id);
  };

  const deleteLibrary = async (libraryId: string) => {
    const nextLibraries = libraries.filter((library) => library.id !== libraryId);
    if (nextLibraries.length === 0) {
      throw new Error("Keep at least one library in the workspace.");
    }

    const nextActiveLibrary = nextLibraries[0];
    if (isWorkspacePersisted) {
      await paperMemoryApi.deleteLibrary(libraryId, installSettings.apiBaseUrl);
      await loadWorkspace({ paperId: "", libraryId: nextActiveLibrary.id });
      return;
    }

    const nextGroups = paperGroups.filter((group) => group.libraryId !== libraryId);
    let nextConversations = conversations.filter((conversation) => conversation.libraryId !== libraryId);
    let nextConversation = nextConversations.find(
      (conversation) => conversation.libraryId === nextActiveLibrary.id,
    );
    if (!nextConversation) {
      nextConversation = makeConversation(nextActiveLibrary.id, "Research chat");
      nextConversations = [nextConversation, ...nextConversations];
    }

    setLibraries(nextLibraries);
    setPaperGroups(nextGroups);
    setConversations(nextConversations);
    setActiveLibraryId(nextActiveLibrary.id);
    setActiveGroupId(nextGroups.find((group) => group.libraryId === nextActiveLibrary.id)?.id ?? "");
    setActiveConversationId(nextConversation.id);
  };

  const deleteGroup = async (groupId: string) => {
    const group = paperGroups.find((item) => item.id === groupId);
    if (!group) {
      return;
    }
    const libraryGroups = paperGroups.filter((item) => item.libraryId === group.libraryId);
    if (libraryGroups.length <= 1) {
      throw new Error("Keep at least one group in this library.");
    }
    if (group.name === DEFAULT_GROUP_NAME) {
      throw new Error("The default ungrouped uploads group stays as the fallback for moved papers.");
    }

    const fallbackGroup = libraryGroups.find((item) => item.name === DEFAULT_GROUP_NAME);
    if (isWorkspacePersisted) {
      await paperMemoryApi.deletePaperGroup(groupId, installSettings.apiBaseUrl);
      await loadWorkspace({ paperId: "", libraryId: group.libraryId, groupId: fallbackGroup?.id });
      return;
    }

    const now = new Date().toISOString();
    const fallbackGroupId = fallbackGroup?.id ?? `group-ungrouped-${Date.now()}`;
    const createdFallbackGroup: PaperGroup | null = fallbackGroup
      ? null
      : {
          id: fallbackGroupId,
          libraryId: group.libraryId,
          name: DEFAULT_GROUP_NAME,
          description: DEFAULT_GROUP_DESCRIPTION,
          paperIds: group.paperIds,
          createdAt: now,
          updatedAt: now,
        };

    setPaperGroups((currentGroups) => {
      const withoutDeleted = currentGroups.filter((item) => item.id !== group.id);
      if (createdFallbackGroup) {
        return [createdFallbackGroup, ...withoutDeleted];
      }
      return withoutDeleted.map((item) =>
        item.id === fallbackGroupId
          ? {
              ...item,
              paperIds: [...group.paperIds, ...item.paperIds.filter((paperId) => !group.paperIds.includes(paperId))],
              updatedAt: now,
            }
          : item,
      );
    });
    setLibraries((currentLibraries) =>
      currentLibraries.map((library) =>
        library.id === group.libraryId
          ? {
              ...library,
              groupIds: [
                fallbackGroupId,
                ...library.groupIds.filter((item) => item !== group.id && item !== fallbackGroupId),
              ],
              updatedAt: now,
            }
          : library,
      ),
    );
    setActiveLibraryId(group.libraryId);
    setActiveGroupId(fallbackGroupId);
  };

  const deleteConversation = async (conversationId: string) => {
    const conversation = conversations.find((item) => item.id === conversationId);
    if (!conversation) {
      return;
    }

    const remainingConversations = conversations.filter((item) => item.id !== conversationId);
    const sameLibraryConversations = remainingConversations.filter(
      (item) => item.libraryId === conversation.libraryId,
    );
    const nextActiveConversation = sameLibraryConversations[0];
    const deletingActiveConversation = activeConversationId === conversationId;

    if (isWorkspacePersisted) {
      await paperMemoryApi.deleteConversation(conversationId, installSettings.apiBaseUrl);
      if (nextActiveConversation) {
        setConversations(remainingConversations);
        if (deletingActiveConversation) {
          setActiveConversationId(nextActiveConversation.id);
        }
        return;
      }

      const created = await paperMemoryApi.createConversation(
        conversation.libraryId,
        {
          title: "Research chat",
          description: "A local chat scoped to this paper database.",
          messages: [],
        },
        installSettings.apiBaseUrl,
      );
      const replacement = mapApiConversation(created);
      setConversations([replacement, ...remainingConversations]);
      setActiveLibraryId(conversation.libraryId);
      setActiveConversationId(replacement.id);
      return;
    }

    if (nextActiveConversation) {
      setConversations(remainingConversations);
      if (deletingActiveConversation) {
        setActiveConversationId(nextActiveConversation.id);
      }
      return;
    }

    const replacement = makeConversation(conversation.libraryId, "Research chat");
    setConversations([replacement, ...remainingConversations]);
    setActiveLibraryId(conversation.libraryId);
    setActiveConversationId(replacement.id);
  };

  const selectLibrary = async (libraryId: string) => {
    const existingConversation = conversations.find(
      (conversation) => conversation.libraryId === libraryId,
    );
    const firstGroup = paperGroups.find((group) => group.libraryId === libraryId);
    setActiveLibraryId(libraryId);
    setActiveGroupId(firstGroup?.id ?? "");

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

  const selectGroup = (groupId: string) => {
    const group = paperGroups.find((item) => item.id === groupId);
    if (!group) {
      return;
    }
    setActiveLibraryId(group.libraryId);
    setActiveGroupId(group.id);
  };

  const loadWorkspace = async (assignment?: { paperId: string; libraryId: string; groupId?: string }) => {
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
      const nextActiveLibraryGroups = mappedGroups.filter((group) => group.libraryId === nextActiveLibraryId);
      const nextActiveGroupId =
        assignment?.groupId && nextActiveLibraryGroups.some((group) => group.id === assignment.groupId)
          ? assignment.groupId
          : nextActiveLibraryGroups.some((group) => group.id === activeGroupId)
            ? activeGroupId
            : (nextActiveLibraryGroups[0]?.id ?? "");
      setActiveLibraryId(nextActiveLibraryId);
      setActiveGroupId(nextActiveGroupId);
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
      const groupId = activeGroup?.id;
      const nextLibraryPaperIds = activeLibrary?.paperIds.includes(uploadedPaper.id)
        ? activeLibrary.paperIds
        : [uploadedPaper.id, ...(activeLibrary?.paperIds ?? [])];
      if (isWorkspacePersisted && groupId) {
        await paperMemoryApi.movePaperToGroup(groupId, uploadedPaper.id, installSettings.apiBaseUrl);
      } else if (isWorkspacePersisted && libraryId) {
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
      if (!isWorkspacePersisted && groupId) {
        setPaperGroups((currentGroups) =>
          currentGroups.map((group) =>
            group.id === groupId
              ? { ...group, paperIds: [uploadedPaper.id, ...group.paperIds], updatedAt: new Date().toISOString() }
              : group,
          ),
        );
      }
      setUploadMessage(response.message);
      setSelectedFile(null);
      setFileInputKey((currentKey) => currentKey + 1);
      setUploadTitle("");
      await loadWorkspace({ paperId: uploadedPaper.id, libraryId, groupId });
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

  const movePaperToGroup = async (paperId: string, groupId: string) => {
    if (!isWorkspacePersisted) {
      const now = new Date().toISOString();
      setPaperGroups((currentGroups) =>
        currentGroups.map((group) => {
          if (group.id === groupId) {
            return { ...group, paperIds: [paperId, ...group.paperIds.filter((id) => id !== paperId)], updatedAt: now };
          }
          if (!group.paperIds.includes(paperId)) {
            return group;
          }
          return { ...group, paperIds: group.paperIds.filter((id) => id !== paperId), updatedAt: now };
        }),
      );
      setActiveGroupId(groupId);
      return;
    }

    const updated = await paperMemoryApi.movePaperToGroup(groupId, paperId, installSettings.apiBaseUrl);
    const updatedGroup = mapApiPaperGroup(updated);
    setPaperGroups((currentGroups) =>
      currentGroups.map((group) => {
        if (group.id === updatedGroup.id) {
          return updatedGroup;
        }
        if (group.libraryId !== updatedGroup.libraryId || !group.paperIds.includes(paperId)) {
          return group;
        }
        return {
          ...group,
          paperIds: group.paperIds.filter((id) => id !== paperId),
          updatedAt: updatedGroup.updatedAt,
        };
      }),
    );
    setLibraries((currentLibraries) =>
      currentLibraries.map((library) =>
        library.id === updatedGroup.libraryId && !library.paperIds.includes(paperId)
          ? { ...library, paperIds: [paperId, ...library.paperIds], updatedAt: updatedGroup.updatedAt }
          : library,
      ),
    );
    setActiveGroupId(updatedGroup.id);
  };

  const deletePaper = async (paperId: string) => {
    const paper = papers.find((item) => item.id === paperId);
    const confirmed = window.confirm(
      `Delete "${paper?.title ?? "this paper"}" from the local library? This removes its PDF, rendered pages, and group references.`,
    );
    if (!confirmed) {
      return;
    }

    if (isWorkspacePersisted) {
      await paperMemoryApi.deletePaper(paperId, installSettings.apiBaseUrl);
      await loadWorkspace();
      return;
    }

    setPapers((currentPapers) => currentPapers.filter((item) => item.id !== paperId));
    setLibraries((currentLibraries) =>
      currentLibraries.map((library) => ({
        ...library,
        paperIds: library.paperIds.filter((id) => id !== paperId),
        updatedAt: new Date().toISOString(),
      })),
    );
    setPaperGroups((currentGroups) =>
      currentGroups.map((group) => ({
        ...group,
        paperIds: group.paperIds.filter((id) => id !== paperId),
        updatedAt: new Date().toISOString(),
      })),
    );
  };

  const handleSelectLibrary = (libraryId: string) => {
    const library = libraries.find((item) => item.id === libraryId);
    void selectLibrary(libraryId).catch((error) => {
      console.error(
        `${library?.name ?? "The database"} is active, but the default conversation could not be created. ${getErrorMessage(error)}`,
      );
    });
  };

  const handleSelectGroup = (groupId: string) => {
    selectGroup(groupId);
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
      <section className="workspace-shell" aria-label="PaperMemory workspace">
        <ResearchSidebar
          libraries={libraries}
          conversations={conversations}
          groups={paperGroups}
          papers={papers}
          activeLibraryId={activeLibrary?.id ?? activeLibraryId}
          activeConversationId={activeConversation?.id ?? activeConversationId}
          activeGroupId={activeGroup?.id ?? activeGroupId}
          activeView={activeView}
          apiLabel={apiStatus.label}
          apiConnection={apiStatus.connection}
          isPersisted={isWorkspacePersisted}
          onViewChange={setActiveView}
          onSelectLibrary={handleSelectLibrary}
          onSelectGroup={handleSelectGroup}
          onSelectConversation={handleSelectConversation}
          onCreateConversation={handleCreateConversation}
          onCreateLibrary={createLibrary}
          onCreateGroup={createGroup}
          onDeleteLibrary={deleteLibrary}
          onDeleteGroup={deleteGroup}
          onDeleteConversation={deleteConversation}
        />

        <div className="workspace-content">
          {activeView === "home" ? (
            <HomeView
              activeLibrary={activeLibrary}
              activeGroup={activeGroup}
              papers={activeLibraryPapers}
              groups={activeLibraryGroups}
              isPersisted={isWorkspacePersisted}
              onViewChange={setActiveView}
            />
          ) : null}
          {activeView === "chat" ? (
            <ChatView
              activeGroup={activeGroup}
              activeGroupPapers={activeGroupPapers}
              messages={messages}
              question={question}
              isSubmitting={isChatSubmitting}
              error={chatError}
              evidence={evidence}
              evidencePacket={evidencePacket}
              evidenceNote={evidenceNote}
              paperTitles={paperTitles}
              apiBaseUrl={installSettings.apiBaseUrl}
              onQuestionChange={setQuestion}
              onSubmit={handleSubmitQuestion}
              onReset={resetChat}
              onSearchEvidence={handleSearchEvidence}
            />
          ) : null}
          {activeView === "papers" ? (
            <PaperManagerView
              activeGroup={activeGroup}
              groups={activeLibraryGroups}
              papers={activeGroupPapers}
              uploadTitle={uploadTitle}
              selectedFile={selectedFile}
              fileInputKey={fileInputKey}
              isUploading={isUploading}
              uploadMessage={uploadMessage}
              uploadError={uploadError}
              onTitleChange={setUploadTitle}
              onFileChange={setSelectedFile}
              onUpload={handleUpload}
              onMovePaper={movePaperToGroup}
              onDeletePaper={deletePaper}
            />
          ) : null}
          {activeView === "plans" ? <PricingView /> : null}
          {activeView === "settings" ? (
            <SettingsView
              modelSettings={settings}
              installSettings={installSettings}
              apiDetail={apiStatus.detail}
              onModelSettingsChange={setSettings}
              onInstallSettingsChange={setInstallSettings}
            />
          ) : null}
        </div>
      </section>
    </main>
  );
}
