import math
from collections.abc import AsyncGenerator
from typing import Any

from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.retrieval import PageEvidence
from app.services.context_builder import PAPERMEMORY_SYSTEM_PROMPT
from app.services.context_builder import build_evisrag_prompt as build_context_prompt
from app.services.context_builder import build_conversational_query
from app.services.context_builder import select_recent_conversation_messages
from app.services.model_gateway import ModelGateway
from app.services.page_image_resolver import PageImageResolver
from app.services.vector_store import VectorStore
from app.services.visrag_service import VisRAGService

CONVERSATION_MODE_LIMIT = "No retrieved paper evidence is available; this response is not paper-grounded."
NO_SCOPED_EVIDENCE_LIMIT = "Scoped retrieval returned no evidence; no paper citations are available."
TEXT_ONLY_EVIDENCE_LIMIT = "Text-only evidence context; no page images were included."


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
        if not request.paper_ids:
            evidence: list[PageEvidence] = []
            retrieval_attempted = False
            prompt = self.build_evisrag_prompt(
                question=request.question,
                evidence=evidence,
                retrieval_attempted=retrieval_attempted,
            )
        else:
            retrieval_attempted = True

            # Multi-turn query enhancement: incorporate recent conversation
            # context into the query vector so follow-up questions ("how does
            # that compare to the baseline?") retrieve the right pages even
            # when the current question is underspecified.
            # Industry reference: conversational RAG query rewriting (MaFeRw 2024).
            conversational_query = build_conversational_query(
                question=request.question,
                messages=request.messages,
            )
            query_embedding = await self.visrag.embed_query(conversational_query)

            # Compute a sensible per-paper cap when not explicitly supplied.
            # If 3 papers are in scope and top_k=6, cap each at 2 to ensure
            # all papers have a fair chance at representation.
            effective_max_per_paper = request.max_per_paper
            if effective_max_per_paper is None and request.paper_ids and len(request.paper_ids) > 1:
                effective_max_per_paper = math.ceil(request.top_k / len(request.paper_ids))

            evidence = await self.vector_store.search_pages(
                embedding=query_embedding.vector,
                top_k=request.top_k,
                paper_ids=request.paper_ids,
                score_threshold=request.score_threshold,
                max_per_paper=effective_max_per_paper,
            )
            prompt = self.build_evisrag_prompt(
                question=request.question,
                evidence=evidence,
                retrieval_attempted=retrieval_attempted,
            )

        user_content = self.model_gateway.build_user_content(
            text=prompt,
            image_paths=self._resolve_authorized_image_paths(evidence),
            enable_image_context=request.enable_image_context,
            max_evidence_images=request.max_evidence_images,
        )
        selected_messages = select_recent_conversation_messages(request.messages)
        messages = [
            {
                "role": "system",
                "content": PAPERMEMORY_SYSTEM_PROMPT,
            },
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

        included_image_count = user_content.included_image_count
        return ChatResponse(
            status=self._response_status(
                evidence_count=len(evidence),
                retrieval_attempted=retrieval_attempted,
            ),
            answer=generation.text,
            evidence=evidence,
            model=generation.model,
            prompt_preview=prompt,
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

        Yields str tokens during generation, then one final dict with keys
        'answer', 'evidence', 'note', and 'stats' when generation is complete.
        The final 'answer' value has leading reasoning traces stripped.
        """
        paper_scope_count = len(request.paper_ids or [])
        if not request.paper_ids:
            evidence: list[PageEvidence] = []
            retrieval_attempted = False
            prompt = self.build_evisrag_prompt(
                question=request.question,
                evidence=evidence,
                retrieval_attempted=retrieval_attempted,
            )
        else:
            retrieval_attempted = True
            conversational_query = build_conversational_query(
                question=request.question,
                messages=request.messages,
            )
            query_embedding = await self.visrag.embed_query(conversational_query)
            effective_max_per_paper = request.max_per_paper
            if effective_max_per_paper is None and request.paper_ids and len(request.paper_ids) > 1:
                effective_max_per_paper = math.ceil(request.top_k / len(request.paper_ids))
            evidence = await self.vector_store.search_pages(
                embedding=query_embedding.vector,
                top_k=request.top_k,
                paper_ids=request.paper_ids,
                score_threshold=request.score_threshold,
                max_per_paper=effective_max_per_paper,
            )
            prompt = self.build_evisrag_prompt(
                question=request.question,
                evidence=evidence,
                retrieval_attempted=retrieval_attempted,
            )

        user_content = self.model_gateway.build_user_content(
            text=prompt,
            image_paths=self._resolve_authorized_image_paths(evidence),
            enable_image_context=request.enable_image_context,
            max_evidence_images=request.max_evidence_images,
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
            },
        }

    def build_evisrag_prompt(
        self,
        question: str,
        evidence: list[PageEvidence],
        retrieval_attempted: bool = False,
    ) -> str:
        return build_context_prompt(
            question=question,
            evidence=evidence,
            retrieval_attempted=retrieval_attempted,
        )

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
