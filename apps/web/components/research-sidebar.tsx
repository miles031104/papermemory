import { type FormEvent, useState } from "react";

import type { PaperSummary, ResearchConversation, ResearchLibrary } from "@/lib/types";

interface ResearchSidebarProps {
  libraries: ResearchLibrary[];
  conversations: ResearchConversation[];
  papers: PaperSummary[];
  activeLibraryId: string;
  activeConversationId: string;
  apiLabel: string;
  apiConnection: "checking" | "online" | "offline";
  isPersisted: boolean;
  onSelectLibrary: (libraryId: string) => void;
  onSelectConversation: (conversationId: string) => void;
  onCreateConversation: () => void;
  onCreateLibrary: (name: string, description: string) => Promise<void>;
}

function formatTime(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Recent";
  }

  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric"
  }).format(date);
}

export function ResearchSidebar({
  libraries,
  conversations,
  papers,
  activeLibraryId,
  activeConversationId,
  apiLabel,
  apiConnection,
  isPersisted,
  onSelectLibrary,
  onSelectConversation,
  onCreateConversation,
  onCreateLibrary
}: ResearchSidebarProps) {
  const [isCreatingDatabase, setIsCreatingDatabase] = useState(false);
  const [databaseName, setDatabaseName] = useState("");
  const [databaseDescription, setDatabaseDescription] = useState("");
  const [isSubmittingDatabase, setIsSubmittingDatabase] = useState(false);
  const [databaseError, setDatabaseError] = useState<string | null>(null);
  const paperCountByLibrary = Object.fromEntries(
    libraries.map((library) => [
      library.id,
      library.paperIds.filter((paperId) => papers.some((paper) => paper.id === paperId)).length
    ])
  );
  const visibleConversations = conversations.filter(
    (conversation) => conversation.libraryId === activeLibraryId
  );

  const handleSubmitDatabase = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedName = databaseName.trim();
    if (!trimmedName) {
      setDatabaseError("Name is required.");
      return;
    }

    setIsSubmittingDatabase(true);
    setDatabaseError(null);
    try {
      await onCreateLibrary(trimmedName, databaseDescription.trim());
      setDatabaseName("");
      setDatabaseDescription("");
      setIsCreatingDatabase(false);
    } catch (error) {
      setDatabaseError(error instanceof Error ? error.message : "Could not create database.");
    } finally {
      setIsSubmittingDatabase(false);
    }
  };

  return (
    <aside className="research-sidebar" aria-label="Research databases and conversations">
      <div className="sidebar-brand">
        <div>
          <p className="eyebrow">PaperMemory</p>
          <h1>Research Workspace</h1>
        </div>
        <div className="sidebar-status" aria-label="API status">
          <span className={`status-dot status-dot--${apiConnection}`} aria-hidden="true" />
          <span>{apiLabel}</span>
        </div>
      </div>

      <nav className="sidebar-section" aria-labelledby="database-title">
        <div className="sidebar-section__header">
          <h2 id="database-title">Databases</h2>
          <button
            className="icon-button"
            type="button"
            aria-label="Create database"
            aria-expanded={isCreatingDatabase}
            onClick={() => {
              setIsCreatingDatabase((current) => !current);
              setDatabaseError(null);
            }}
          >
            +
          </button>
        </div>
        {isCreatingDatabase ? (
          <form className="sidebar-create-form" onSubmit={handleSubmitDatabase}>
            <label>
              <span>Name</span>
              <input
                autoFocus
                maxLength={120}
                placeholder="New research database"
                value={databaseName}
                onChange={(event) => setDatabaseName(event.target.value)}
              />
            </label>
            <label>
              <span>Description</span>
              <textarea
                maxLength={500}
                placeholder="Optional scope or project note"
                rows={2}
                value={databaseDescription}
                onChange={(event) => setDatabaseDescription(event.target.value)}
              />
            </label>
            {databaseError ? <p className="inline-alert inline-alert--error">{databaseError}</p> : null}
            <div className="sidebar-create-form__actions">
              <button
                className="button button--subtle"
                type="button"
                onClick={() => {
                  setIsCreatingDatabase(false);
                  setDatabaseError(null);
                }}
              >
                Cancel
              </button>
              <button className="button button--primary" type="submit" disabled={isSubmittingDatabase}>
                {isSubmittingDatabase ? "Creating" : "Create"}
              </button>
            </div>
          </form>
        ) : null}
        <div className="sidebar-list" role="list">
          {libraries.map((library) => {
            const isActive = library.id === activeLibraryId;

            return (
              <button
                className={`sidebar-item${isActive ? " sidebar-item--active" : ""}`}
                key={library.id}
                type="button"
                onClick={() => onSelectLibrary(library.id)}
              >
                <span className="sidebar-item__title">{library.name}</span>
                <span className="sidebar-item__meta">
                  {paperCountByLibrary[library.id] ?? 0} papers
                </span>
              </button>
            );
          })}
        </div>
      </nav>

      <nav className="sidebar-section sidebar-section--grow" aria-labelledby="conversation-title">
        <div className="sidebar-section__header">
          <h2 id="conversation-title">Conversations</h2>
          <button className="icon-button" type="button" aria-label="New conversation" onClick={onCreateConversation}>
            +
          </button>
        </div>
        <div className="sidebar-list" role="list">
          {visibleConversations.length === 0 ? (
            <p className="small-muted">Create a conversation inside this database.</p>
          ) : null}
          {visibleConversations.map((conversation) => {
            const isActive = conversation.id === activeConversationId;

            return (
              <button
                className={`sidebar-item sidebar-item--conversation${
                  isActive ? " sidebar-item--active" : ""
                }`}
                key={conversation.id}
                type="button"
                onClick={() => onSelectConversation(conversation.id)}
              >
                <span className="sidebar-item__title">{conversation.title}</span>
                <span className="sidebar-item__meta">{formatTime(conversation.updatedAt)}</span>
              </button>
            );
          })}
        </div>
      </nav>

      <div className="library-entry">
        <p className={`inline-alert ${isPersisted ? "inline-alert--success" : "inline-alert--warning"}`}>
          {isPersisted
            ? "Databases and conversations are stored in the local JSON workspace."
            : "Showing mock workspace data. Offline database changes are temporary."}
        </p>
        <button className="button button--subtle" type="button" disabled>
          Papers manager
        </button>
        <p className="small-muted">
          Future page for paper groups, title/author metadata, and generated idea cards.
        </p>
      </div>
    </aside>
  );
}
