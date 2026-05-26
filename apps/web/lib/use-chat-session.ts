"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { paperMemoryApi } from "@/lib/api";
import type {
  ApiChatRequest,
  ApiPageEvidence,
  ApiWorkspaceMessage,
  ChatMessage,
  Citation,
  EvidenceItem,
  InstallSettings,
  ModelSettings,
  ResearchConversation,
  ResearchLibrary,
} from "@/lib/types";

function mapWorkspaceCitation(c: ApiWorkspaceMessage["citations"][number]): Citation {
  return { paperId: c.paper_id, label: c.label, page: c.page };
}

interface UseChatSessionOptions {
  activeConversation: ResearchConversation | undefined;
  activeLibrary: ResearchLibrary | undefined;
  readyPaperIds: string[];
  settings: ModelSettings;
  installSettings: InstallSettings;
  paperTitles: Record<string, string>;
  isWorkspacePersisted: boolean;
  onMessagesChange: (conversationId: string, messages: ChatMessage[]) => void;
  onPersistMessages: (conversationId: string, messages: ChatMessage[]) => Promise<void>;
}

interface UseChatSessionReturn {
  messages: ChatMessage[];
  question: string;
  setQuestion: (q: string) => void;
  isSubmitting: boolean;
  error: string | null;
  evidence: Array<EvidenceItem | ApiPageEvidence>;
  evidenceNote: string | null;
  submit: () => void;
  reset: () => void;
  searchEvidence: () => void;
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Unknown error.";
}

