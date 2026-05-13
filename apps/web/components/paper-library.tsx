import { StatusBadge } from "@/components/status-badge";
import type { PaperSummary } from "@/lib/types";

interface PaperLibraryProps {
  papers: PaperSummary[];
  embedded?: boolean;
}

function PaperLibraryBody({ papers }: { papers: PaperSummary[] }) {
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
          </li>
        ))}
      </ul>
    </>
  );
}

export function PaperLibrary({ papers, embedded = false }: PaperLibraryProps) {
  if (embedded) {
    return <PaperLibraryBody papers={papers} />;
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
        <PaperLibraryBody papers={papers} />
      </div>
    </section>
  );
}
