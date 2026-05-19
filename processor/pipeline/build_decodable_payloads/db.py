from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


MAIN_HK_TABLE = "main_hk_payloads"
ADCS_HK_TABLE = "adcs_hk_payloads"
ADCS_SAMPLING_TYPES = {
    "011": "high",
    "100": "normal",
}


def _to_iso_utc(value) -> str:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize(timezone.utc)
    else:
        ts = ts.tz_convert(timezone.utc)
    return ts.isoformat()


def _timestamp_obc_unix(value) -> int:
    return _timestamp_unix(value)


def _timestamp_adcs_unix(value) -> int:
    return _timestamp_unix(value)


def _timestamp_unix(value) -> int:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize(timezone.utc)
    else:
        ts = ts.tz_convert(timezone.utc)
    return int(ts.timestamp())


def _unit_id(packet_id: str, timestamp_unix: int, data_hex: str) -> str:
    material = f"{packet_id}|{timestamp_unix}|{data_hex}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _reception_id(gse: str, packet_id: str, timestamp_unix: int, data_hex: str) -> str:
    material = f"{gse}|{packet_id}|{timestamp_unix}|{data_hex}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def store_main_hk_payloads(db_path: Path, packet_id: str, df: pd.DataFrame, gse: str = "unknown") -> int:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    rows = []

    for row in df.to_dict("records"):
        data_hex = row["Data"]
        timestamp_obc_unix = _timestamp_obc_unix(row["timestamp_obc"])
        rows.append(
            (
                _reception_id(gse, packet_id, timestamp_obc_unix, data_hex),
                _unit_id(packet_id, timestamp_obc_unix, data_hex),
                gse,
                packet_id,
                _to_iso_utc(row["Received time"]),
                _to_iso_utc(row["timestamp_obc"]),
                timestamp_obc_unix,
                data_hex,
            )
        )

    with sqlite3.connect(db_path) as conn:
        _ensure_main_hk_schema(conn)
        before_changes = conn.total_changes
        conn.executemany(
            f"""
            INSERT OR IGNORE INTO {MAIN_HK_TABLE}
            (reception_id, unit_id, gse, packet_id, received_time, timestamp_obc, timestamp_obc_unix, data_hex)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        return conn.total_changes - before_changes


def store_adcs_hk_payloads(db_path: Path, packet_id: str, df: pd.DataFrame, gse: str = "unknown") -> int:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    file_id = packet_id[:3]
    sampling_type = ADCS_SAMPLING_TYPES[file_id]
    rows = []

    for row in df.to_dict("records"):
        data_hex = row["Data"]
        timestamp_adcs_unix = _timestamp_adcs_unix(row["timestamp_adcs"])
        rows.append(
            (
                _reception_id(gse, packet_id, timestamp_adcs_unix, data_hex),
                _unit_id(packet_id, timestamp_adcs_unix, data_hex),
                gse,
                packet_id,
                sampling_type,
                _to_iso_utc(row["Received time"]),
                _to_iso_utc(row["timestamp_adcs"]),
                timestamp_adcs_unix,
                data_hex,
            )
        )

    with sqlite3.connect(db_path) as conn:
        _ensure_adcs_hk_schema(conn)
        before_changes = conn.total_changes
        conn.executemany(
            f"""
            INSERT OR IGNORE INTO {ADCS_HK_TABLE}
            (reception_id, unit_id, gse, packet_id, sampling_type, received_time, timestamp_adcs, timestamp_adcs_unix, data_hex)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        return conn.total_changes - before_changes


def _ensure_main_hk_schema(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, MAIN_HK_TABLE):
        _create_main_hk_table(conn)
        return
    if not _has_reception_primary_key(conn, MAIN_HK_TABLE):
        _migrate_main_hk_table(conn)


def _ensure_adcs_hk_schema(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, ADCS_HK_TABLE):
        _create_adcs_hk_table(conn)
        return
    if not _has_reception_primary_key(conn, ADCS_HK_TABLE):
        _migrate_adcs_hk_table(conn)


def _create_main_hk_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {MAIN_HK_TABLE} (
            reception_id TEXT PRIMARY KEY,
            unit_id TEXT NOT NULL,
            gse TEXT NOT NULL DEFAULT 'unknown',
            packet_id TEXT NOT NULL,
            received_time TEXT NOT NULL,
            timestamp_obc TEXT NOT NULL,
            timestamp_obc_unix INTEGER NOT NULL,
            data_hex TEXT NOT NULL
        )
        """
    )


def _create_adcs_hk_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {ADCS_HK_TABLE} (
            reception_id TEXT PRIMARY KEY,
            unit_id TEXT NOT NULL,
            gse TEXT NOT NULL DEFAULT 'unknown',
            packet_id TEXT NOT NULL,
            sampling_type TEXT NOT NULL,
            received_time TEXT NOT NULL,
            timestamp_adcs TEXT NOT NULL,
            timestamp_adcs_unix INTEGER NOT NULL,
            data_hex TEXT NOT NULL
        )
        """
    )


