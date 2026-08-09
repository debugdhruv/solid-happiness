from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

load_dotenv()

DEFAULT_DATABASE_URL = "postgresql+psycopg2://support:change-me@localhost:5432/support_analytics"


def database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine(database_url(), pool_pre_ping=True, future=True)


def execute_sql_file(path: str | Path) -> None:
    sql = Path(path).read_text(encoding="utf-8")
    statements = [statement.strip() for statement in sql.split(";") if statement.strip()]
    with get_engine().begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def healthcheck() -> dict[str, str]:
    with get_engine().connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}

