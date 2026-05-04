from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from pipeline.build_decodable_payloads.db import store_adcs_hk_payloads, store_main_hk_payloads
import pandas as pd


DEFAULT_DB_PATH = Path("data/main_hk.sqlite")
DB_PATH_ENV = "S_BAND_DECODER_DB"
MAIN_HK_TABLE = "main_hk_payloads"
ADCS_HK_TABLE = "adcs_hk_payloads"

app = FastAPI(title="S-band Decoder DB")


class PayloadUpload(BaseModel):
    packet_id: str
    rows: list[dict] = Field(default_factory=list)


def db_path() -> Path:
    return Path(os.environ.get(DB_PATH_ENV, DEFAULT_DB_PATH))


def connect() -> sqlite3.Connection:
    path = db_path()
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Database not found: {path}. Run the pipeline first or set {DB_PATH_ENV}.",
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


@app.get("/health")
def health():
    path = db_path()
    return {"status": "ok", "db_path": str(path), "db_exists": path.exists()}


@app.get("/tables")
def tables():
    with connect() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        ).fetchall()

    return {"tables": [row["name"] for row in rows]}


@app.get("/main-hk")
def main_hk(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    with connect() as conn:
        require_table(conn, MAIN_HK_TABLE)
        rows = conn.execute(
            f"""
            SELECT unit_id, packet_id, received_time, timestamp_obc, timestamp_obc_unix, data_hex
            FROM {MAIN_HK_TABLE}
            ORDER BY timestamp_obc_unix DESC, received_time DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()

    return {"rows": [dict(row) for row in rows], "limit": limit, "offset": offset}


@app.get("/adcs-hk")
def adcs_hk(
    sampling_type: str | None = Query(None, pattern="^(normal|high)$"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    where_clause = ""
    params: list[object] = []
    if sampling_type is not None:
        where_clause = "WHERE sampling_type = ?"
        params.append(sampling_type)

    params.extend([limit, offset])

    with connect() as conn:
        require_table(conn, ADCS_HK_TABLE)
        rows = conn.execute(
            f"""
            SELECT unit_id, packet_id, sampling_type, received_time, timestamp_adcs, timestamp_adcs_unix, data_hex
            FROM {ADCS_HK_TABLE}
            {where_clause}
            ORDER BY timestamp_adcs_unix DESC, received_time DESC
            LIMIT ? OFFSET ?
            """,
            params,
        ).fetchall()

    return {
        "rows": [dict(row) for row in rows],
        "sampling_type": sampling_type,
        "limit": limit,
        "offset": offset,
    }


@app.post("/payloads/main-hk")
def upload_main_hk(payload: PayloadUpload):
    inserted = store_main_hk_payloads(db_path(), payload.packet_id, pd.DataFrame(payload.rows))
    return {"inserted": inserted}


@app.post("/payloads/adcs-hk")
def upload_adcs_hk(payload: PayloadUpload):
    inserted = store_adcs_hk_payloads(db_path(), payload.packet_id, pd.DataFrame(payload.rows))
    return {"inserted": inserted}
