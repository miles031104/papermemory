import type { ChatMessage } from "@/lib/types";

interface ChatPanelProps {
  messages: ChatMessage[];
  question: string;
  isSubmitting: boolean;
  error?: string | null;
  onQuestionChange: (question: string) => void;
  onSubmit: () => void;
  onReset: () => void;
  onSearchEvidence: () => void;
}

export function ChatPanel({
  messages,
  question,
  isSubmitting,
  error,
  onQuestionChange,
  onSubmit,
  onReset,
  onSearchEvidence
}: ChatPanelProps) {
  const canSubmit = question.trim().length > 0 && !isSubmitting;

  return (
    <section className="panel chat-panel" aria-labelledby="chat-title">
      <div className="panel__header">
        <div>
          <h2 id="chat-title">Ask the library</h2>
          <p>EVisRAG-style answers grounded in retrieved page evidence.</p>
        </div>
        <button className="button button--subtle" type="button" onClick={onReset}>
          New chat
        </button>
      </div>

      <div className="panel__body">
        <ol className="message-list" aria-label="Chat transcript">
          {messages.map((message) => (
            <li className={`message message--${message.role}`} key={message.id}>
              <p className="message__author">
                {message.role === "assistant" ? "PaperMemory" : "You"}
              </p>
              <p className="message__body">{message.content}</p>
              {message.citations.length > 0 ? (
                <div className="citation-chips" aria-label="Cited pages">
                  {message.citations.map((citation) => (
                    <span className="citation-chip" key={`${citation.paperId}-${citation.page}`}>
                      {citation.label} p.{citation.page}
                    </span>
                  ))}
                </div>
              ) : null}
            </li>
          ))}
        </ol>
      </div>

      <form
        className="composer"
        aria-label="Ask a question"
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit();
        }}
      >
        {error ? (
          <p className="inline-alert inline-alert--error" role="alert">
            {error}
          </p>
        ) : null}
        <div className="field">
          <label htmlFor="question">Question</label>
          <textarea
            id="question"
            name="question"
            value={question}
            onChange={(event) => onQuestionChange(event.target.value)}
            placeholder="Compare the retrieval evidence behind the main contribution."
          />
        </div>
        <div className="button-row">
          <button className="button button--primary" type="submit" disabled={!canSubmit}>
            {isSubmitting ? "Asking..." : "Ask with evidence"}
          </button>
          <button className="button" type="button" disabled={!canSubmit} onClick={onSearchEvidence}>
            Search evidence
          </button>
        </div>
      </form>
    </section>
  );
}
