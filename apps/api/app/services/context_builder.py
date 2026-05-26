from app.schemas.papers import page_image_url
from app.schemas.chat import ChatMessage
from app.schemas.retrieval import PageEvidence

RECENT_CONVERSATION_MESSAGE_LIMIT = 8

# Number of recent conversation turns to blend into the retrieval query.
# Industry standard for conversational RAG: 1-2 prior turns is sufficient
# to resolve co-references without making the query vector too diffuse.
# Reference: MaFeRw 2024, SemEval 2026 Task 8.
QUERY_CONTEXT_TURNS = 2

# Score tiers for evidence confidence annotation.
# Empirical starting points for VisRAG-Ret cosine scores.
# Note: cosine similarity is not comparable across queries; use these as a
# rough floor, not a hard quality guarantee. (Qdrant docs; arxiv:2408.04887)
EVIDENCE_HIGH_CONFIDENCE = 0.65
EVIDENCE_LOW_CONFIDENCE = 0.40

PAPERMEMORY_SYSTEM_PROMPT = """You are PaperMemory, a local-first research paper assistant.

Core behavior:
- Support both general research conversation and evidence-grounded paper QA.
- When paper evidence is provided, answer from retrieved paper evidence, attached page images,
  and prior chat context.
- When no paper evidence is provided, answer as a general research assistant and clearly avoid
  presenting the response as paper-grounded.
- Reason internally before answering, but never expose hidden reasoning, chain-of-thought,
  scratchpads, XML thinking tags, or provider reasoning traces.
- Do not narrate the retrieval process. Avoid lines like "I will inspect pages", "Step 1", or "Loading pages".
- Do not claim that you inspected a page unless the content is present in the provided evidence or attached image context.
- If evidence is weak or missing, say exactly what is missing and give the best bounded answer.

Output format:
Use concise Markdown with these sections when paper evidence is available:
**Answer**
Directly answer the user's question.

**Evidence**
- Cite page-level evidence only as `paper_id p.N`.

**Limits**
State uncertainty, missing pages, or whether the answer relies on text-only evidence.
"""


QUERY_REWRITE_SYSTEM_PROMPT = (
    "You are a search query optimizer. "
    "Rewrite the user's last question as a concise standalone retrieval query: "
    "resolve pronouns and co-references, remove conversational preamble. "
    "Output ONLY the rewritten query, nothing else. Keep it under 20 words."
)


def build_query_rewrite_prompt(question: str, messages: list[ChatMessage]) -> str:
    """Build a prompt asking the LLM to produce a standalone retrieval query.

    Includes up to ``QUERY_CONTEXT_TURNS`` prior turns so the model can resolve
    references like "it", "that method", or "the proposed approach".
    """
    lines: list[str] = []
    for msg in messages[-(QUERY_CONTEXT_TURNS * 2):]:
        lines.append(f"{msg.role}: {msg.content.strip()}")
    lines.append(f"user: {question}")
    return "\n".join(lines)


def build_conversational_query(
    question: str,
    messages: list[ChatMessage],
    context_turns: int = QUERY_CONTEXT_TURNS,
) -> str:
    """Build an enriched query for embedding by blending recent conversation context.

    In multi-turn conversations the current question is often underspecified
    ("how does that compare?", "what about the limitations?"). Prepending the
    last ``context_turns`` assistant+user pairs gives the retriever enough
    co-reference context to find the right pages without making the query
    vector too diffuse.

    Industry reference: conversational RAG query rewriting (MaFeRw 2024,
    SemEval 2026 Task 8). Simple concatenation outperforms no-context baseline;
    full LLM rewrite is reserved for Stage 6 agentic retrieval.

    Args:
        question: The current user question.
        messages: The full conversation history (newest last).
        context_turns: Number of prior user+assistant turn pairs to include.

    Returns:
        A single string suitable for passing to ``embed_query``.
    """
    if not messages or context_turns <= 0:
        return question

    # Take the last N *pairs* (user + assistant).
    recent = messages[-(context_turns * 2):]
    context_parts = [
        f"{msg.role}: {msg.content.strip()}"
        for msg in recent
        if msg.role in ("user", "assistant") and msg.content.strip()
    ]
    if not context_parts:
        return question

    context_block = "\n".join(context_parts)
    return f"{context_block}\nuser: {question}"


def select_recent_conversation_messages(
    messages: list[ChatMessage],
    limit: int = RECENT_CONVERSATION_MESSAGE_LIMIT,
) -> list[ChatMessage]:
    """Return the most recent ``limit`` messages, prepending a summary if available.

    When the conversation exceeds ``limit`` messages the tail is kept verbatim
    and a synthetic summary message is prepended so the model retains awareness
    of earlier conclusions.

    The summary is produced by ``compress_conversation_history``. If that
    function has not been called (no summary exists), older turns are silently
    dropped - the same behaviour as before this change.

    Industry reference: LangChain ConversationSummaryBufferMemory pattern;
    trigger summarisation at ~75% context capacity (agenta.ai, 2024).
    """
    if limit <= 0:
        return []
    if len(messages) <= limit:
        return list(messages)

    # Keep the most recent (limit - 1) messages, leaving room for a summary.
    tail = list(messages[-(limit - 1):])

    # Check if the older portion contains a pre-computed summary message.
    older = messages[:-(limit - 1)]
    summary_msg = _extract_summary_message(older)
    if summary_msg is not None:
        return [summary_msg] + tail

    # No summary available yet - return the full limit without a summary slot.
    return list(messages[-limit:])


