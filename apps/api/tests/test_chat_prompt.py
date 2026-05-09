from app.schemas.retrieval import PageEvidence
from app.services.chat_service import ChatService


def test_evisrag_prompt_mentions_page_evidence() -> None:
    service = ChatService(visrag=None, vector_store=None, model_gateway=None)  # type: ignore[arg-type]

    prompt = service.build_evisrag_prompt(
        question="What does the ablation table show?",
        evidence=[
            PageEvidence(
                paper_id="paper-1",
                page_number=7,
                score=0.91,
                image_path=".papermemory/rendered_pages/paper-1/page-0007.png",
                caption="Ablation results",
            )
        ],
    )

    assert "EVisRAG-style" in prompt
    assert "paper_id=paper-1" in prompt
    assert "page=7" in prompt
