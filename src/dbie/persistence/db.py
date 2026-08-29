"""SQLAlchemy database foundation supporting SQLite and PostgreSQL URLs."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine, text


class Database:
    def __init__(self, url: str) -> None:
        self.url = url
        if url.startswith("sqlite:///"):
            path = Path(url.removeprefix("sqlite:///"))
            if str(path) != ":memory:":
                path.parent.mkdir(parents=True, exist_ok=True)
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        self.engine: Engine = create_engine(url, connect_args=connect_args)

    def initialize(self) -> None:
        from dbie.persistence.schema import metadata

        metadata.create_all(self.engine)

    def ping(self) -> bool:
        with self.engine.connect() as connection:
            return connection.execute(text("SELECT 1")).scalar_one() == 1

    def dispose(self) -> None:
        self.engine.dispose()
