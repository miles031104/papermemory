"use client";

import { useCallback, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import type { ChatMessage } from "@/lib/types";

interface ChatPanelProps {
  messages: ChatMessage[];
  question: string;
  isSubmitting: boolean;
  title: string;
  contextLabel: string;
  libraryDescription: string;
  error?: string | null;
  onQuestionChange: (question: string) => void;
  onSubmit: () => void;
  onReset: () => void;
  onSearchEvidence: () => void;
}

function scrollToEvidence(paperId: string, page: number) {
  const id = `evidence-${paperId}-${page}`;
  const el = document.getElementById(id);
  if (!el) return;
  el.scrollIntoView({ behavior: "smooth", block: "nearest" });
  el.classList.add("evidence-item--highlight");
  setTimeout(() => el.classList.remove("evidence-item--highlight"), 1500);
}

export function ChatPanel({
  messages,
  question,
  isSubmitting,
  title,
  contextLabel,
  libraryDescription,
  error,
  onQuestionChange,
  onSubmit,
  onReset,
  onSearchEvidence,
}: ChatPanelProps) {
  const canSubmit = question.trim().length > 0 && !isSubmitting;
  const listRef = useRef<HTMLOListElement>(null);

  useEffect(() => {
    const list = listRef.current;
    if (list) {
      list.scrollTop = list.scrollHeight;
    }
  }, [messages]);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
        event.preventDefault();
        if (canSubmit) onSubmit();
      }
    },
    [canSubmit, onSubmit],
  );

  return (
    <section className="panel chat-panel" aria-labelledby="chat-title">
      <div className="panel__header">
        <div>
          <p className="eyebrow">{contextLabel}</p>
          <h2 id="chat-title">{title}</h2>
          <p>{libraryDescription}</p>
        </div>
        <button className="button button--subtle" type="button" onClick={onReset}>
          Clear
        </button>
      </div>

      <div className="panel__body">
        <ol className="message-list" aria-label="Chat transcript" ref={listRef}>
          {messages.map((message) => (
            <li className={`message message--${message.role}`} key={message.id}>
              {message.role === "assistant" ? (
                <span className="message__avatar" aria-hidden="true">PM</span>
              ) : null}
              <div className="message__bubble">
                {message.role === "assistant" ? (
                  <div className="message__body message__body--markdown">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {message.content}
                    </ReactMarkdown>
                    {message.id === "streaming-assistant" ? (
                      <span className="streaming-cursor" aria-hidden="true" />
                    ) : null}
                  </div>
                ) : (
                  <p className="message__body">{message.content}</p>
                )}
                {message.citations.length > 0 ? (
                  <div className="citation-chips" aria-label="Cited pages">
                    {message.citations.map((citation) => (
                      <button
                        className="citation-chip"
                        key={`${citation.paperId}-${citation.page}`}
                        type="button"
                        onClick={() => scrollToEvidence(citation.paperId, citation.page)}
                        aria-label={`Jump to evidence: ${citation.label} page ${citation.page}`}
                      >
                        {citation.label} p.{citation.page}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
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
          <label htmlFor="question">
            <span>Question</span>
            <span className="shortcut-hint">⌘↵ to send</span>
          </label>
          <textarea
            id="question"
            name="question"
            rows={3}
            value={question}
            onChange={(event) => onQuestionChange(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about the active papers…"
          />
        </div>
        <div className="button-row">
          <button className="button button--primary" type="submit" disabled={!canSubmit}>
            {isSubmitting ? "Thinking…" : "Ask"}
          </button>
          <button
            className="button"
            type="button"
            disabled={!canSubmit}
            onClick={onSearchEvidence}
          >
            Search evidence
          </button>
        </div>
      </form>
    </section>
  );
}
