"""PostgreSQL pgvector store used by the oss_local production profile."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import (
    Column,
    DateTime,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    insert,
    select,
)
from sqlalchemy.engine import Engine
from sqlalchemy.sql import text

from dbie.persistence.vector import (
    EmbeddingService,
    SemanticMemoryRecord,
    SemanticSearchHit,
    normalize_embedding_text,
)


class PgVectorStore:
    def __init__(
        self,
        engine: Engine,
        embeddings: EmbeddingService,
        *,
        dimension: int,
    ) -> None:
        if engine.dialect.name != "postgresql":
            raise ValueError("PgVectorStore requires PostgreSQL")
        self.engine = engine
        self.embeddings = embeddings
        self.dimension = dimension
        metadata = MetaData()
        self.table = Table(
            "semantic_memories_vector",
            metadata,
            Column("id", String(36), primary_key=True),
            Column("run_id", String(36), nullable=False, index=True),
            Column("entity_type", String(64), nullable=False, index=True),
            Column("entity_id", String(36), nullable=False, index=True),
            Column("canonical_text", Text, nullable=False),
            Column("embedding", VECTOR(dimension), nullable=False),
            Column("embedding_model", String(256), nullable=False),
            Column("embedding_dimension", Integer, nullable=False),
            Column("normalization_version", String(32), nullable=False),
            Column("created_at", DateTime(timezone=True), nullable=False),
        )
        self.hnsw_index = Index(
            "ix_semantic_memories_vector_hnsw",
            self.table.c.embedding,
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        )
        self.metadata = metadata

    def initialize(self) -> None:
        with self.engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        self.metadata.create_all(self.engine)

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
        if batch.dimension != self.dimension:
            raise ValueError(
                f"embedding dimension {batch.dimension} != store dimension {self.dimension}"
            )
        record = SemanticMemoryRecord(
            id=str(uuid4()),
            run_id=run_id,
            entity_type=entity_type,
            entity_id=entity_id,
            canonical_text=normalized,
            embedding=batch.vectors[0],
            embedding_model=batch.model_id,
            embedding_dimension=batch.dimension,
            normalization_version=batch.normalization_version,
            created_at=datetime.now(UTC),
        )
        with self.engine.begin() as connection:
            connection.execute(insert(self.table).values(**record.model_dump()))
        return record

    def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        entity_types: set[str] | None = None,
        exclude_run_id: str | None = None,
        min_similarity: float = 0.05,
    ) -> list[SemanticSearchHit]:
        if not normalize_embedding_text(query):
            return []
        if not -1 <= min_similarity <= 1:
            raise ValueError("min_similarity must be between -1 and 1")
        if top_k < 1:
            return []
        batch = self.embeddings.embed([normalize_embedding_text(query)])
        distance = self.table.c.embedding.cosine_distance(batch.vectors[0])
        statement = select(self.table, distance.label("distance"))
        if entity_types:
            statement = statement.where(self.table.c.entity_type.in_(entity_types))
        if exclude_run_id:
            statement = statement.where(self.table.c.run_id != exclude_run_id)
        statement = statement.order_by(distance).limit(top_k)
        with self.engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        return [
            SemanticSearchHit(
                entity_type=row["entity_type"],
                entity_id=row["entity_id"],
                canonical_text=row["canonical_text"],
                similarity=1.0 - float(row["distance"]),
                run_id=row["run_id"],
                embedding_model=row["embedding_model"],
                source_record_id=row["id"],
                source_ids=[f"{row['entity_type']}:{row['entity_id']}@{row['run_id']}"],
            )
            for row in rows
            if 1.0 - float(row["distance"]) >= min_similarity
        ]
        unique: dict[tuple[str, str], SemanticSearchHit] = {}
        for hit in hits:
            key = (hit.entity_type, normalize_embedding_text(hit.canonical_text).casefold())
            if key not in unique:
                unique[key] = hit
            else:
                unique[key].source_ids.extend(hit.source_ids)
        return list(unique.values())
