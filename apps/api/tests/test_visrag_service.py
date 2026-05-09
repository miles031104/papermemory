import asyncio
from pathlib import Path
from typing import Any

import pytest

from app.core.config import Settings
from app.services.visrag_service import VisRAGService, weighted_mean_pooling


class CaptureEncoder:
    def __init__(self, vector: list[float]) -> None:
        self.vector = vector
        self.calls: list[dict[str, Any]] = []

    def __call__(self, inputs: dict[str, Any]) -> list[list[float]]:
        self.calls.append(inputs)
        return [self.vector]


class FakeImage:
    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.converted_to: list[str] = []
        self.original: FakeImage | None = None

    def convert(self, mode: str) -> "FakeImage":
        self.converted_to.append(mode)
        converted = FakeImage(mode)
        converted.original = self
        return converted


class FakeTensor:
    def __init__(self, data: Any) -> None:
        self.data = data

    def cumsum(self, dim: int) -> "FakeTensor":
        assert dim == 1
        rows = []
        for row in self.data:
            running = 0
            cumsum_row = []
            for value in row:
                running += value
                cumsum_row.append(running)
            rows.append(cumsum_row)
        return FakeTensor(rows)

    def unsqueeze(self, dim: int) -> "FakeTensor":
        assert dim == -1
        return FakeTensor([[[value] for value in row] for row in self.data])

    def float(self) -> "FakeTensor":
        return self

    def sum(self, dim: int, keepdim: bool = False) -> "FakeTensor":
        assert dim == 1
        if self._rank() == 3:
            return FakeTensor(
                [
                    [
                        sum(token[column] for token in row)
                        for column in range(len(row[0]))
                    ]
                    for row in self.data
                ]
            )

        summed = [sum(row) for row in self.data]
        if keepdim:
            return FakeTensor([[value] for value in summed])
        return FakeTensor(summed)

    def __mul__(self, other: "FakeTensor") -> "FakeTensor":
        if self._rank() == 2 and other._rank() == 2:
            return FakeTensor(
                [
                    [left * right for left, right in zip(left_row, right_row)]
                    for left_row, right_row in zip(self.data, other.data)
                ]
            )
        if self._rank() == 3 and other._rank() == 3:
            return FakeTensor(
                [
                    [
                        [value * other.data[row_idx][token_idx][0] for value in token]
                        for token_idx, token in enumerate(row)
                    ]
                    for row_idx, row in enumerate(self.data)
                ]
            )
        raise AssertionError("unexpected fake tensor multiply")

    def __truediv__(self, other: "FakeTensor") -> "FakeTensor":
        return FakeTensor(
            [
                [value / other.data[row_idx][0] for value in row]
                for row_idx, row in enumerate(self.data)
            ]
        )

    def _rank(self) -> int:
        rank = 0
        value = self.data
        while isinstance(value, list):
            rank += 1
            value = value[0]
        return rank


class FakeTorch:
    @staticmethod
    def sum(tensor: FakeTensor, dim: int) -> FakeTensor:
        return tensor.sum(dim=dim)


def transformer_service(
    settings: Settings,
    encoder: CaptureEncoder,
    image_loader: Any | None = None,
) -> VisRAGService:
    service = VisRAGService(settings=settings, image_loader=image_loader)
    service._model = object()
    service._tokenizer = object()
    service._encode = encoder  # type: ignore[method-assign]
    return service


def test_stub_embeddings_follow_configured_vector_size_and_are_normalized() -> None:
    service = VisRAGService(Settings(qdrant_vector_size=5))

    result = asyncio.run(service.embed_query("layout-aware retrieval"))

    assert len(result.vector) == 5
    assert all(isinstance(value, float) for value in result.vector)
    assert sum(value * value for value in result.vector) == pytest.approx(1.0)


def test_query_instruction_prefix_is_passed_to_backend_exactly_once() -> None:
    settings = Settings(qdrant_vector_size=2, visrag_backend="transformers")
    encoder = CaptureEncoder([3, 4])
    service = transformer_service(settings, encoder)

    raw_result = asyncio.run(service.embed_query("What does the table show?"))
    prefixed_result = asyncio.run(
        service.embed_query(
            f"{settings.visrag_instruction} What does the figure show?"
        )
    )

    assert encoder.calls[0]["text"] == [
        f"{settings.visrag_instruction} What does the table show?"
    ]
    assert encoder.calls[0]["image"] == [None]
    assert encoder.calls[0]["tokenizer"] is service._tokenizer
    assert encoder.calls[1]["text"] == [
        f"{settings.visrag_instruction} What does the figure show?"
    ]
    assert encoder.calls[0]["text"][0].count(settings.visrag_instruction) == 1
    assert encoder.calls[1]["text"][0].count(settings.visrag_instruction) == 1
    assert raw_result.vector == pytest.approx([0.6, 0.8])
    assert prefixed_result.vector == pytest.approx([0.6, 0.8])


def test_transformers_image_embedding_loads_local_rgb_image_for_backend() -> None:
    image_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    opened_paths: list[Path] = []
    source_image = FakeImage("L")

    def load_image(path: Path) -> FakeImage:
        assert path.exists()
        opened_paths.append(path)
        return source_image

    settings = Settings(qdrant_vector_size=2, visrag_backend="transformers")
    encoder = CaptureEncoder([10, 0])
    service = transformer_service(settings, encoder, image_loader=load_image)

    result = asyncio.run(service.embed_page_image(str(image_path)))

    assert opened_paths == [image_path]
    backend_image = encoder.calls[0]["image"][0]
    assert backend_image.mode == "RGB"
    assert backend_image.original is source_image
    assert encoder.calls[0]["text"] == [""]
    assert result.vector == pytest.approx([1.0, 0.0])


def test_weighted_mean_pooling_matches_visrag_formula() -> None:
    hidden = FakeTensor(
        [
            [[1.0, 1.0], [3.0, 3.0], [100.0, 100.0]],
            [[2.0, 4.0], [4.0, 8.0], [6.0, 12.0]],
        ]
    )
    attention_mask = FakeTensor(
        [
            [1, 1, 0],
            [1, 1, 1],
        ]
    )

    pooled = weighted_mean_pooling(hidden, attention_mask, torch_module=FakeTorch)

    assert [value for row in pooled.data for value in row] == pytest.approx(
        [7.0 / 3.0, 7.0 / 3.0, 28.0 / 6.0, 56.0 / 6.0]
    )
