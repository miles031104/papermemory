import { PaperLibrary } from "@/components/paper-library";
import { PaperUploadPanel } from "@/components/paper-upload-panel";
import type { PaperGroup, PaperSummary } from "@/lib/types";

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
}: PaperManagerViewProps) {
  return (
    <section className="workspace-grid workspace-grid--papers" aria-label="Paper manager">
      <div className="workspace-main">
        <section className="panel scope-panel" aria-labelledby="paper-manager-title">
          <div className="panel__header">
            <div>
              <p className="eyebrow">Paper Manager</p>
              <h2 id="paper-manager-title">{activeGroup?.name ?? "No group selected"}</h2>
              <p>Uploads and move actions update this group's RAG scope.</p>
            </div>
          </div>
        </section>
        <PaperUploadPanel
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
      <aside className="side-stack workspace-aside" aria-label="Papers in active group">
        <PaperLibrary
          papers={papers}
          groups={groups}
          activeGroupId={activeGroup?.id ?? ""}
          onMovePaper={onMovePaper}
        />
      </aside>
    </section>
  );
}
