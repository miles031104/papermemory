import type { ApiPageEvidence, EvidenceItem } from "@/lib/types";

interface EvidencePanelProps {
  evidence: Array<EvidenceItem | ApiPageEvidence>;
  paperTitles?: Record<string, string>;
  note?: string | null;
  apiBaseUrl?: string;
}

function isApiEvidence(item: EvidenceItem | ApiPageEvidence): item is ApiPageEvidence {
  return "paper_id" in item;
}

function toPercent(score: number) {
  const normalized = score <= 1 ? score * 100 : score;
  return Math.max(0, Math.min(100, Math.round(normalized)));
}

function resolveEvidenceImageUrl(imageUrl: string | null | undefined, apiBaseUrl?: string) {
  if (!imageUrl) {
    return null;
  }

  if (/^(https?:|data:|blob:)/.test(imageUrl)) {
    return imageUrl;
  }

  const trimmedBaseUrl = apiBaseUrl?.trim();
  if (!trimmedBaseUrl) {
    return imageUrl;
  }

  try {
    return new URL(imageUrl, `${trimmedBaseUrl.replace(/\/$/, "")}/`).toString();
  } catch {
    return imageUrl;
  }
}

function formatEvidence(
  item: EvidenceItem | ApiPageEvidence,
  paperTitles: Record<string, string>,
  apiBaseUrl?: string
) {
  if (!isApiEvidence(item)) {
    return item;
  }

  const imageUrl = resolveEvidenceImageUrl(item.image_url, apiBaseUrl);

  return {
    id: `${item.paper_id}-${item.page_number}-${item.score}`,
    paperId: item.paper_id,
    paperTitle: paperTitles[item.paper_id] ?? item.paper_id,
    page: item.page_number,
    retriever: "VisRAG-Ret" as const,
    confidence: toPercent(item.score),
    snippet: item.caption ?? "Retrieved page image evidence is available for this result.",
    imageUrl
  };
}

export function EvidencePanel({ evidence, paperTitles = {}, note, apiBaseUrl }: EvidencePanelProps) {
  const normalizedEvidence = evidence.map((item) => formatEvidence(item, paperTitles, apiBaseUrl));

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
        {normalizedEvidence.length === 0 ? (
          <p className="small-muted">No page evidence is attached to the current conversation yet.</p>
        ) : null}
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
              {item.imageUrl ? (
                <figure className="page-preview">
                  <img src={item.imageUrl} alt={`${item.paperTitle}, page ${item.page}`} loading="lazy" />
                  <figcaption>Page image evidence</figcaption>
                </figure>
              ) : null}
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
