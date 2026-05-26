import type { PaperGroup, PaperSummary, ResearchLibrary, WorkspaceView } from "@/lib/types";

interface HomeViewProps {
  activeLibrary?: ResearchLibrary;
  activeGroup?: PaperGroup;
  papers: PaperSummary[];
  groups: PaperGroup[];
  isPersisted: boolean;
  onViewChange: (view: WorkspaceView) => void;
}

export function HomeView({
  activeLibrary,
  activeGroup,
  papers,
  groups,
  isPersisted,
  onViewChange,
}: HomeViewProps) {
  const readyPapers = papers.filter((paper) => paper.status === "ready").length;
  const indexedPages = papers.reduce((total, paper) => total + paper.pages, 0);
  const activeGroupPapers = papers.filter((paper) => activeGroup?.paperIds.includes(paper.id));

  return (
    <section className="home-view" aria-labelledby="home-title">
      <div className="hero-section hero-section--home">
        <div className="hero-section__copy">
          <p className="hero-kicker">Local-first visual RAG for serious reading</p>
          <h1 id="home-title">A research memory organized around paper groups.</h1>
          <p className="hero-section__lead">
            Manage local PDFs by group, then chat with exactly the group you selected.
          </p>
          <div className="hero-actions">
            <button className="button button--primary button--hero" type="button" onClick={() => onViewChange("chat")}>
              Enter Chat
            </button>
            <button className="button button--subtle button--hero" type="button" onClick={() => onViewChange("papers")}>
              Manage Paper Library
            </button>
            <button
              className="button button--subtle button--hero"
              type="button"
              onClick={() => onViewChange("settings")}
            >
              Settings
            </button>
          </div>
        </div>
        <div className="hero-command" aria-label="Workspace overview">
          <div className="hero-command__top">
            <div>
              <p className="eyebrow">Active group</p>
              <h2>{activeGroup?.name ?? activeLibrary?.name ?? "Research workspace"}</h2>
            </div>
            <span className="hero-command__pill">{isPersisted ? "Local sync" : "Demo mode"}</span>
          </div>
          <div className="hero-metrics">
            <div className="hero-metric">
              <strong>{readyPapers.toString().padStart(2, "0")}</strong>
              <span>Ready papers</span>
            </div>
            <div className="hero-metric">
              <strong>{indexedPages.toLocaleString()}</strong>
              <span>Indexed pages</span>
            </div>
            <div className="hero-metric">
              <strong>{groups.length.toString().padStart(2, "0")}</strong>
              <span>Groups</span>
            </div>
          </div>
          <p className="small-muted">{activeGroupPapers.length} paper(s) are currently in this active RAG group.</p>
        </div>
      </div>
    </section>
  );
}
