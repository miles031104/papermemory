import json

from app.core.config import Settings
from app.services.model_gateway import ModelGateway


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
