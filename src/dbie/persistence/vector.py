"""Embedding-independent semantic memory with a SQLite-safe exact fallback."""

from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import insert, select

from dbie.persistence.db import Database
from dbie.persistence.schema import semantic_memories


class EmbeddingBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vectors: list[list[float]]
    model_id: str
    dimension: int = Field(gt=0)
    normalization_version: str


class EmbeddingService(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> EmbeddingBatch:
        raise NotImplementedError


def normalize_embedding_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


class DeterministicEmbeddingService(EmbeddingService):
    """Dependency-free fixture backend; never presented as production semantics."""

    model_id = "dbie-test-hash-v1"
    dimension = 32
    normalization_version = "ws-v1"

    def embed(self, texts: list[str]) -> EmbeddingBatch:
        vectors: list[list[float]] = []
        for text in texts:
            normalized = normalize_embedding_text(text).lower()
            values = [0.0] * self.dimension
            for token in re.findall(r"[a-z0-9]+", normalized):
                digest = sha256(token.encode()).digest()
                index = int.from_bytes(digest[:2], "big") % self.dimension
                values[index] += -1.0 if digest[2] & 1 else 1.0
            length = math.sqrt(sum(value * value for value in values)) or 1.0
            vectors.append([value / length for value in values])
        return EmbeddingBatch(
            vectors=vectors,
            model_id=self.model_id,
            dimension=self.dimension,
            normalization_version=self.normalization_version,
        )


class SemanticMemoryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    entity_type: str
    entity_id: str
    canonical_text: str
    embedding: list[float]
    embedding_model: str
    embedding_dimension: int
    normalization_version: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SemanticSearchHit(BaseModel):
    entity_type: str
    entity_id: str
    canonical_text: str
    similarity: float
    run_id: str
    embedding_model: str


class SemanticMemoryRepository:
    def __init__(self, database: Database, embeddings: EmbeddingService) -> None:
        self.database = database
        self.embeddings = embeddings

    def index(
        self,
        *,
        run_id: str,
        entity_type: str,
        entity_id: str,
        text: str,
    ) -> SemanticMemoryRecord:
        normalized = normalize_embedding_text(text)
        batch = self.embeddings.embed([normalized])
        record = SemanticMemoryRecord(
            run_id=run_id,
            entity_type=entity_type,
            entity_id=entity_id,
            canonical_text=normalized,
            embedding=batch.vectors[0],
            embedding_model=batch.model_id,
            embedding_dimension=batch.dimension,
            normalization_version=batch.normalization_version,
        )
        with self.database.engine.begin() as connection:
            existing = connection.execute(
                select(semantic_memories.c.id).where(
                    semantic_memories.c.entity_type == entity_type,
                    semantic_memories.c.entity_id == entity_id,
                    semantic_memories.c.embedding_model == batch.model_id,
                    semantic_memories.c.normalization_version
                    == batch.normalization_version,
                )
            ).scalar_one_or_none()
            if existing is not None:
                return self.get(existing)
            connection.execute(insert(semantic_memories).values(**record.model_dump()))
        return record

    def get(self, record_id: str) -> SemanticMemoryRecord:
        with self.database.engine.connect() as connection:
            row = (
                connection.execute(
                    select(semantic_memories).where(semantic_memories.c.id == record_id)
                )
                .mappings()
                .one()
            )
        return SemanticMemoryRecord.model_validate(dict(row))

    def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        entity_types: set[str] | None = None,
        exclude_run_id: str | None = None,
    ) -> list[SemanticSearchHit]:
        query_batch = self.embeddings.embed([normalize_embedding_text(query)])
        query_vector = query_batch.vectors[0]
        statement = select(semantic_memories).where(
            semantic_memories.c.embedding_model == query_batch.model_id,
            semantic_memories.c.normalization_version
            == query_batch.normalization_version,
        )
        if entity_types:
            statement = statement.where(
                semantic_memories.c.entity_type.in_(entity_types)
            )
        if exclude_run_id:
            statement = statement.where(semantic_memories.c.run_id != exclude_run_id)
        with self.database.engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        hits = [
            SemanticSearchHit(
                entity_type=row["entity_type"],
                entity_id=row["entity_id"],
                canonical_text=row["canonical_text"],
                similarity=_cosine(query_vector, row["embedding"]),
                run_id=row["run_id"],
                embedding_model=row["embedding_model"],
            )
            for row in rows
        ]
        return sorted(hits, key=lambda hit: hit.similarity, reverse=True)[:top_k]


def _cosine(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_length = math.sqrt(sum(value * value for value in left))
    right_length = math.sqrt(sum(value * value for value in right))
    if not left_length or not right_length:
        return 0.0
    return numerator / (left_length * right_length)
