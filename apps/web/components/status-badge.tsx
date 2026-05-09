import type { PaperStatus } from "@/lib/types";

const statusLabels: Record<PaperStatus, string> = {
  queued: "Queued",
  indexing: "Indexing",
  ready: "Ready",
  error: "Needs review"
};

export function StatusBadge({ status }: { status: PaperStatus }) {
  return (
    <span className={`status-badge status-badge--${status}`}>
      {statusLabels[status]}
    </span>
  );
}
