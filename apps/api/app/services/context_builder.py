from app.schemas.papers import page_image_url
from app.schemas.chat import ChatMessage
from app.schemas.retrieval import PageEvidence

RECENT_CONVERSATION_MESSAGE_LIMIT = 8

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


def select_recent_conversation_messages(
    messages: list[ChatMessage],
    limit: int = RECENT_CONVERSATION_MESSAGE_LIMIT,
) -> list[ChatMessage]:
    if limit <= 0:
        return []
    return list(messages[-limit:])


def build_evisrag_prompt(
    question: str,
    evidence: list[PageEvidence],
    retrieval_attempted: bool = False,
) -> str:
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
        (
            f"- paper_id={item.paper_id}, page={item.page_number}, "
            f"citation_id={item.paper_id} p.{item.page_number}, "
            f"score={item.score:.4f}, image_ref={_evidence_image_reference(item)}, "
            f"caption={item.caption or 'none'}"
        )
        for item in evidence
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
        "- If the evidence is insufficient, say what is missing instead of guessing.\n\n"
        f"Question:\n{question}\n\n"
        f"Retrieved visual evidence:\n{evidence_block}"
    )


def _evidence_image_reference(item: PageEvidence) -> str:
    image_url = page_image_url(item.paper_id, item.page_number)
    if image_url is not None:
        return image_url
    return f"paper_id={item.paper_id}, page={item.page_number}"
