import asyncio
import json
from unittest.mock import patch
from app.core.config import Settings
from app.services.model_gateway import ModelGateway, ModelGatewayError


def _make_settings(base_url: str = "http://fake-provider.local/v1", api_key: str = "test-key") -> Settings:
    return Settings(
        byok_base_url=base_url,
        byok_api_key=api_key,
        byok_model="test-model",
        qdrant_mode="local",
    )


class FakeAiterLines:
    """Async iterator that yields a fixed list of SSE lines."""

    def __init__(self, lines: list[str]) -> None:
        self._lines = iter(lines)

    def __aiter__(self):
        return self

    async def __anext__(self) -> str:
        try:
            return next(self._lines)
        except StopIteration:
            raise StopAsyncIteration


class FakeStreamResponse:
    status_code = 200

    def __init__(self, lines: list[str]) -> None:
        self._lines = lines

    def raise_for_status(self) -> None:
        pass

    def aiter_lines(self) -> FakeAiterLines:
        return FakeAiterLines(self._lines)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class FakeHttpxClient:
    def __init__(self, lines: list[str]) -> None:
        self._response = FakeStreamResponse(lines)

    def stream(self, method: str, url: str, **kwargs):
        return self._response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


def _sse(content: str) -> str:
    return f"data: {json.dumps({'choices': [{'delta': {'content': content}}]})}"


def test_generate_stream_yields_deltas():
    """generate_stream() yields each delta content token from SSE lines."""
    async def run():
        gateway = ModelGateway(_make_settings())
        lines = [_sse("Hello"), _sse(", "), _sse("world"), "data: [DONE]"]
        with patch("httpx.AsyncClient", return_value=FakeHttpxClient(lines)):
            tokens = []
            async for token in gateway.generate_stream(messages=[{"role": "user", "content": "hi"}]):
                tokens.append(token)
        assert tokens == ["Hello", ", ", "world"]

    asyncio.run(run())


def test_generate_stream_skips_empty_deltas():
    """generate_stream() does not yield empty-string deltas."""
    async def run():
        gateway = ModelGateway(_make_settings())
        lines = [_sse("A"), _sse(""), _sse("B"), "data: [DONE]"]
        with patch("httpx.AsyncClient", return_value=FakeHttpxClient(lines)):
            tokens = []
            async for token in gateway.generate_stream(messages=[{"role": "user", "content": "hi"}]):
                tokens.append(token)
        assert tokens == ["A", "B"]

    asyncio.run(run())


def test_generate_stream_unconfigured_yields_error_message():
    """generate_stream() yields a single error message when not configured."""
    async def run():
        gateway = ModelGateway(Settings(
            byok_base_url=None,
            byok_api_key=None,
            byok_model="test-model",
            qdrant_mode="local",
        ))
        tokens = []
        async for token in gateway.generate_stream(messages=[{"role": "user", "content": "hi"}]):
            tokens.append(token)
        assert len(tokens) == 1
        assert "not configured" in tokens[0]

    asyncio.run(run())
