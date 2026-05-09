from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.retrieval import PageEvidence
from app.services.model_gateway import ModelGateway
from app.services.vector_store import VectorStore
from app.services.visrag_service import VisRAGService


class ChatService:
    """Coordinates retrieval and answer generation with visual page evidence."""

    def __init__(
        self,
        visrag: VisRAGService,
        vector_store: VectorStore,
        model_gateway: ModelGateway,
    ) -> None:
        self.visrag = visrag
        self.vector_store = vector_store
        self.model_gateway = model_gateway

    async def answer(self, request: ChatRequest) -> ChatResponse:
        query_embedding = await self.visrag.embed_query(request.question)
        evidence = await self.vector_store.search_pages(
            embedding=query_embedding.vector,
            top_k=request.top_k,
            paper_ids=request.paper_ids,
        )
        prompt = self.build_evisrag_prompt(question=request.question, evidence=evidence)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are PaperMemory, a local-first research assistant. Answer only from "
                    "provided evidence when possible and cite page-level visual evidence."
                ),
            },
            *[message.model_dump() for message in request.messages],
            {"role": "user", "content": prompt},
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
            note="Generation is stubbed until a BYOK OpenAI-compatible provider is configured.",
        )

    def build_evisrag_prompt(self, question: str, evidence: list[PageEvidence]) -> str:
        evidence_block = "\n".join(
            (
                f"- paper_id={item.paper_id}, page={item.page_number}, "
                f"score={item.score:.4f}, image_path={item.image_path or 'unavailable'}, "
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
