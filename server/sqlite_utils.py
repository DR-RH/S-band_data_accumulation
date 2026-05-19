from __future__ import annotations

import sqlite3

from fastapi import HTTPException

from settings import db_path


def connect() -> sqlite3.Connection:
    path = db_path()
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Database not found: {path}. Upload payloads first or set S_BAND_DECODER_DB.",
        )

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def require_table(conn: sqlite3.Connection, table_name: str) -> None:
    if not table_exists(conn, table_name):
        raise HTTPException(status_code=404, detail=f"Table not found: {table_name}")
