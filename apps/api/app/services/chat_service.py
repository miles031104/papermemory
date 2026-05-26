import json
import math
import re
from collections.abc import AsyncGenerator
from typing import Any

from app.schemas.chat import ChatMessage, ChatRequest, ChatResponse
from app.schemas.retrieval import PageEvidence
from app.services.context_builder import (
    AGENTIC_RETRIEVAL_SYSTEM_PROMPT,
    PAPERMEMORY_SYSTEM_PROMPT,
    QUERY_REWRITE_SYSTEM_PROMPT,
    RECENT_CONVERSATION_MESSAGE_LIMIT,
    build_agentic_retrieval_prompt,
    build_conversational_query,
    build_evisrag_prompt as build_context_prompt,
    build_query_rewrite_prompt,
    compress_conversation_history,
    select_recent_conversation_messages,
)
from app.services.model_gateway import BuiltUserContent, ModelGateway
from app.services.page_image_resolver import PageImageResolver
from app.services.vector_store import VectorStore
from app.services.visrag_service import VisRAGService

CONVERSATION_MODE_LIMIT = "No retrieved paper evidence is available; this response is not paper-grounded."
NO_SCOPED_EVIDENCE_LIMIT = "Scoped retrieval returned no evidence; no paper citations are available."
TEXT_ONLY_EVIDENCE_LIMIT = "Text-only evidence context; no page images were included."
AGENTIC_RETRIEVAL_MAX_QUERIES = 4
AGENTIC_RETRIEVAL_MAX_QUERY_CHARS = 180


