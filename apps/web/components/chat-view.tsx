import { ChatPanel } from "@/components/chat-panel";
import { EvidencePanel } from "@/components/evidence-panel";
import type { ApiPageEvidence, ChatMessage, EvidenceItem, PaperGroup, PaperSummary } from "@/lib/types";

interface ChatViewProps {
  activeGroup?: PaperGroup;
  activeGroupPapers: PaperSummary[];
  messages: ChatMessage[];
  question: string;
  isSubmitting: boolean;
  error?: string | null;
  evidence: Array<EvidenceItem | ApiPageEvidence>;
  evidenceNote: string | null;
  paperTitles: Record<string, string>;
  apiBaseUrl: string;
  onQuestionChange: (question: string) => void;
  onSubmit: () => void;
  onReset: () => void;
  onSearchEvidence: () => void;
}

export function ChatView({
  activeGroup,
  activeGroupPapers,
  messages,
  question,
  isSubmitting,
  error,
  evidence,
  evidenceNote,
  paperTitles,
  apiBaseUrl,
  onQuestionChange,
  onSubmit,
  onReset,
  onSearchEvidence,
}: ChatViewProps) {
  const readyCount = activeGroupPapers.filter((paper) => paper.status === "ready").length;
  const pageCount = activeGroupPapers.reduce((total, paper) => total + paper.pages, 0);
  const emptyScopeNote =
    readyCount === 0
      ? "This group has no ready papers yet. Upload and index a PDF before asking paper-grounded questions."
      : null;

  return (
    <section className="workspace-grid workspace-grid--chat" aria-label="Group scoped chat">
      <div className="workspace-main">
        <section className="panel scope-panel" aria-labelledby="scope-title">
          <div className="panel__header">
            <div>
              <p className="eyebrow">Group RAG scope</p>
              <h2 id="scope-title">Chat with: {activeGroup?.name ?? "No group selected"}</h2>
              <p>
                {readyCount} ready paper(s), {pageCount} indexed page(s).
              </p>
            </div>
          </div>
          {emptyScopeNote ? (
            <div className="panel__body">
              <p className="inline-alert inline-alert--warning">{emptyScopeNote}</p>
            </div>
          ) : null}
        </section>
        <ChatPanel
          messages={messages}
          question={question}
          isSubmitting={isSubmitting}
          title={activeGroup ? `Chat with ${activeGroup.name}` : "Research chat"}
          contextLabel="Group-scoped RAG"
          libraryDescription="Questions use only the selected group's ready papers."
          error={error}
          onQuestionChange={onQuestionChange}
          onSubmit={onSubmit}
          onReset={onReset}
          onSearchEvidence={onSearchEvidence}
        />
      </div>
      <aside className="side-stack workspace-aside" aria-label="Retrieved evidence">
        <EvidencePanel evidence={evidence} paperTitles={paperTitles} note={evidenceNote} apiBaseUrl={apiBaseUrl} />
      </aside>
    </section>
  );
}
