from collections.abc import Callable
from math import sqrt
from pathlib import Path
from typing import Any, Literal

from app.core.config import Settings
from pydantic import BaseModel


VisRAGBackend = Literal["stub", "transformers"]


class EmbeddingResult(BaseModel):
    vector: list[float]
    model: str
    instruction: str


class VisRAGUnavailable(RuntimeError):
    """Raised when the configured VisRAG backend cannot produce embeddings."""


class VisRAGService:
    """Boundary for VisRAG-Ret query and page-image embeddings."""

    def __init__(
        self,
        settings: Settings,
        image_loader: Callable[[Path], Any] | None = None,
    ) -> None:
        self.model_name = settings.visrag_model_name
        self.instruction = settings.visrag_instruction
        self.vector_size = settings.qdrant_vector_size
        self.backend: VisRAGBackend = self._resolve_backend(
            getattr(settings, "visrag_backend", "stub")
        )
        self.device = getattr(settings, "visrag_device", "auto")
        self.torch_dtype = getattr(
            settings,
            "visrag_torch_dtype",
            getattr(settings, "visrag_dtype", "auto"),
        )
        self.trust_remote_code = bool(getattr(settings, "visrag_trust_remote_code", False))
        self._model: Any | None = None
        self._tokenizer: Any | None = None
        self._torch: Any | None = None
        self._torch_functional: Any | None = None
        self._image_loader = image_loader or self._load_rgb_image

    async def embed_query(self, query: str) -> EmbeddingResult:
        if self.backend == "transformers":
            vector = self._normalize_vector(self._encode_texts([self._with_instruction(query)])[0])
        else:
            vector = self._deterministic_stub_vector(query)

        return EmbeddingResult(
            vector=vector,
            model=self.model_name,
            instruction=self.instruction,
        )

    async def embed_page_image(self, image_path: str) -> EmbeddingResult:
        if self.backend == "transformers":
            vector = self._normalize_vector(self._encode_images([image_path])[0])
        else:
            vector = self._deterministic_stub_vector(image_path)

        return EmbeddingResult(
            vector=vector,
            model=self.model_name,
            instruction=self.instruction,
        )

    def _deterministic_stub_vector(self, text: str) -> list[float]:
        seed = sum(ord(char) for char in text) or 1
        vector = [((seed + offset * 17) % 997) / 997 for offset in range(self.vector_size)]
        return self._normalize_vector(vector)

    def _encode_texts(self, texts: list[str]) -> list[list[float]]:
        self._ensure_transformers_ready()
        inputs = {
            "text": texts,
            "image": [None] * len(texts),
            "tokenizer": self._tokenizer,
        }
        return self._encode(inputs)

    def _encode_images(self, image_paths: list[str]) -> list[list[float]]:
        self._ensure_transformers_ready()
        images = []
        try:
            for image_path in image_paths:
                image = self._image_loader(Path(image_path))
                images.append(self._ensure_rgb_image(image))
        except Exception as exc:
            raise VisRAGUnavailable(f"Unable to load page image for VisRAG: {exc}") from exc

        inputs = {
            "text": [""] * len(images),
            "image": images,
            "tokenizer": self._tokenizer,
        }
        return self._encode(inputs)

    def _encode(self, inputs: dict[str, Any]) -> list[list[float]]:
        self._ensure_transformers_ready()
        try:
            with self._torch.no_grad():
                outputs = self._model(**inputs)
                reps = weighted_mean_pooling(
                    outputs.last_hidden_state,
                    outputs.attention_mask,
                    torch_module=self._torch,
                )
                embeddings = self._torch_functional.normalize(reps, p=2, dim=1)
            return embeddings.detach().cpu().numpy().tolist()
        except VisRAGUnavailable:
            raise
        except Exception as exc:
            raise VisRAGUnavailable(f"VisRAG transformers embedding failed: {exc}") from exc

    def _ensure_transformers_ready(self) -> None:
        if self._model is not None and self._tokenizer is not None:
            return

        try:
            import torch
            import torch.nn.functional as F
            from transformers import AutoModel, AutoTokenizer
        except Exception as exc:  # pragma: no cover - depends on optional deps
            raise VisRAGUnavailable(
                "The VisRAG transformers backend requires torch and transformers. "
                "Install the optional model dependencies or use the 'stub' backend."
            ) from exc

        try:
            dtype = self._resolve_torch_dtype(torch)
            tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=self.trust_remote_code,
            )
            model = AutoModel.from_pretrained(
                self.model_name,
                torch_dtype=dtype,
                trust_remote_code=self.trust_remote_code,
            )
            device = self._resolve_device(torch)
            if hasattr(model, "to"):
                model = model.to(device)
            if hasattr(model, "eval"):
                model.eval()
        except Exception as exc:
            raise VisRAGUnavailable(
                f"Unable to load VisRAG model '{self.model_name}' with transformers: {exc}"
            ) from exc

        self._tokenizer = tokenizer
        self._model = model
        self._torch = torch
        self._torch_functional = F

    def _with_instruction(self, query: str) -> str:
        instruction = self.instruction.strip()
        if not instruction:
            return query

        query_text = query.strip()
        while query_text.startswith(instruction):
            query_text = query_text[len(instruction) :].lstrip()
        return f"{instruction} {query_text}".rstrip()

    def _load_rgb_image(self, image_path: Path) -> Any:
        try:
            from PIL import Image
        except Exception as exc:  # pragma: no cover - depends on optional deps
            raise VisRAGUnavailable(
                "Pillow is required for VisRAG image embeddings. Install the "
                "transformers VisRAG optional dependencies or use the 'stub' backend."
            ) from exc

        with Image.open(image_path) as image:
            return image.convert("RGB")

    @staticmethod
    def _ensure_rgb_image(image: Any) -> Any:
        if getattr(image, "mode", None) == "RGB":
            return image
        if hasattr(image, "convert"):
            return image.convert("RGB")
        return image

    def _normalize_vector(self, vector: Any) -> list[float]:
        if hasattr(vector, "detach"):
            vector = vector.detach()
        if hasattr(vector, "cpu"):
            vector = vector.cpu()
        if hasattr(vector, "numpy"):
            vector = vector.numpy()
        if hasattr(vector, "tolist"):
            vector = vector.tolist()

        if vector and isinstance(vector[0], list):
            if len(vector) != 1:
                raise VisRAGUnavailable("VisRAG backend returned a nested batch vector.")
            vector = vector[0]

        values = [float(value) for value in vector]
        if len(values) != self.vector_size:
            raise VisRAGUnavailable(
                f"VisRAG embedding has size {len(values)}, expected {self.vector_size}."
            )

        norm = sqrt(sum(value * value for value in values))
        if norm == 0:
            return values
        return [value / norm for value in values]

    def _resolve_device(self, torch: Any) -> str:
        if self.device == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        if self.device not in {"cpu", "cuda"}:
            raise VisRAGUnavailable(
                "visrag_device must be one of 'auto', 'cpu', or 'cuda'."
            )
        if self.device == "cuda" and not torch.cuda.is_available():
            raise VisRAGUnavailable("visrag_device is 'cuda' but CUDA is unavailable.")
        return self.device

    def _resolve_torch_dtype(self, torch: Any) -> Any:
        if self.torch_dtype == "auto":
            return torch.bfloat16 if self._resolve_device(torch) == "cuda" else torch.float32
        dtype = getattr(torch, str(self.torch_dtype), None)
        if dtype is None:
            raise VisRAGUnavailable(
                "visrag_torch_dtype must name a torch dtype such as 'float32', "
                "'float16', or 'bfloat16'."
            )
        return dtype

    @staticmethod
    def _resolve_backend(backend: str) -> VisRAGBackend:
        normalized = backend.lower()
        if normalized not in {"stub", "transformers"}:
            raise ValueError("visrag_backend must be either 'stub' or 'transformers'.")
        return normalized  # type: ignore[return-value]


def weighted_mean_pooling(
    hidden: Any,
    attention_mask: Any,
    *,
    torch_module: Any | None = None,
) -> Any:
    if torch_module is None:
        try:
            import torch as torch_module
        except Exception as exc:  # pragma: no cover - depends on optional deps
            raise VisRAGUnavailable(
                "torch is required for VisRAG weighted_mean_pooling."
            ) from exc

    attention_mask_ = attention_mask * attention_mask.cumsum(dim=1)
    s = torch_module.sum(hidden * attention_mask_.unsqueeze(-1).float(), dim=1)
    d = attention_mask_.sum(dim=1, keepdim=True).float()
    return s / d
