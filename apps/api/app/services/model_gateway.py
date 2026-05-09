from typing import Any

from fastapi import HTTPException, status
import httpx
from pydantic import BaseModel

from app.core.config import Settings


class GenerationRequest(BaseModel):
    model: str
    messages: list[dict[str, str]]
    base_url: str | None = None
    api_key: str | None = None
    temperature: float = 0.2


class GenerationResponse(BaseModel):
    text: str
    model: str


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

    async def generate(
        self,
        messages: list[dict[str, str]],
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
        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
        }
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

    def _extract_text(self, data: dict[str, Any]) -> str:
        try:
            choice = data["choices"][0]
            message = choice.get("message") or {}
            content = message.get("content")
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise ModelGatewayError("response did not include choices[0].message.content") from exc

        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = [
                str(part.get("text"))
                for part in content
                if isinstance(part, dict) and part.get("type") in {"text", "output_text"} and part.get("text")
            ]
            if parts:
                return "\n".join(parts)
        raise ModelGatewayError("response content was empty or unsupported")

    @staticmethod
    def _safe_provider_error(response: httpx.Response) -> str:
        try:
            data = response.json()
        except ValueError:
            data = response.text

        text = str(data)
        return text[:500]