class ChatService:
    """Coordinates retrieval and answer generation with visual page evidence."""

    def __init__(
        self,
        visrag: VisRAGService,
        vector_store: VectorStore,
        model_gateway: ModelGateway,
        page_image_resolver: PageImageResolver | None = None,
    ) -> None:
        self.visrag = visrag
        self.vector_store = vector_store
        self.model_gateway = model_gateway
        self.page_image_resolver = page_image_resolver

    async def answer(self, request: ChatRequest) -> ChatResponse:
        paper_scope_count = len(request.paper_ids or [])
        evidence, retrieval_attempted = await self._do_retrieval(request)

        verified_prompt, user_content = self._build_generation_content(
            request=request,
            evidence=evidence,
            retrieval_attempted=retrieval_attempted,
        )
        selected_messages = select_recent_conversation_messages(request.messages)
        messages = [
            {"role": "system", "content": PAPERMEMORY_SYSTEM_PROMPT},
            *[message.model_dump() for message in selected_messages],
            {"role": "user", "content": user_content.content},
        ]
        generation = await self.model_gateway.generate(
            messages=messages,
            model=request.model,
            base_url=request.base_url,
            api_key=request.api_key,
            temperature=request.temperature,
        )

        answer_text, _ = self._verify_citations(generation.text, evidence)
        included_image_count = user_content.included_image_count
        return ChatResponse(
            status=self._response_status(
                evidence_count=len(evidence),
                retrieval_attempted=retrieval_attempted,
            ),
            answer=answer_text,
            evidence=evidence,
            model=generation.model,
            prompt_preview=verified_prompt,
            note=self._build_generation_note(
                included_image_count=included_image_count,
                evidence_count=len(evidence),
                retrieval_attempted=retrieval_attempted,
            ),
            stats={
                "retrieval_attempted": retrieval_attempted,
                "paper_scope_count": paper_scope_count,
                "evidence_count": len(evidence),
                "included_image_count": included_image_count,
            },
            limits=self._response_limits(
                evidence_count=len(evidence),
                retrieval_attempted=retrieval_attempted,
                included_image_count=included_image_count,
            ),
        )

    async def answer_stream(self, request: ChatRequest) -> AsyncGenerator[str | dict[str, Any], None]:
        """Stream chat response as SSE-compatible chunks.

        Yields, in order:
        1. One dict with key ``evidence_ready`` as soon as retrieval finishes.
        2. str tokens during LLM generation.
        3. One final dict with keys ``answer``, ``evidence``, ``note``, ``stats``,
           and optionally ``summary_message`` when generation is complete.
        """
        paper_scope_count = len(request.paper_ids or [])
        evidence, retrieval_attempted = await self._do_retrieval(request)

        # ── Early evidence frame ──────────────────────────────────────────────
        yield {
            "evidence_ready": evidence,
            "note": self._build_retrieval_note(evidence, retrieval_attempted),
        }

        prompt, user_content = self._build_generation_content(
            request=request,
            evidence=evidence,
            retrieval_attempted=retrieval_attempted,
        )
        selected_messages = select_recent_conversation_messages(request.messages)
        messages = [
            {"role": "system", "content": PAPERMEMORY_SYSTEM_PROMPT},
            *[message.model_dump() for message in selected_messages],
            {"role": "user", "content": user_content.content},
        ]

        raw_tokens: list[str] = []
        async for token in self.model_gateway.generate_stream(
            messages=messages,
            model=request.model,
            base_url=request.base_url,
            api_key=request.api_key,
            temperature=request.temperature,
        ):
            raw_tokens.append(token)
            yield token

        full_text = "".join(raw_tokens)
        try:
            clean_answer = ModelGateway._strip_reasoning_traces(full_text)
        except Exception:
            clean_answer = full_text

        # ── Citation verification ─────────────────────────────────────────────
        clean_answer, removed_citations = self._verify_citations(clean_answer, evidence)

        # ── Conversation summarization ────────────────────────────────────────
        summary_message = await self._maybe_summarize(request)

        included_image_count = user_content.included_image_count
        yield {
            "answer": clean_answer,
            "evidence": evidence,
            "note": self._build_generation_note(
                included_image_count=included_image_count,
                evidence_count=len(evidence),
                retrieval_attempted=retrieval_attempted,
            ),
            "stats": {
                "retrieval_attempted": retrieval_attempted,
                "paper_scope_count": paper_scope_count,
                "evidence_count": len(evidence),
                "included_image_count": included_image_count,
                "removed_citations": removed_citations,
            },
            "summary_message": summary_message.model_dump() if summary_message else None,
        }

    # ── Retrieval helpers ──────────────────────────────────────────────────────

    async def _do_retrieval(self, request: ChatRequest) -> tuple[list[PageEvidence], bool]:
        """Run retrieval with query rewriting and automatic zero-result retry.

        Returns ``(evidence, retrieval_attempted)``.

        Query building order:
        1. If ``enable_agentic_retrieval`` is set, ask the LLM for a bounded
           list of search queries and execute only those search actions.
        2. If planning fails, fall back to query rewrite or conversational
           concatenation.

        On zero results a second pass runs with the bare question and no score
        threshold to maximise recall for ambiguous follow-up questions.
        """
        if not request.paper_ids:
            return [], False

        effective_max_per_paper = request.max_per_paper
        if effective_max_per_paper is None and len(request.paper_ids) > 1:
            effective_max_per_paper = math.ceil(request.top_k / len(request.paper_ids))

        planned_queries = (
            await self._plan_retrieval_queries(request)
            if request.enable_agentic_retrieval
            else None
        )

        if planned_queries:
            evidence: list[PageEvidence] = []
            for retrieval_query in planned_queries:
                evidence.extend(
                    await self._search_retrieval_query(
                        request=request,
                        retrieval_query=retrieval_query,
                        max_per_paper=effective_max_per_paper,
                    )
                )
            evidence = self._dedupe_and_rank_evidence(evidence, top_k=request.top_k)
        else:
            retrieval_query = await self._fallback_retrieval_query(request)
            evidence = await self._search_retrieval_query(
                request=request,
                retrieval_query=retrieval_query,
                max_per_paper=effective_max_per_paper,
            )

        # Zero-result retry: always use the bare question here to maximise
        # recall — drop the rewritten/enriched query and the score threshold.
        if not evidence:
            bare_embedding = await self.visrag.embed_query(request.question)
            evidence = await self.vector_store.search_pages(
                embedding=bare_embedding.vector,
                top_k=request.top_k,
                paper_ids=request.paper_ids,
            )

        return evidence, True

    async def _plan_retrieval_queries(self, request: ChatRequest) -> list[str] | None:
        """Ask the LLM for bounded retrieval queries and validate the result."""
        try:
            prompt = build_agentic_retrieval_prompt(request.question, request.messages)
            response = await self.model_gateway.generate(
                messages=[
                    {"role": "system", "content": AGENTIC_RETRIEVAL_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                model=request.model,
                base_url=request.base_url,
                api_key=request.api_key,
                temperature=0,
            )
            return self._parse_planned_queries(response.text)
        except Exception:
            return None

    async def _fallback_retrieval_query(self, request: ChatRequest) -> str:
        if request.enable_query_rewrite and len(request.messages) >= 2:
            return await self._rewrite_query(request)
        return build_conversational_query(
            question=request.question,
            messages=request.messages,
        )

    async def _search_retrieval_query(
        self,
        request: ChatRequest,
        retrieval_query: str,
        max_per_paper: int | None,
    ) -> list[PageEvidence]:
        query_embedding = await self.visrag.embed_query(retrieval_query)
        return await self.vector_store.search_pages(
            embedding=query_embedding.vector,
            top_k=request.top_k,
            paper_ids=request.paper_ids,
            score_threshold=request.score_threshold,
            max_per_paper=max_per_paper,
        )

    @classmethod
    def _parse_planned_queries(cls, text: str) -> list[str] | None:
        payload = cls._load_json_object(text)
        if not isinstance(payload, dict):
            return None
        raw_queries = payload.get("queries")
        if not isinstance(raw_queries, list):
            return None

        queries: list[str] = []
        seen: set[str] = set()
        for raw_item in raw_queries:
            if isinstance(raw_item, str):
                raw_query = raw_item
            elif isinstance(raw_item, dict):
                raw_query = raw_item.get("query") or raw_item.get("search_query")
            else:
                raw_query = None

            if not isinstance(raw_query, str):
                continue
            query = " ".join(raw_query.split())[:AGENTIC_RETRIEVAL_MAX_QUERY_CHARS].strip()
            dedupe_key = query.lower()
            if query and dedupe_key not in seen:
                queries.append(query)
                seen.add(dedupe_key)
            if len(queries) >= AGENTIC_RETRIEVAL_MAX_QUERIES:
                break

        return queries or None

    @staticmethod
    def _load_json_object(text: str) -> Any:
        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
            stripped = re.sub(r"\s*```$", "", stripped)
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
            if not match:
                raise
            return json.loads(match.group(0))

    @staticmethod
    def _dedupe_and_rank_evidence(
        evidence: list[PageEvidence],
        top_k: int,
    ) -> list[PageEvidence]:
        best_by_page: dict[tuple[str, int], PageEvidence] = {}
        for item in evidence:
            key = (item.paper_id, item.page_number)
            previous = best_by_page.get(key)
            if previous is None or item.score > previous.score:
                best_by_page[key] = item

        return sorted(best_by_page.values(), key=lambda item: item.score, reverse=True)[:top_k]

    async def _rewrite_query(self, request: ChatRequest) -> str:
        """Ask the LLM to rewrite the question as a standalone retrieval query.

        Resolves pronouns and co-references so the embedding captures the
        actual topic rather than an underspecified follow-up fragment like
        "what about the limitations?".

        Falls back to the original question on any error so retrieval is
        never blocked by a rewriting failure.
        """
        try:
            prompt = build_query_rewrite_prompt(request.question, request.messages)
            response = await self.model_gateway.generate(
                messages=[
                    {"role": "system", "content": QUERY_REWRITE_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                model=request.model,
                base_url=request.base_url,
                api_key=request.api_key,
                temperature=0,
            )
            rewritten = response.text.strip()
            return rewritten if rewritten else request.question
        except Exception:
            return request.question

    # ── Citation verification ──────────────────────────────────────────────────

    @staticmethod
    def _verify_citations(
        answer: str,
        evidence: list[PageEvidence],
    ) -> tuple[str, list[str]]:
        """Remove citations for pages absent from the retrieved evidence.

        Only inspects citations whose ``paper_id`` appears in the evidence set,
        so general references to papers outside the active scope are left
        untouched.  Hallucinated page numbers for a known paper are stripped and
        recorded so callers can surface them in stats.

        Returns:
            (verified_answer, list_of_removed_citation_strings)
        """
        if not evidence:
            return answer, []

        valid_pairs = {(e.paper_id, e.page_number) for e in evidence}
        # Sort longest IDs first to prevent a shorter ID from being matched as a
        # prefix of a longer one during regex alternation.
        known_ids = sorted({e.paper_id for e in evidence}, key=len, reverse=True)
        escaped = "|".join(re.escape(pid) for pid in known_ids)
        if not escaped:
            return answer, []

        pattern = re.compile(rf'\b({escaped})\s+p\.(\d+)\b')
        removed: list[str] = []

        def check(m: re.Match) -> str:  # type: ignore[type-arg]
            pid, page = m.group(1), int(m.group(2))
            if (pid, page) in valid_pairs:
                return m.group(0)
            removed.append(f"{pid} p.{page}")
            return ""

        verified = pattern.sub(check, answer)
        # Collapse consecutive spaces left by removed inline citations.
        verified = re.sub(r" {2,}", " ", verified).strip()
        return verified, removed

    # ── Summarization helpers ──────────────────────────────────────────────────

    @staticmethod
    def _needs_summarization(messages: list[ChatMessage]) -> bool:
        """True when history exceeds the context window and has no existing summary."""
        if len(messages) <= RECENT_CONVERSATION_MESSAGE_LIMIT:
            return False
        return not (
            messages[0].role == "assistant"
            and messages[0].content.startswith("[Summary]")
        )

    async def _maybe_summarize(self, request: ChatRequest) -> ChatMessage | None:
        """Generate a [Summary] message for older turns if the history is long.

        Called after the main generation so it adds no latency to the first
        token.  Returns None silently on any error.
        """
        if not self._needs_summarization(request.messages):
            return None
        try:
            cutoff = -(RECENT_CONVERSATION_MESSAGE_LIMIT - 1)
            older = list(request.messages[:cutoff])
            _, summary_prompt = compress_conversation_history(older)
            response = await self.model_gateway.generate(
                messages=[{"role": "user", "content": summary_prompt}],
                model=request.model,
                base_url=request.base_url,
                api_key=request.api_key,
                temperature=0,
            )
            return ChatMessage(role="assistant", content=f"[Summary] {response.text}")
        except Exception:
            return None

    # ── Prompt / context helpers ───────────────────────────────────────────────

    def build_evisrag_prompt(
        self,
        question: str,
        evidence: list[PageEvidence],
        retrieval_attempted: bool = False,
        include_captions: bool = True,
    ) -> str:
        return build_context_prompt(
            question=question,
            evidence=evidence,
            retrieval_attempted=retrieval_attempted,
            include_captions=include_captions,
        )

    def _build_generation_content(
        self,
        request: ChatRequest,
        evidence: list[PageEvidence],
        retrieval_attempted: bool,
    ) -> tuple[str, BuiltUserContent]:
        wants_image_context = self._wants_image_context(request)
        prompt = self.build_evisrag_prompt(
            question=request.question,
            evidence=evidence,
            retrieval_attempted=retrieval_attempted,
            include_captions=not wants_image_context,
        )
        user_content = self.model_gateway.build_user_content(
            text=prompt,
            image_paths=self._resolve_authorized_image_paths(evidence),
            enable_image_context=request.enable_image_context,
            max_evidence_images=request.max_evidence_images,
        )

        if evidence and wants_image_context and user_content.included_image_count == 0:
            prompt = self.build_evisrag_prompt(
                question=request.question,
                evidence=evidence,
                retrieval_attempted=retrieval_attempted,
                include_captions=True,
            )
            user_content = self.model_gateway.build_user_content(
                text=prompt,
                image_paths=[],
                enable_image_context=False,
                max_evidence_images=0,
            )

        return prompt, user_content

    def _wants_image_context(self, request: ChatRequest) -> bool:
        enable_image_context = (
            getattr(self.model_gateway, "enable_image_context", False)
            if request.enable_image_context is None
            else request.enable_image_context
        )
        max_evidence_images = (
            getattr(self.model_gateway, "max_evidence_images", 0)
            if request.max_evidence_images is None
            else request.max_evidence_images
        )
        return bool(enable_image_context and max_evidence_images > 0)

    @staticmethod
    def _build_retrieval_note(evidence: list[PageEvidence], retrieval_attempted: bool) -> str:
        """Note emitted in the early evidence SSE frame, before generation."""
        if not retrieval_attempted:
            return "Conversation mode — no paper scope active."
        if not evidence:
            return "Retrieval found no matching pages after retry. Generating without paper evidence."
        return f"Retrieved {len(evidence)} page(s) of evidence. Generating answer…"

    @staticmethod
    def _response_status(evidence_count: int, retrieval_attempted: bool) -> str:
        if retrieval_attempted and evidence_count == 0:
            return "partial"
        return "success"

    @staticmethod
    def _response_limits(
        evidence_count: int,
        retrieval_attempted: bool,
        included_image_count: int,
    ) -> list[str]:
        if evidence_count == 0:
            if retrieval_attempted:
                return [NO_SCOPED_EVIDENCE_LIMIT]
            return [CONVERSATION_MODE_LIMIT]
        if included_image_count == 0:
            return [TEXT_ONLY_EVIDENCE_LIMIT]
        return []

    @staticmethod
    def _build_generation_note(
        included_image_count: int,
        evidence_count: int,
        retrieval_attempted: bool,
    ) -> str:
        if evidence_count == 0:
            if retrieval_attempted:
                return "Generation request used scoped paper retrieval, but no evidence was returned."
            return "Generation request used conversation mode without retrieved paper evidence."
        if included_image_count > 0:
            return f"Generation request included {included_image_count} retrieved page image(s)."
        return "Generation request used text-only evidence context."

    def _resolve_authorized_image_paths(self, evidence: list[PageEvidence]) -> list[str]:
        if self.page_image_resolver is None:
            return []

        image_paths: list[str] = []
        for item in evidence:
            image_path = self.page_image_resolver.resolve_evidence_image_path(item)
            if image_path is not None:
                image_paths.append(image_path)
        return image_paths
