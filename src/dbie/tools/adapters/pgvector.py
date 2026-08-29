from __future__ import annotations

from typing import Protocol

from dbie.persistence.vector import SemanticSearchHit
from dbie.tools.adapters.base import (
    AdapterCapabilities,
    AdapterHealth,
    AdapterRequest,
    AdapterResult,
    ToolAdapter,
)


class MemoryStore(Protocol):
    def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        entity_types: set[str] | None = None,
        exclude_run_id: str | None = None,
    ) -> list[SemanticSearchHit]: ...


class PgVectorMemoryAdapter(ToolAdapter):
    name = "pgvector"
    capabilities = AdapterCapabilities(operations={"semantic_memory_search"})

    def __init__(self, repository: MemoryStore) -> None:
        self.repository = repository

    def health(self) -> AdapterHealth:
        try:
            database = getattr(self.repository, "database", None)
            if database is not None:
                available = bool(database.ping())
            else:
                engine = self.repository.engine
                with engine.connect() as connection:
                    connection.exec_driver_sql("SELECT 1")
                available = True
            return AdapterHealth(name=self.name, available=available)
        except Exception as exc:  # noqa: BLE001 - health checks fail closed
            return AdapterHealth(name=self.name, available=False, detail=str(exc))

    def execute(self, request: AdapterRequest) -> AdapterResult:
        arguments = request.arguments
        hits = self.repository.search(
            str(arguments["query"]),
            top_k=int(arguments.get("top_k", 10)),
            entity_types=set(arguments.get("entity_types") or []) or None,
            exclude_run_id=arguments.get("exclude_run_id"),
        )
        return AdapterResult(
            payload={
                "hits": [hit.model_dump() for hit in hits],
                "memory_is_evidence": False,
            }
        )
