import { type FormEvent, useMemo, useState } from "react";

import type {
  PaperGroup,
  PaperSummary,
  ResearchConversation,
  ResearchLibrary,
  WorkspaceView,
} from "@/lib/types";

interface ResearchSidebarProps {
  libraries: ResearchLibrary[];
  conversations: ResearchConversation[];
  groups: PaperGroup[];
  papers: PaperSummary[];
  activeLibraryId: string;
  activeConversationId: string;
  activeGroupId: string;
  activeView: WorkspaceView;
  apiLabel: string;
  apiConnection: "checking" | "online" | "offline";
  isPersisted: boolean;
  onViewChange: (view: WorkspaceView) => void;
  onSelectLibrary: (libraryId: string) => void;
  onSelectGroup: (groupId: string) => void;
  onSelectConversation: (conversationId: string) => void;
  onCreateConversation: () => void;
  onCreateLibrary: (name: string, description: string) => Promise<void>;
  onCreateGroup: (libraryId: string, name: string, description: string) => Promise<void>;
}

const workspaceViews: Array<{ id: WorkspaceView; label: string }> = [
  { id: "home", label: "Home" },
  { id: "chat", label: "Chat" },
  { id: "papers", label: "Paper Manager" },
  { id: "settings", label: "Settings" },
];

function formatTime(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Recent";
  }

  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
  }).format(date);
}

export function ResearchSidebar({
  libraries,
  conversations,
  groups,
  papers,
  activeLibraryId,
  activeConversationId,
  activeGroupId,
  activeView,
  apiLabel,
  apiConnection,
  isPersisted,
  onViewChange,
  onSelectLibrary,
  onSelectGroup,
  onSelectConversation,
  onCreateConversation,
  onCreateLibrary,
  onCreateGroup,
}: ResearchSidebarProps) {
  const [isCreatingDatabase, setIsCreatingDatabase] = useState(false);
  const [databaseName, setDatabaseName] = useState("");
  const [databaseDescription, setDatabaseDescription] = useState("");
  const [isSubmittingDatabase, setIsSubmittingDatabase] = useState(false);
  const [databaseError, setDatabaseError] = useState<string | null>(null);
  const [isCreatingGroup, setIsCreatingGroup] = useState(false);
  const [groupName, setGroupName] = useState("");
  const [groupDescription, setGroupDescription] = useState("");
  const [isSubmittingGroup, setIsSubmittingGroup] = useState(false);
  const [groupError, setGroupError] = useState<string | null>(null);

  const paperCountByLibrary = useMemo(
    () =>
      Object.fromEntries(
        libraries.map((library) => [
          library.id,
          library.paperIds.filter((paperId) => papers.some((paper) => paper.id === paperId)).length,
        ]),
      ),
    [libraries, papers],
  );

  const paperCountByGroup = useMemo(
    () =>
      Object.fromEntries(
        groups.map((group) => [
          group.id,
          group.paperIds.filter((paperId) => papers.some((paper) => paper.id === paperId)).length,
        ]),
      ),
    [groups, papers],
  );

  const groupsByLibrary = useMemo(
    () =>
      Object.fromEntries(
        libraries.map((library) => [
          library.id,
          groups.filter((group) => group.libraryId === library.id),
        ]),
      ),
    [groups, libraries],
  );

  const visibleConversations = conversations.filter(
    (conversation) => conversation.libraryId === activeLibraryId,
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

  const handleSubmitGroup = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedName = groupName.trim();
    if (!activeLibraryId) {
      setGroupError("Select a library first.");
      return;
    }
    if (!trimmedName) {
      setGroupError("Name is required.");
      return;
    }

    setIsSubmittingGroup(true);
    setGroupError(null);
    try {
      await onCreateGroup(activeLibraryId, trimmedName, groupDescription.trim());
      setGroupName("");
      setGroupDescription("");
      setIsCreatingGroup(false);
    } catch (error) {
      setGroupError(error instanceof Error ? error.message : "Could not create group.");
    } finally {
      setIsSubmittingGroup(false);
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

      <div className="sidebar-view-nav" role="tablist" aria-label="Workspace views">
        {workspaceViews.map((view) => (
          <button
            className={`sidebar-view-nav__item${activeView === view.id ? " sidebar-view-nav__item--active" : ""}`}
            type="button"
            role="tab"
            aria-selected={activeView === view.id}
            onClick={() => onViewChange(view.id)}
            key={view.id}
          >
            {view.label}
          </button>
        ))}
      </div>

      <nav className="sidebar-section" aria-labelledby="database-title">
        <div className="sidebar-section__header">
          <h2 id="database-title">Libraries</h2>
          <button
            className="icon-button"
            type="button"
            aria-label="Create library"
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
                placeholder="New research library"
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
            const libraryGroups = groupsByLibrary[library.id] ?? [];

            return (
              <div className="sidebar-tree-node" key={library.id}>
                <button
                  className={`sidebar-item${isActive ? " sidebar-item--active" : ""}`}
                  type="button"
                  onClick={() => onSelectLibrary(library.id)}
                >
                  <span className="sidebar-item__title">{library.name}</span>
                  <span className="sidebar-item__meta">
                    {paperCountByLibrary[library.id] ?? 0} papers
                  </span>
                </button>
                {libraryGroups.map((group) => (
                  <button
                    className={`sidebar-item sidebar-item--group${
                      group.id === activeGroupId ? " sidebar-item--active" : ""
                    }`}
                    type="button"
                    key={group.id}
                    onClick={() => onSelectGroup(group.id)}
                  >
                    <span className="sidebar-item__title">{group.name}</span>
                    <span className="sidebar-item__meta">{paperCountByGroup[group.id] ?? 0}</span>
                  </button>
                ))}
              </div>
            );
          })}
        </div>
      </nav>

      <nav className="sidebar-section" aria-labelledby="group-title">
        <div className="sidebar-section__header">
          <h2 id="group-title">Groups</h2>
          <button
            className="icon-button"
            type="button"
            aria-label="Create group"
            aria-expanded={isCreatingGroup}
            onClick={() => {
              setIsCreatingGroup((current) => !current);
              setGroupError(null);
            }}
          >
            +
          </button>
        </div>
        {isCreatingGroup ? (
          <form className="sidebar-create-form" onSubmit={handleSubmitGroup}>
            <label>
              <span>Name</span>
              <input
                autoFocus
                maxLength={120}
                placeholder="Related papers"
                value={groupName}
                onChange={(event) => setGroupName(event.target.value)}
              />
            </label>
            <label>
              <span>Description</span>
              <textarea
                maxLength={500}
                placeholder="Optional group note"
                rows={2}
                value={groupDescription}
                onChange={(event) => setGroupDescription(event.target.value)}
              />
            </label>
            {groupError ? <p className="inline-alert inline-alert--error">{groupError}</p> : null}
            <div className="sidebar-create-form__actions">
              <button
                className="button button--subtle"
                type="button"
                onClick={() => {
                  setIsCreatingGroup(false);
                  setGroupError(null);
                }}
              >
                Cancel
              </button>
              <button className="button button--primary" type="submit" disabled={isSubmittingGroup}>
                {isSubmittingGroup ? "Creating" : "Create"}
              </button>
            </div>
          </form>
        ) : null}
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
            <p className="small-muted">Create a conversation inside this library.</p>
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
            ? "Workspace data is stored in the local JSON workspace."
            : "Showing mock workspace data. Offline changes are temporary."}
        </p>
      </div>
    </aside>
  );
}
