import { StatusBadge } from "@/components/status-badge";
import type { PaperGroup, PaperSummary } from "@/lib/types";

interface PaperLibraryProps {
  papers: PaperSummary[];
  embedded?: boolean;
  groups?: PaperGroup[];
  activeGroupId?: string;
  onMovePaper?: (paperId: string, groupId: string) => Promise<void>;
}

function PaperLibraryBody({
  papers,
  groups = [],
  activeGroupId = "",
  onMovePaper,
}: {
  papers: PaperSummary[];
  groups?: PaperGroup[];
  activeGroupId?: string;
  onMovePaper?: (paperId: string, groupId: string) => Promise<void>;
}) {
  return (
    <>
      {papers.length === 0 ? <p className="small-muted">No papers in this database yet.</p> : null}
      <ul className="paper-list" aria-label="Paper library">
        {papers.map((paper) => (
          <li className="paper-item" key={paper.id}>
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
            {onMovePaper && groups.length > 0 ? (
              <label className="paper-move-control">
                <span>Move group</span>
                <select
                  value={activeGroupId}
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
            ) : null}
          </li>
        ))}
      </ul>
    </>
  );
}

export function PaperLibrary({
  papers,
  embedded = false,
  groups,
  activeGroupId,
  onMovePaper,
}: PaperLibraryProps) {
  if (embedded) {
    return (
      <PaperLibraryBody
        papers={papers}
        groups={groups}
        activeGroupId={activeGroupId}
        onMovePaper={onMovePaper}
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
          onMovePaper={onMovePaper}
        />
      </div>
    </section>
  );
}