def _migrate_main_hk_table(conn: sqlite3.Connection) -> None:
    legacy_table = f"{MAIN_HK_TABLE}_legacy"
    conn.execute(f"ALTER TABLE {MAIN_HK_TABLE} RENAME TO {legacy_table}")
    _create_main_hk_table(conn)
    legacy_rows = _table_dicts(conn, legacy_table)
    for row in legacy_rows:
        gse = row.get("gse") or "unknown"
        timestamp_unix = row["timestamp_obc_unix"]
        data_hex = row["data_hex"]
        packet_id = row["packet_id"]
        conn.execute(
            f"""
            INSERT OR IGNORE INTO {MAIN_HK_TABLE}
            (reception_id, unit_id, gse, packet_id, received_time, timestamp_obc, timestamp_obc_unix, data_hex)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _reception_id(gse, packet_id, timestamp_unix, data_hex),
                _unit_id(packet_id, timestamp_unix, data_hex),
                gse,
                packet_id,
                row["received_time"],
                row["timestamp_obc"],
                timestamp_unix,
                data_hex,
            ),
        )
    conn.execute(f"DROP TABLE {legacy_table}")


def _migrate_adcs_hk_table(conn: sqlite3.Connection) -> None:
    legacy_table = f"{ADCS_HK_TABLE}_legacy"
    conn.execute(f"ALTER TABLE {ADCS_HK_TABLE} RENAME TO {legacy_table}")
    _create_adcs_hk_table(conn)
    legacy_rows = _table_dicts(conn, legacy_table)
    for row in legacy_rows:
        gse = row.get("gse") or "unknown"
        timestamp_unix = row["timestamp_adcs_unix"]
        data_hex = row["data_hex"]
        packet_id = row["packet_id"]
        conn.execute(
            f"""
            INSERT OR IGNORE INTO {ADCS_HK_TABLE}
            (reception_id, unit_id, gse, packet_id, sampling_type, received_time, timestamp_adcs, timestamp_adcs_unix, data_hex)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _reception_id(gse, packet_id, timestamp_unix, data_hex),
                _unit_id(packet_id, timestamp_unix, data_hex),
                gse,
                packet_id,
                row["sampling_type"],
                row["received_time"],
                row["timestamp_adcs"],
                timestamp_unix,
                data_hex,
            ),
        )
    conn.execute(f"DROP TABLE {legacy_table}")


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone() is not None


def _has_reception_primary_key(conn: sqlite3.Connection, table_name: str) -> bool:
    return any(row[1] == "reception_id" and row[5] == 1 for row in conn.execute(f"PRAGMA table_info({table_name})"))


def _table_dicts(conn: sqlite3.Connection, table_name: str) -> list[dict]:
    cursor = conn.execute(f"SELECT * FROM {table_name}")
    columns = [description[0] for description in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
