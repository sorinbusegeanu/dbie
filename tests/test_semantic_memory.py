from pathlib import Path

from dbie.persistence.db import Database
from dbie.persistence.vector import (
    DeterministicEmbeddingService,
    SemanticMemoryRepository,
)


def repository(tmp_path: Path) -> SemanticMemoryRepository:
    database = Database(f"sqlite:///{tmp_path / 'memory.sqlite3'}")
    database.initialize()
    return SemanticMemoryRepository(database, DeterministicEmbeddingService())


def test_semantic_memory_indexes_and_retrieves_without_llm(tmp_path: Path) -> None:
    memory = repository(tmp_path)
    memory.index(
        run_id="old-run",
        entity_type="IDEA",
        entity_id="compliance",
        text="Automated regulatory compliance workflow",
    )
    memory.index(
        run_id="old-run",
        entity_type="IDEA",
        entity_id="music",
        text="Digital music composition marketplace",
    )

    hits = memory.search("regulatory compliance automation", top_k=1)

    assert hits[0].entity_id == "compliance"
    assert hits[0].embedding_model == "dbie-test-hash-v1"


def test_semantic_memory_can_hide_current_run(tmp_path: Path) -> None:
    memory = repository(tmp_path)
    memory.index(
        run_id="current",
        entity_type="EVIDENCE",
        entity_id="current-item",
        text="buyer pain",
    )
    memory.index(
        run_id="prior",
        entity_type="EVIDENCE",
        entity_id="prior-item",
        text="buyer pain",
    )

    hits = memory.search("buyer pain", exclude_run_id="current")

    assert [hit.entity_id for hit in hits] == ["prior-item"]


def test_indexing_same_entity_and_model_is_idempotent(tmp_path: Path) -> None:
    memory = repository(tmp_path)
    first = memory.index(
        run_id="run",
        entity_type="IDEA",
        entity_id="one",
        text="same text",
    )
    second = memory.index(
        run_id="run",
        entity_type="IDEA",
        entity_id="one",
        text="same text",
    )

    assert second.id == first.id
