from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from dbie.persistence.db import Database
from dbie.tools.adapters.base import (
    AdapterCapabilities,
    AdapterHealth,
    AdapterRequest,
    AdapterResult,
    ToolAdapter,
)

QueryHandler = Callable[[dict[str, Any]], Any]


class SQLAlchemyDatabaseAdapter(ToolAdapter):
    name = "sqlalchemy_db"
    capabilities = AdapterCapabilities(operations={"database_query"})

    def __init__(
        self, database: Database, operations: dict[str, QueryHandler] | None = None
    ) -> None:
        self.database = database
        self.operations = operations or {}

    def health(self) -> AdapterHealth:
        try:
            return AdapterHealth(name=self.name, available=self.database.ping())
        except Exception as exc:  # noqa: BLE001 - health checks fail closed
            return AdapterHealth(name=self.name, available=False, detail=str(exc))

    def execute(self, request: AdapterRequest) -> AdapterResult:
        started = datetime.now(UTC)
        operation = str(request.arguments.get("operation", ""))
        if (
            operation in {"RAW_SQL", "SCHEMA_CHANGE", "DELETE"}
            or "sql" in request.arguments
        ):
            raise ValueError("raw or destructive SQL is not exposed")
        try:
            handler = self.operations[operation]
        except KeyError as exc:
            raise ValueError(
                f"database operation is not allowlisted: {operation}"
            ) from exc
        value = handler(dict(request.arguments.get("parameters", {})))
        ended = datetime.now(UTC)
        return AdapterResult(
            payload={"operation": operation, "result": value},
            started_at=started,
            ended_at=ended,
        )
