from dataclasses import dataclass
import base64
import mimetypes
from pathlib import Path
import re
from typing import Any

from fastapi import HTTPException, status
import httpx
from pydantic import BaseModel

from app.core.config import Settings

ChatCompletionMessage = dict[str, Any]
MessageContent = str | list[dict[str, Any]]
SUPPORTED_IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/webp"}
LEADING_THINK_BLOCK_PATTERN = re.compile(r"\A\s*<think\b[^>]*>.*?</think>\s*", flags=re.IGNORECASE | re.DOTALL)
LEADING_OPEN_THINK_PATTERN = re.compile(r"\A\s*<think\b[^>]*>", flags=re.IGNORECASE | re.DOTALL)


class GenerationRequest(BaseModel):
    model: str
    messages: list[ChatCompletionMessage]
    base_url: str | None = None
    api_key: str | None = None
    temperature: float = 0.2


class GenerationResponse(BaseModel):
    text: str
    model: str


@dataclass(frozen=True)
class BuiltUserContent:
    content: MessageContent
    included_image_count: int


class ModelGatewayError(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_502_BAD_GATEWAY) -> None:
        super().__init__(status_code=status_code, detail=f"Model provider error: {detail}")


class ModelGateway:
    """OpenAI-compatible BYOK adapter.

    Never log raw API keys, Authorization headers, or provider responses that may echo secrets.
    Add structured redaction before introducing request logging or tracing.
    """

    def __init__(self, settings: Settings) -> None:
        self.base_url = str(settings.byok_base_url) if settings.byok_base_url else None
        self.api_key = settings.byok_api_key
        self.model = settings.byok_model
        self.timeout_seconds = settings.byok_timeout_seconds
        self.enable_image_context = settings.byok_enable_image_context
        self.max_evidence_images = settings.byok_max_evidence_images
        self.max_image_bytes = settings.byok_max_image_bytes

    async def generate(
        self,
        messages: list[ChatCompletionMessage],
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.2,
    ) -> GenerationResponse:
        target_model = model or self.model
        target_base_url = base_url or self.base_url
        target_api_key = api_key or self.api_key

        if not target_base_url or not target_api_key:
            return GenerationResponse(
                text=(
                    "BYOK model gateway is not configured yet. Add a provider base URL and API key "
                    "in setup or model settings, then retry this question."
                ),
                model=target_model,
            )

        url = f"{target_base_url.rstrip('/')}/chat/completions"
        payload = self.build_chat_completions_payload(
            messages=messages,
            model=target_model,
            temperature=temperature,
        )
        headers = {
            "Authorization": f"Bearer {target_api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            provider_detail = self._safe_provider_error(exc.response)
            raise ModelGatewayError(
                f"provider returned HTTP {exc.response.status_code}: {provider_detail}",
                status_code=status.HTTP_502_BAD_GATEWAY,
            ) from exc
        except httpx.RequestError as exc:
            raise ModelGatewayError(f"request failed: {exc.__class__.__name__}") from exc

        data = response.json()
        text = self._extract_text(data)
        response_model = str(data.get("model") or target_model)
        return GenerationResponse(text=text, model=response_model)

    def build_user_content(
        self,
        text: str,
        image_paths: list[str],
        enable_image_context: bool | None = None,
        max_evidence_images: int | None = None,
    ) -> BuiltUserContent:
        use_image_context = self.enable_image_context if enable_image_context is None else enable_image_context
        image_limit = self.max_evidence_images if max_evidence_images is None else max_evidence_images

        if not use_image_context or image_limit <= 0:
            return BuiltUserContent(content=text, included_image_count=0)

        parts: list[dict[str, Any]] = [{"type": "text", "text": text}]
        included = 0
        for image_path in image_paths:
            if included >= image_limit:
                break
            data_url = self._image_file_to_data_url(image_path)
            if not data_url:
                continue
            parts.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": data_url,
                    },
                }
            )
            included += 1

        if included == 0:
            return BuiltUserContent(content=text, included_image_count=0)
        return BuiltUserContent(content=parts, included_image_count=included)

    @staticmethod
    def build_chat_completions_payload(
        messages: list[ChatCompletionMessage],
        model: str,
        temperature: float,
    ) -> dict[str, Any]:
        return {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

    def _extract_text(self, data: dict[str, Any]) -> str:
        try:
            choice = data["choices"][0]
            message = choice.get("message") or {}
            content = message.get("content")
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise ModelGatewayError("response did not include choices[0].message.content") from exc

        if isinstance(content, str):
            return self._strip_reasoning_traces(content)
        if isinstance(content, list):
            parts = [
                str(part.get("text"))
                for part in content
                if isinstance(part, dict) and part.get("type") in {"text", "output_text"} and part.get("text")
            ]
            if parts:
                return self._strip_reasoning_traces("\n".join(parts))
        raise ModelGatewayError("response content was empty or unsupported")

    @staticmethod
    def _strip_reasoning_traces(text: str) -> str:
        remaining = text
        stripped_reasoning = False

        while match := LEADING_THINK_BLOCK_PATTERN.match(remaining):
            remaining = remaining[match.end() :]
            stripped_reasoning = True

        if LEADING_OPEN_THINK_PATTERN.match(remaining):
            raise ModelGatewayError("provider returned malformed hidden reasoning without a user-visible answer")

        visible_text = remaining.strip()
        if stripped_reasoning and not visible_text:
            raise ModelGatewayError("provider returned only hidden reasoning without a user-visible answer")
        if not visible_text:
            raise ModelGatewayError("response content was empty or unsupported")
        return visible_text

    @staticmethod
    def _safe_provider_error(response: httpx.Response) -> str:
        try:
            data = response.json()
        except ValueError:
            data = response.text

        text = str(data)
        return text[:500]

    def _image_file_to_data_url(self, image_path: str) -> str | None:
        path = Path(image_path)
        if not path.is_file():
            return None

        image_size = path.stat().st_size
        if image_size <= 0 or image_size > self.max_image_bytes:
            return None

        mime_type, _ = mimetypes.guess_type(path.name)
        if mime_type not in SUPPORTED_IMAGE_MIME_TYPES:
            return None

        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"
