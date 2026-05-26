import { useEffect, useMemo, useState } from "react";
import { PaperLibrary } from "@/components/paper-library";
import { PaperUploadPanel } from "@/components/paper-upload-panel";
import type { PaperGroup, PaperSummary } from "@/lib/types";

type PaperManagerViewMode = "table" | "cards";

interface PaperManagerViewProps {
  activeGroup?: PaperGroup;
  groups: PaperGroup[];
  papers: PaperSummary[];
  uploadTitle: string;
  selectedFile: File | null;
  fileInputKey: number;
  isUploading: boolean;
  uploadMessage: string | null;
  uploadError: string | null;
  onTitleChange: (title: string) => void;
  onFileChange: (file: File | null) => void;
  onUpload: () => void;
  onMovePaper: (paperId: string, groupId: string) => Promise<void>;
  onDeletePaper: (paperId: string) => Promise<void>;
}

export function PaperManagerView({
  activeGroup,
  groups,
  papers,
  uploadTitle,
  selectedFile,
  fileInputKey,
  isUploading,
  uploadMessage,
  uploadError,
  onTitleChange,
  onFileChange,
  onUpload,
  onMovePaper,
  onDeletePaper,
}: PaperManagerViewProps) {
  const [viewMode, setViewMode] = useState<PaperManagerViewMode>("table");
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [selectedPaperId, setSelectedPaperId] = useState<string | undefined>(papers[0]?.id);

  useEffect(() => {
    if (papers.length === 0) {
      setSelectedPaperId(undefined);
      return;
    }

    if (!selectedPaperId || !papers.some((paper) => paper.id === selectedPaperId)) {
      setSelectedPaperId(papers[0].id);
    }
  }, [papers, selectedPaperId]);

  const selectedPaper = useMemo(
    () => papers.find((paper) => paper.id === selectedPaperId) ?? papers[0],
    [papers, selectedPaperId]
  );
  const readyCount = papers.filter((paper) => paper.status === "ready").length;
  const pageCount = papers.reduce((total, paper) => total + paper.pages, 0);

  return (
    <section className="workspace-grid workspace-grid--papers" aria-label="Paper manager">
      <div className="workspace-main">
        <section className="panel paper-manager-panel" aria-labelledby="paper-manager-title">
          <div className="panel__header paper-manager-header">
            <div className="paper-manager-heading">
              <p className="eyebrow">Paper Manager</p>
              <h2 id="paper-manager-title">{activeGroup?.name ?? "No group selected"}</h2>
              <p>
                {papers.length} paper(s), {readyCount} ready, {pageCount} indexed page(s).
              </p>
            </div>
            <div className="paper-manager-actions" aria-label="Paper manager controls">
              <div className="segmented paper-manager-view-switch" role="group" aria-label="Paper layout">
                <button
                  className={`segment ${viewMode === "table" ? "segment--active" : ""}`}
                  type="button"
                  onClick={() => setViewMode("table")}
                >
                  Table
                </button>
                <button
                  className={`segment ${viewMode === "cards" ? "segment--active" : ""}`}
                  type="button"
                  onClick={() => setViewMode("cards")}
                >
                  Cards
                </button>
              </div>
              <button
                className="button button--primary"
                type="button"
                aria-expanded={isUploadOpen}
                onClick={() => setIsUploadOpen((open) => !open)}
              >
                Upload paper
              </button>
            </div>
          </div>
          <div className="panel__body paper-manager-body">
            {isUploadOpen ? (
              <div className="paper-manager-upload-drawer">
                <PaperUploadPanel
                  embedded
                  title={uploadTitle}
                  selectedFile={selectedFile}
                  fileInputKey={fileInputKey}
                  isUploading={isUploading}
                  message={uploadMessage}
                  error={uploadError}
                  onTitleChange={onTitleChange}
                  onFileChange={onFileChange}
                  onUpload={onUpload}
                />
              </div>
            ) : null}
            <div className="paper-manager-library">
              <PaperLibrary
                embedded
                papers={papers}
                groups={groups}
                activeGroupId={activeGroup?.id ?? ""}
                viewMode={viewMode}
                selectedPaperId={selectedPaper?.id}
                onSelectPaper={setSelectedPaperId}
                onMovePaper={onMovePaper}
                onDeletePaper={onDeletePaper}
              />
              {papers.length === 0 ? (
                <button
                  className="button button--subtle paper-manager-empty-action"
                  type="button"
                  onClick={() => setIsUploadOpen(true)}
                >
                  Upload first paper
                </button>
              ) : null}
            </div>
          </div>
        </section>
      </div>
      <aside className="side-stack workspace-aside" aria-label="Selected paper details">
        <section className="panel paper-inspector-panel" aria-labelledby="paper-inspector-title">
          <div className="panel__header">
            <div>
              <p className="eyebrow">Inspector</p>
              <h2 id="paper-inspector-title">{selectedPaper?.title ?? "No paper selected"}</h2>
              <p>{activeGroup ? `Scope: ${activeGroup.name}` : "Choose a group to manage papers."}</p>
            </div>
          </div>
          <div className="panel__body paper-inspector-body">
            {selectedPaper ? (
              <>
                <dl className="paper-inspector-list">
                  <div>
                    <dt>Authors</dt>
                    <dd>{selectedPaper.authors.join(", ") || "Unknown"}</dd>
                  </div>
                  <div>
                    <dt>Year</dt>
                    <dd>{selectedPaper.year}</dd>
                  </div>
                  <div>
                    <dt>Pages</dt>
                    <dd>{selectedPaper.pages}</dd>
                  </div>
                  <div>
                    <dt>Status</dt>
                    <dd>{selectedPaper.status}</dd>
                  </div>
                  <div>
                    <dt>Index</dt>
                    <dd>{selectedPaper.progress}%</dd>
                  </div>
                </dl>
                <div className="progress-track" aria-label={`${selectedPaper.title} index progress`}>
                  <div className="progress-bar" style={{ width: `${selectedPaper.progress}%` }} />
                </div>
                <p className="small-muted">{selectedPaper.indexSummary}</p>
                <p className="inline-alert inline-alert--success">
                  Use the table row controls to move this paper between groups or delete it from the local library.
                </p>
              </>
            ) : (
              <p className="small-muted">Upload or select a paper to see its management details.</p>
            )}
          </div>
        </section>
      </aside>
    </section>
  );
}
