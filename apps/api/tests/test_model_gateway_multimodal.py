import json

import pytest

from app.core.config import Settings
from app.services.model_gateway import ModelGateway, ModelGatewayError


def test_build_user_content_returns_text_only_when_image_context_disabled(tmp_path) -> None:
    image_path = tmp_path / "page-0001.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    gateway = ModelGateway(Settings(byok_enable_image_context=False))

    built = gateway.build_user_content(
        text="Use this evidence.",
        image_paths=[str(image_path)],
    )
    payload = gateway.build_chat_completions_payload(
        model="vision-model",
        temperature=0.2,
        messages=[{"role": "user", "content": built.content}],
    )

    assert built.included_image_count == 0
    assert payload["messages"][0]["content"] == "Use this evidence."


def test_build_user_content_adds_image_data_url_without_local_path(tmp_path) -> None:
    image_path = tmp_path / "page-0001.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    gateway = ModelGateway(Settings(byok_enable_image_context=True, byok_max_evidence_images=1))

    built = gateway.build_user_content(
        text="Use this evidence.",
        image_paths=[str(image_path)],
    )
    payload = gateway.build_chat_completions_payload(
        model="vision-model",
        temperature=0.2,
        messages=[{"role": "user", "content": built.content}],
    )
    content = payload["messages"][0]["content"]
    serialized_payload = json.dumps(payload)

    assert built.included_image_count == 1
    assert content[0] == {"type": "text", "text": "Use this evidence."}
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")
    assert str(image_path) not in serialized_payload


def test_build_user_content_skips_oversized_images(tmp_path) -> None:
    image_path = tmp_path / "page-0001.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    gateway = ModelGateway(
        Settings(
            byok_enable_image_context=True,
            byok_max_evidence_images=1,
            byok_max_image_bytes=4,
        )
    )

    built = gateway.build_user_content(
        text="Use this evidence.",
        image_paths=[str(image_path)],
    )

    assert built.included_image_count == 0
    assert built.content == "Use this evidence."


def test_extract_text_strips_provider_reasoning_traces() -> None:
    gateway = ModelGateway(Settings())

    text = gateway._extract_text(
        {
            "choices": [
                {
                    "message": {
                        "content": (
                            "<think>I should inspect pages and plan the answer.</think>\n"
                            "**Answer**\nPan frames LLMs and KGs as complementary."
                        )
                    }
                }
            ]
        }
    )

    assert text == "**Answer**\nPan frames LLMs and KGs as complementary."
    assert "<think>" not in text
    assert "inspect pages" not in text


def test_extract_text_strips_multiple_leading_reasoning_traces() -> None:
    gateway = ModelGateway(Settings())

    text = gateway._extract_text(
        {
            "choices": [
                {
                    "message": {
                        "content": (
                            "<think>Plan evidence.</think>\n"
                            "<think>Check citation shape.</think>\n"
                            "**Answer**\nUse `paper_id p.2`."
                        )
                    }
                }
            ]
        }
    )

    assert text == "**Answer**\nUse `paper_id p.2`."


def test_extract_text_keeps_literal_think_tags_inside_answer() -> None:
    gateway = ModelGateway(Settings())

    text = gateway._extract_text(
        {
            "choices": [
                {
                    "message": {
                        "content": "The paper discusses <think> tags as literal markup, not reasoning."
                    }
                }
            ]
        }
    )

    assert text == "The paper discusses <think> tags as literal markup, not reasoning."


def test_extract_text_rejects_closed_think_only_response() -> None:
    gateway = ModelGateway(Settings())

    with pytest.raises(ModelGatewayError) as exc_info:
        gateway._extract_text(
            {
                "choices": [
                    {
                        "message": {
                            "content": "  <think>I should inspect pages and plan the answer.</think>\n"
                        }
                    }
                ]
            }
        )

    assert "only hidden reasoning" in exc_info.value.detail


def test_extract_text_rejects_unclosed_leading_think_response() -> None:
    gateway = ModelGateway(Settings())

    with pytest.raises(ModelGatewayError) as exc_info:
        gateway._extract_text(
            {
                "choices": [
                    {
                        "message": {
                            "content": "<think>I should inspect pages and plan the answer."
                        }
                    }
                ]
            }
        )

    assert "malformed hidden reasoning" in exc_info.value.detail