export function useChatSession({
  activeConversation,
  activeLibrary,
  readyPaperIds,
  settings,
  installSettings,
  paperTitles,
  isWorkspacePersisted,
  onMessagesChange,
  onPersistMessages,
}: UseChatSessionOptions): UseChatSessionReturn {
  const [question, setQuestion] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [evidence, setEvidence] = useState<Array<EvidenceItem | ApiPageEvidence>>([]);
  const [evidenceNote, setEvidenceNote] = useState<string | null>(null);
  const [streamingContent, setStreamingContent] = useState("");

  // Auto-reset when the active conversation or library changes.
  useEffect(() => {
    setEvidence([]);
    setEvidenceNote(
      activeLibrary
        ? `No evidence loaded for ${activeLibrary.name} yet. Search inside this database to populate page evidence.`
        : null,
    );
    setStreamingContent("");
    setQuestion("");
    setError(null);
  }, [activeConversation?.id, activeLibrary?.id]);

  // Merge stored messages with any in-progress streaming content.
  const messages = useMemo<ChatMessage[]>(() => {
    const base = activeConversation?.messages ?? [];
    if (!streamingContent) return base;
    return [
      ...base,
      {
        id: "streaming-assistant",
        role: "assistant" as const,
        content: streamingContent,
        citations: [],
      },
    ];
  }, [activeConversation?.messages, streamingContent]);

  const doSearchEvidence = useCallback(
    async (query: string): Promise<Array<ApiPageEvidence>> => {
      const response = await paperMemoryApi.searchEvidence(
        query,
        readyPaperIds,
        settings.retrievalTopK,
        installSettings.apiBaseUrl,
      );
      setEvidence(response.evidence);
      setEvidenceNote(response.note);
      return response.evidence;
    },
    [readyPaperIds, settings.retrievalTopK, installSettings.apiBaseUrl],
  );

  const submit = useCallback(async () => {
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || isSubmitting) return;

    const conversationId = activeConversation?.id;
    if (!conversationId) {
      setError("Create a conversation inside the active database before asking questions.");
      return;
    }

    const currentMessages = activeConversation?.messages ?? [];
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: trimmedQuestion,
      citations: [],
    };
    const nextUserMessages = [...currentMessages, userMessage];
    onMessagesChange(conversationId, nextUserMessages);
    setQuestion("");
    setError(null);
    setIsSubmitting(true);
    setStreamingContent("");

    const priorMessages = currentMessages.map((m) => ({
      role: m.role as "user" | "assistant",
      content: m.content,
    }));

    // Show a placeholder note while the backend retrieval runs.
    if (readyPaperIds.length > 0) {
      setEvidenceNote("Searching for relevant pages…");
    } else {
      setEvidence([]);
      setEvidenceNote("Conversation mode: no ready papers in the active database.");
    }

    try {
      const chatRequest: ApiChatRequest = {
        question: trimmedQuestion,
        paper_ids: readyPaperIds.length > 0 ? readyPaperIds : undefined,
        top_k: settings.retrievalTopK,
        messages: priorMessages,
        provider: settings.provider,
        base_url: settings.baseUrl.trim() || undefined,
        model: settings.model.trim() || undefined,
        api_key: settings.apiKey || undefined,
        temperature: settings.temperature,
        enable_image_context: settings.useMultimodalContext,
        max_evidence_images: settings.maxEvidenceImages,
        enable_query_rewrite: true,
      };

      const done = await paperMemoryApi.streamChat(
        chatRequest,
        installSettings.apiBaseUrl,
        (token) => {
          setStreamingContent((prev) => prev + token);
        },
        // Early evidence frame: update the panel as soon as retrieval finishes,
        // before the first LLM token arrives.
        (earlyEvidence, earlyNote) => {
          setEvidence(earlyEvidence);
          setEvidenceNote(earlyNote);
        },
      );

      // Final evidence update from the done frame (may differ after retry).
      setEvidence(done.evidence);
      setEvidenceNote(done.note);

      const citations = (done.evidence as ApiPageEvidence[]).slice(0, 4).map((item) => ({
        paperId: item.paper_id,
        label: paperTitles[item.paper_id] ?? item.paper_id,
        page: item.page_number,
      }));

      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: done.answer,
        citations,
      };

      let nextMessages = [...nextUserMessages, assistantMessage];

      // If the backend produced a conversation summary (history exceeded the
      // context window), prepend it so future turns retain earlier conclusions.
      if (done.summary_message) {
        const sm = done.summary_message;
        const summaryMsg: ChatMessage = {
          id: sm.id,
          role: sm.role as "user" | "assistant",
          content: sm.content,
          citations: sm.citations.map(mapWorkspaceCitation),
        };
        nextMessages = [summaryMsg, ...nextMessages];
      }

      onMessagesChange(conversationId, nextMessages);
      if (isWorkspacePersisted) {
        await onPersistMessages(conversationId, nextMessages);
      }
    } catch (err) {
      setError(getErrorMessage(err));
      setEvidence([]);
      setEvidenceNote("Chat failed before PaperMemory could return an answer.");
    } finally {
      setStreamingContent("");
      setIsSubmitting(false);
    }
  }, [
    question,
    isSubmitting,
    activeConversation,
    readyPaperIds,
    settings,
    installSettings.apiBaseUrl,
    paperTitles,
    isWorkspacePersisted,
    onMessagesChange,
    onPersistMessages,
  ]);

  const reset = useCallback(() => {
    if (activeConversation) {
      onMessagesChange(activeConversation.id, []);
      if (isWorkspacePersisted) {
        void onPersistMessages(activeConversation.id, []);
      }
    }
    setEvidence([]);
    setEvidenceNote(
      activeLibrary
        ? `No evidence loaded for ${activeLibrary.name} yet. Search inside this database to populate page evidence.`
        : null,
    );
    setError(null);
    setQuestion("");
    setStreamingContent("");
  }, [activeConversation, activeLibrary, isWorkspacePersisted, onMessagesChange, onPersistMessages]);

  const searchEvidence = useCallback(async () => {
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion) return;

    if (readyPaperIds.length === 0) {
      const msg = `No ready papers in ${activeLibrary?.name ?? "the active database"}. Upload and index a PDF before searching.`;
      setEvidence([]);
      setEvidenceNote(msg);
      setError(msg);
      return;
    }

    setError(null);
    try {
      await doSearchEvidence(trimmedQuestion);
    } catch (err) {
      setEvidence([]);
      setEvidenceNote(getErrorMessage(err));
      setError(getErrorMessage(err));
    }
  }, [question, readyPaperIds, activeLibrary, doSearchEvidence]);

  return {
    messages,
    question,
    setQuestion,
    isSubmitting,
    error,
    evidence,
    evidenceNote,
    submit,
    reset,
    searchEvidence,
  };
}
