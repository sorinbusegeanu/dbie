from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import Any

from dbie.persistence.vector import (
    EmbeddingBatch,
    EmbeddingService,
    normalize_embedding_text,
)


class FastEmbedBGEEmbeddingService(EmbeddingService):
    def __init__(
        self,
        model_id: str = "BAAI/bge-small-en-v1.5",
        model: Any | None = None,
    ) -> None:
        self.model_id = model_id
        self._model = model
        self.normalization_version = "ws-v1"

    def available(self) -> bool:
        try:
            version("fastembed")
            return True
        except PackageNotFoundError:
            return False

    def embed(self, texts: list[str]) -> EmbeddingBatch:
        model = self._model
        if model is None:
            from fastembed import TextEmbedding

            model = TextEmbedding(
                model_name=self.model_id, providers=["CPUExecutionProvider"]
            )
            self._model = model
        normalized = [normalize_embedding_text(text) for text in texts]
        vectors = [vector.tolist() for vector in model.embed(normalized)]
        dimension = len(vectors[0]) if vectors else 0
        if not dimension:
            raise ValueError("embedding service returned no vectors")
        return EmbeddingBatch(
            vectors=vectors,
            model_id=self.model_id,
            dimension=dimension,
            normalization_version=self.normalization_version,
        )
