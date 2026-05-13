from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.retrieval import PageEvidence
from app.services.model_gateway import ModelGateway
from app.services.page_image_resolver import PageImageResolver
from app.services.vector_store import VectorStore
from app.services.visrag_service import VisRAGService


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
        if request.paper_ids == []:
            evidence: list[PageEvidence] = []
            prompt = self.build_evisrag_prompt(question=request.question, evidence=evidence)
            return ChatResponse(
                answer=(
                    "No paper database scope is selected, so PaperMemory did not call the external "
                    "model provider. Upload and index papers in the active database, then ask again."
                ),
                evidence=evidence,
                model=request.model or self.model_gateway.model,
                prompt_preview=prompt,
                note="No paper scope selected; BYOK generation was skipped.",
            )
        else:
            query_embedding = await self.visrag.embed_query(request.question)
            evidence = await self.vector_store.search_pages(
                embedding=query_embedding.vector,
                top_k=request.top_k,
                paper_ids=request.paper_ids,
            )
        prompt = self.build_evisrag_prompt(question=request.question, evidence=evidence)

        user_content = self.model_gateway.build_user_content(
            text=prompt,
            image_paths=self._resolve_authorized_image_paths(evidence),
            enable_image_context=request.enable_image_context,
            max_evidence_images=request.max_evidence_images,
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "You are PaperMemory, a local-first research assistant. Answer only from "
                    "provided evidence when possible and cite page-level visual evidence."
                ),
            },
            *[message.model_dump() for message in request.messages],
            {"role": "user", "content": user_content.content},
        ]
        generation = await self.model_gateway.generate(
            messages=messages,
            model=request.model,
            base_url=request.base_url,
            api_key=request.api_key,
            temperature=request.temperature,
        )

        return ChatResponse(
            answer=generation.text,
            evidence=evidence,
            model=generation.model,
            prompt_preview=prompt,
            note=self._build_generation_note(user_content.included_image_count),
        )

    def build_evisrag_prompt(self, question: str, evidence: list[PageEvidence]) -> str:
        evidence_block = "\n".join(
            (
                f"- paper_id={item.paper_id}, page={item.page_number}, "
                f"score={item.score:.4f}, image_ref={self._evidence_image_reference(item)}, "
                f"caption={item.caption or 'none'}"
            )
            for item in evidence
        )
        if not evidence_block:
            evidence_block = "- No retrieved page evidence yet."

        return (
            "Use an EVisRAG-style evidence-first workflow:\n"
            "1. Inspect the retrieved page images and metadata before answering.\n"
            "2. Ground claims in page-level evidence, including figures, tables, equations, and captions.\n"
            "3. Say when evidence is missing or insufficient.\n\n"
            f"Question:\n{question}\n\n"
            f"Retrieved visual evidence:\n{evidence_block}"
        )

    @staticmethod
    def _build_generation_note(included_image_count: int) -> str:
        if included_image_count > 0:
            return f"Generation request included {included_image_count} retrieved page image(s)."
        return "Generation request used text-only evidence context."

    @staticmethod
    def _evidence_image_reference(item: PageEvidence) -> str:
        image_url = getattr(item, "image_url", None)
        if image_url:
            return str(image_url)
        return f"paper_id={item.paper_id}, page={item.page_number}"

    def _resolve_authorized_image_paths(self, evidence: list[PageEvidence]) -> list[str]:
        if self.page_image_resolver is None:
            return []

        image_paths: list[str] = []
        for item in evidence:
            image_path = self.page_image_resolver.resolve_evidence_image_path(item)
            if image_path is not None:
                image_paths.append(image_path)
        return image_paths
