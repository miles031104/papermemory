import { useEffect, useMemo, useState } from "react";

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
  const normalizedEvidence = useMemo(
    () => evidence.map((item) => formatEvidence(item, paperTitles, apiBaseUrl)),
    [apiBaseUrl, evidence, paperTitles],
  );
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(null);
  const selectedEvidence =
    normalizedEvidence.find((item) => item.id === selectedEvidenceId) ?? null;

  useEffect(() => {
    if (!selectedEvidenceId) {
      return;
    }
    if (!normalizedEvidence.some((item) => item.id === selectedEvidenceId)) {
      setSelectedEvidenceId(null);
    }
  }, [normalizedEvidence, selectedEvidenceId]);

  useEffect(() => {
    if (!selectedEvidence) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setSelectedEvidenceId(null);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [selectedEvidence]);

  return (
    <>
      <section className="panel evidence-panel" aria-labelledby="evidence-title">
        <div className="panel__header">
          <div>
            <h2 id="evidence-title">Retrieval evidence</h2>
            <p>Page-level citations queued for grounded generation.</p>
          </div>
        </div>
        <div className="panel__body evidence-panel__body">
          {note ? <p className="inline-alert">{note}</p> : null}
          {normalizedEvidence.length === 0 ? (
            <p className="small-muted">No page evidence is attached to the current conversation yet.</p>
          ) : null}
          <ol className="evidence-list" aria-label="Retrieved page evidence">
            {normalizedEvidence.map((item) => (
              <li className="evidence-item" key={item.id} id={`evidence-${item.paperId}-${item.page}`}>
                <button
                  className="evidence-card-button"
                  type="button"
                  onClick={() => setSelectedEvidenceId(item.id)}
                  aria-label={`Open evidence page ${item.page} from ${item.paperTitle}`}
                >
                  <div className="evidence-item__top">
                    <div>
                      <p className="evidence-title">{item.paperTitle}</p>
                      <p className="small-muted">
                        Page {item.page} | {item.retriever}
                      </p>
                    </div>
                    <div className="page-thumb" aria-label={`Page ${item.page} preview`}>
                      {item.imageUrl ? (
                        <img src={item.imageUrl} alt="" loading="lazy" />
                      ) : (
                        <span>p.{item.page}</span>
                      )}
                    </div>
                  </div>
                  <p className="evidence-snippet">{item.snippet}</p>
                  <div className="confidence-meter" aria-label={`${item.confidence}% confidence`}>
                    <span>{item.confidence}%</span>
                    <div className="progress-track">
                      <div className="progress-bar" style={{ width: `${item.confidence}%` }} />
                    </div>
                  </div>
                </button>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {selectedEvidence ? (
        <div
          className="evidence-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="evidence-dialog-title"
          onClick={() => setSelectedEvidenceId(null)}
        >
          <div className="evidence-dialog__surface" onClick={(event) => event.stopPropagation()}>
            <div className="evidence-dialog__header">
              <div>
                <p className="eyebrow">Page evidence</p>
                <h2 id="evidence-dialog-title">{selectedEvidence.paperTitle}</h2>
                <p>
                  Page {selectedEvidence.page} | {selectedEvidence.confidence}% confidence
                </p>
              </div>
              <button
                className="icon-button"
                type="button"
                aria-label="Close evidence preview"
                onClick={() => setSelectedEvidenceId(null)}
              >
                x
              </button>
            </div>
            <div className="evidence-dialog__content">
              <div className="evidence-dialog__image">
                {selectedEvidence.imageUrl ? (
                  <img
                    src={selectedEvidence.imageUrl}
                    alt={`${selectedEvidence.paperTitle}, page ${selectedEvidence.page}`}
                  />
                ) : (
                  <div className="evidence-dialog__empty-image">
                    Page {selectedEvidence.page}
                  </div>
                )}
              </div>
              <div className="evidence-dialog__text">
                <p className="eyebrow">Extracted text</p>
                <p>{selectedEvidence.snippet}</p>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
