import type { ApiPageEvidence, EvidenceItem } from "@/lib/types";

interface EvidencePanelProps {
  evidence: Array<EvidenceItem | ApiPageEvidence>;
  paperTitles?: Record<string, string>;
  note?: string | null;
}

function isApiEvidence(item: EvidenceItem | ApiPageEvidence): item is ApiPageEvidence {
  return "paper_id" in item;
}

function toPercent(score: number) {
  const normalized = score <= 1 ? score * 100 : score;
  return Math.max(0, Math.min(100, Math.round(normalized)));
}

function formatEvidence(item: EvidenceItem | ApiPageEvidence, paperTitles: Record<string, string>) {
  if (!isApiEvidence(item)) {
    return item;
  }

  return {
    id: `${item.paper_id}-${item.page_number}-${item.score}`,
    paperId: item.paper_id,
    paperTitle: paperTitles[item.paper_id] ?? item.paper_id,
    page: item.page_number,
    retriever: "VisRAG-Ret" as const,
    confidence: toPercent(item.score),
    snippet: item.caption ?? item.image_path ?? "Retrieved page image evidence."
  };
}

export function EvidencePanel({ evidence, paperTitles = {}, note }: EvidencePanelProps) {
  const normalizedEvidence = evidence.map((item) => formatEvidence(item, paperTitles));

  return (
    <section className="panel" aria-labelledby="evidence-title">
      <div className="panel__header">
        <div>
          <h2 id="evidence-title">Retrieval evidence</h2>
          <p>Page-level citations queued for grounded generation.</p>
        </div>
      </div>
      <div className="panel__body">
        {note ? <p className="inline-alert">{note}</p> : null}
        <ol className="evidence-list" aria-label="Retrieved page evidence">
          {normalizedEvidence.map((item) => (
            <li className="evidence-item" key={item.id}>
              <div className="evidence-item__top">
                <div>
                  <p className="evidence-title">{item.paperTitle}</p>
                  <p className="small-muted">
                    Page {item.page} | {item.retriever}
                  </p>
                </div>
                <div className="page-thumb" aria-label={`Page ${item.page} preview placeholder`}>
                  p.{item.page}
                </div>
              </div>
              <p className="evidence-snippet">{item.snippet}</p>
              <div className="confidence-meter" aria-label={`${item.confidence}% confidence`}>
                <span>{item.confidence}%</span>
                <div className="progress-track">
                  <div className="progress-bar" style={{ width: `${item.confidence}%` }} />
                </div>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
