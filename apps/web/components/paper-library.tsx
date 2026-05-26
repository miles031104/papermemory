import { StatusBadge } from "@/components/status-badge";
import type { PaperGroup, PaperSummary } from "@/lib/types";

type PaperLibraryViewMode = "cards" | "table";

interface PaperLibraryProps {
  papers: PaperSummary[];
  embedded?: boolean;
  groups?: PaperGroup[];
  activeGroupId?: string;
  viewMode?: PaperLibraryViewMode;
  selectedPaperId?: string;
  onSelectPaper?: (paperId: string) => void;
  onMovePaper?: (paperId: string, groupId: string) => Promise<void>;
  onDeletePaper?: (paperId: string) => Promise<void>;
}

function PaperMoveControl({
  paper,
  groups,
  activeGroupId,
  compact = false,
  onMovePaper,
}: {
  paper: PaperSummary;
  groups: PaperGroup[];
  activeGroupId: string;
  compact?: boolean;
  onMovePaper?: (paperId: string, groupId: string) => Promise<void>;
}) {
  if (!onMovePaper || groups.length === 0) {
    return null;
  }

  return (
    <label className={`paper-move-control ${compact ? "paper-move-control--compact" : ""}`}>
      <span>{compact ? "Group" : "Move group"}</span>
      <select
        value={activeGroupId}
        onClick={(event) => event.stopPropagation()}
        onChange={(event) => {
          const nextGroupId = event.target.value;
          if (nextGroupId && nextGroupId !== activeGroupId) {
            void onMovePaper(paper.id, nextGroupId);
          }
        }}
      >
        {groups.map((group) => (
          <option value={group.id} key={group.id}>
            {group.name}
          </option>
        ))}
      </select>
    </label>
  );
}

function PaperDeleteButton({
  paper,
  compact = false,
  onDeletePaper,
}: {
  paper: PaperSummary;
  compact?: boolean;
  onDeletePaper?: (paperId: string) => Promise<void>;
}) {
  if (!onDeletePaper) {
    return null;
  }

  return (
    <button
      className={`button button--danger paper-delete-button ${
        compact ? "paper-delete-button--compact" : ""
      }`}
      type="button"
      onClick={(event) => {
        event.stopPropagation();
        void onDeletePaper(paper.id);
      }}
    >
      Delete
    </button>
  );
}

function PaperLibraryBody({
  papers,
  groups = [],
  activeGroupId = "",
  viewMode = "cards",
  selectedPaperId,
  onSelectPaper,
  onMovePaper,
  onDeletePaper,
}: {
  papers: PaperSummary[];
  groups?: PaperGroup[];
  activeGroupId?: string;
  viewMode?: PaperLibraryViewMode;
  selectedPaperId?: string;
  onSelectPaper?: (paperId: string) => void;
  onMovePaper?: (paperId: string, groupId: string) => Promise<void>;
  onDeletePaper?: (paperId: string) => Promise<void>;
}) {
  if (papers.length === 0) {
    return <p className="small-muted">No papers in this database yet.</p>;
  }

  if (viewMode === "table") {
    return (
      <div className="paper-table-wrap">
        <table className="paper-table" aria-label="Paper library table">
          <thead>
            <tr>
              <th scope="col">Paper</th>
              <th scope="col">Authors</th>
              <th scope="col">Year</th>
              <th scope="col">Pages</th>
              <th scope="col">Status</th>
              <th scope="col">Index</th>
              <th scope="col">Group</th>
              <th scope="col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {papers.map((paper) => (
              <tr
                className={paper.id === selectedPaperId ? "paper-table__row--active" : ""}
                key={paper.id}
                onClick={() => onSelectPaper?.(paper.id)}
              >
                <td className="paper-table__title-cell">
                  <button
                    className="paper-table__title-button"
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      onSelectPaper?.(paper.id);
                    }}
                  >
                    {paper.title}
                  </button>
                  <span>{paper.indexSummary}</span>
                </td>
                <td className="paper-table__muted">{paper.authors.join(", ") || "Unknown"}</td>
                <td>{paper.year}</td>
                <td>{paper.pages}</td>
                <td>
                  <StatusBadge status={paper.status} />
                </td>
                <td>
                  <div className="paper-table__progress">
                    <div className="progress-track" aria-label={`${paper.title} index progress`}>
                      <div className="progress-bar" style={{ width: `${paper.progress}%` }} />
                    </div>
                    <span>{paper.progress}%</span>
                  </div>
                </td>
                <td>
                  <PaperMoveControl
                    paper={paper}
                    groups={groups}
                    activeGroupId={activeGroupId}
                    compact
                    onMovePaper={onMovePaper}
                  />
                </td>
                <td>
                  <PaperDeleteButton paper={paper} compact onDeletePaper={onDeletePaper} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <ul className="paper-list" aria-label="Paper library">
      {papers.map((paper) => (
        <li
          className={`paper-item ${paper.id === selectedPaperId ? "paper-item--active" : ""}`}
          key={paper.id}
          onClick={() => onSelectPaper?.(paper.id)}
        >
          <div className="paper-item__top">
            <div>
              <p className="paper-title">{paper.title}</p>
              <p className="paper-meta">
                {paper.authors.join(", ")} | {paper.year} | {paper.pages} pages
              </p>
            </div>
            <StatusBadge status={paper.status} />
          </div>
          <div className="progress-track" aria-label={`${paper.title} index progress`}>
            <div className="progress-bar" style={{ width: `${paper.progress}%` }} />
          </div>
          <p className="small-muted">{paper.indexSummary}</p>
          <PaperMoveControl
            paper={paper}
            groups={groups}
            activeGroupId={activeGroupId}
            onMovePaper={onMovePaper}
          />
          <PaperDeleteButton paper={paper} onDeletePaper={onDeletePaper} />
        </li>
      ))}
    </ul>
  );
}

export function PaperLibrary({
  papers,
  embedded = false,
  groups,
  activeGroupId,
  viewMode,
  selectedPaperId,
  onSelectPaper,
  onMovePaper,
  onDeletePaper,
}: PaperLibraryProps) {
  if (embedded) {
    return (
      <PaperLibraryBody
        papers={papers}
        groups={groups}
        activeGroupId={activeGroupId}
        viewMode={viewMode}
        selectedPaperId={selectedPaperId}
        onSelectPaper={onSelectPaper}
        onMovePaper={onMovePaper}
        onDeletePaper={onDeletePaper}
      />
    );
  }

  return (
    <section className="panel" aria-labelledby="library-title">
      <div className="panel__header">
        <div>
          <h2 id="library-title">Library</h2>
          <p>Local papers and indexing state.</p>
        </div>
      </div>
      <div className="panel__body">
        <PaperLibraryBody
          papers={papers}
          groups={groups}
          activeGroupId={activeGroupId}
          viewMode={viewMode}
          selectedPaperId={selectedPaperId}
          onSelectPaper={onSelectPaper}
          onMovePaper={onMovePaper}
          onDeletePaper={onDeletePaper}
        />
      </div>
    </section>
  );
}
