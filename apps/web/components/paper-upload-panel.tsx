import type { ChangeEvent } from "react";

interface PaperUploadPanelProps {
  title: string;
  selectedFile: File | null;
  fileInputKey: number;
  isUploading: boolean;
  message?: string | null;
  error?: string | null;
  onTitleChange: (title: string) => void;
  onFileChange: (file: File | null) => void;
  onUpload: () => void;
}

export function PaperUploadPanel({
  title,
  selectedFile,
  fileInputKey,
  isUploading,
  message,
  error,
  onTitleChange,
  onFileChange,
  onUpload
}: PaperUploadPanelProps) {
  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    onFileChange(event.target.files?.[0] ?? null);
  };

  return (
    <section className="panel" aria-labelledby="upload-title">
      <div className="panel__header">
        <div>
          <h2 id="upload-title">Upload paper</h2>
          <p>Ingest a PDF into local storage, page images, and vector indexes.</p>
        </div>
      </div>
      <form
        className="panel__body"
        aria-label="Upload a paper"
        onSubmit={(event) => {
          event.preventDefault();
          onUpload();
        }}
      >
        {error ? (
          <p className="inline-alert inline-alert--error" role="alert">
            {error}
          </p>
        ) : null}
        {message ? <p className="inline-alert">{message}</p> : null}
        <div className="upload-dropzone">
          <label htmlFor="paper-file">PDF file</label>
          <input
            key={fileInputKey}
            id="paper-file"
            name="paper-file"
            type="file"
            accept="application/pdf"
            onChange={handleFileChange}
          />
          <p className="small-muted">OCR and page embeddings will run locally before chat.</p>
        </div>

        <div className="field-grid">
          <div className="field">
            <label htmlFor="paper-title">Title</label>
            <input
              id="paper-title"
              name="title"
              type="text"
              value={title}
              onChange={(event) => onTitleChange(event.target.value)}
              placeholder={selectedFile?.name ?? "Optional title override"}
            />
          </div>
        </div>

        <div className="button-row">
          <button
            className="button button--primary"
            type="submit"
            disabled={!selectedFile || isUploading}
          >
            {isUploading ? "Uploading..." : "Start ingest"}
          </button>
          <button className="button button--subtle" type="button">
            Watch folder
          </button>
        </div>
      </form>
    </section>
  );
}
