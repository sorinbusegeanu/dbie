from sqlalchemy import create_mock_engine

from dbie.persistence.pgvector_store import PgVectorStore
from dbie.persistence.vector import DeterministicEmbeddingService


def test_pgvector_store_keeps_index_operation_callable() -> None:
    engine = create_mock_engine("postgresql+psycopg://", lambda *args, **kwargs: None)
    store = PgVectorStore(engine, DeterministicEmbeddingService(), dimension=32)

    assert callable(store.index)
    assert store.hnsw_index.dialect_options["postgresql"]["using"] == "hnsw"