def compress_conversation_history(
    messages: list[ChatMessage],
    summary_prompt_prefix: str = (
        "Summarise the key research conclusions, paper references, and open "
        "questions from this conversation so far. Be concise."
    ),
) -> tuple[list[ChatMessage], str]:
    """Produce a text summary prompt for ``messages``.

    This function does NOT call the model itself - it returns the text that
    should be passed to the model as a summarisation request. The caller is
    responsible for running inference and storing the result.

    Usage pattern (in a background task or after the context window fills)::

        older, prompt = compress_conversation_history(history[:cutoff])
        summary_text = await model_gateway.generate(
            [{"role": "user", "content": prompt}]
        )
        # Store result as:
        # ChatMessage(role="assistant", content=f"[Summary] {summary_text}")
        # and prepend it to future message lists.

    Returns:
        (messages_to_summarise, summary_prompt)
    """
    prompt_parts = [summary_prompt_prefix, "\n\nConversation:\n"]
    for msg in messages:
        prompt_parts.append(f"{msg.role.capitalize()}: {msg.content.strip()}")
    return messages, "\n".join(prompt_parts)


def build_evisrag_prompt(
    question: str,
    evidence: list[PageEvidence],
    retrieval_attempted: bool = False,
    include_captions: bool = True,
) -> str:
    """Build the per-turn user prompt for the LLM.

    Evidence items are annotated with a confidence tier based on their
    retrieval score so the model can weight them appropriately.
    Paper title and author metadata are injected when available.
    """
    if not evidence:
        if retrieval_attempted:
            return (
                "Use PaperMemory scoped retrieval mode for this turn.\n"
                "The active paper scope was searched, but no page evidence was returned. "
                "Do not present the answer as grounded in the user's paper library.\n"
                "Final-answer contract:\n"
                "- Reason internally, but do not output <think>, hidden reasoning, scratchpad text, "
                "or step-by-step process narration.\n"
                "- If the user asks about paper-specific claims, say that scoped retrieval found no supporting "
                "evidence and suggest searching different terms, adding papers, or checking indexing status.\n"
                "- Do not include paper citations because no retrieved evidence is available.\n\n"
                f"Question:\n{question}\n\n"
                "Retrieved visual evidence:\n- Scoped retrieval returned no evidence."
            )

        return (
            "Use PaperMemory conversation mode for this turn.\n"
            "No retrieved paper evidence is available, so do not present the answer as grounded "
            "in the user's paper library.\n"
            "Final-answer contract:\n"
            "- Reason internally, but do not output <think>, hidden reasoning, scratchpad text, "
            "or step-by-step process narration.\n"
            "- Answer the user's question directly when it can be handled as general research conversation.\n"
            "- If the user asks about specific papers, say that no paper evidence is available and suggest "
            "uploading/indexing or searching the relevant papers.\n"
            "- Do not include paper citations unless retrieved evidence is provided.\n\n"
            f"Question:\n{question}\n\n"
            "Retrieved visual evidence:\n- None for this turn."
        )

    evidence_block = "\n".join(
        _format_evidence_item(item, include_caption=include_captions) for item in evidence
    )
    return (
        "Use an EVisRAG-style evidence-first workflow internally, but do not narrate "
        "the workflow to the user.\n"
        "Final-answer contract:\n"
        "- Reason internally, but do not output <think>, hidden reasoning, scratchpad text, "
        "or step-by-step process narration.\n"
        "- Do not say you inspected, loaded, or viewed pages; simply answer from the evidence.\n"
        "- Use the sections **Answer**, **Evidence**, and **Limits**.\n"
        "- Cite page-level evidence using the provided citation_id values in `paper_id p.N` form.\n"
        "- Evidence items marked [weak] have low retrieval scores; treat them as supporting "
        "context only, not primary citations.\n"
        "- If the evidence is insufficient, say what is missing instead of guessing.\n\n"
        f"Question:\n{question}\n\n"
        f"Retrieved visual evidence:\n{evidence_block}"
    )


def _format_evidence_item(item: PageEvidence, include_caption: bool = True) -> str:
    """Format a single evidence item with confidence tier and available metadata."""
    if item.score >= EVIDENCE_HIGH_CONFIDENCE:
        confidence = "high"
    elif item.score >= EVIDENCE_LOW_CONFIDENCE:
        confidence = "medium"
    else:
        confidence = "weak"

    title_label = ""
    if item.title:
        title_label = f", title={item.title!r}"
    elif item.metadata and item.metadata.get("title"):
        title_label = f", title={item.metadata['title']!r}"

    author_label = ""
    if item.metadata and item.metadata.get("authors"):
        author_label = f", authors={item.metadata['authors']!r}"

    image_ref = _evidence_image_reference(item)
    caption_label = f", caption={item.caption or 'none'}" if include_caption else ""

    return (
        f"- [{confidence}] paper_id={item.paper_id}, page={item.page_number}, "
        f"citation_id={item.paper_id} p.{item.page_number}, "
        f"score={item.score:.4f}{title_label}{author_label}, "
        f"image_ref={image_ref}{caption_label}"
    )


def _extract_summary_message(messages: list[ChatMessage]) -> ChatMessage | None:
    """Return the last [Summary] message from a list, if one exists."""
    for msg in reversed(messages):
        if msg.role == "assistant" and msg.content.startswith("[Summary]"):
            return msg
    return None


def _evidence_image_reference(item: PageEvidence) -> str:
    image_url = page_image_url(item.paper_id, item.page_number)
    if image_url is not None:
        return image_url
    return f"paper_id={item.paper_id}, page={item.page_number}"
