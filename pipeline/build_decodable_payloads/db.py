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


def _unit_id(packet_id: str, timestamp_obc_unix: int, data_hex: str) -> str:
    material = f"{packet_id}|{timestamp_obc_unix}|{data_hex}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _adcs_unit_id(packet_id: str, timestamp_adcs_unix: int, data_hex: str) -> str:
    material = f"{packet_id}|{timestamp_adcs_unix}|{data_hex}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def store_main_hk_payloads(db_path: Path, packet_id: str, df: pd.DataFrame) -> int:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    rows = []

    for row in df.to_dict("records"):
        data_hex = row["Data"]
        timestamp_obc_unix = _timestamp_obc_unix(row["timestamp_obc"])
        rows.append(
            (
                _unit_id(packet_id, timestamp_obc_unix, data_hex),
                packet_id,
                _to_iso_utc(row["Received time"]),
                _to_iso_utc(row["timestamp_obc"]),
                timestamp_obc_unix,
                data_hex,
            )
        )

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {MAIN_HK_TABLE} (
                unit_id TEXT PRIMARY KEY,
                packet_id TEXT NOT NULL,
                received_time TEXT NOT NULL,
                timestamp_obc TEXT NOT NULL,
                timestamp_obc_unix INTEGER NOT NULL,
                data_hex TEXT NOT NULL
            )
            """
        )
        conn.executemany(
            f"""
            INSERT OR IGNORE INTO {MAIN_HK_TABLE}
            (unit_id, packet_id, received_time, timestamp_obc, timestamp_obc_unix, data_hex)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        return conn.total_changes


def store_adcs_hk_payloads(db_path: Path, packet_id: str, df: pd.DataFrame) -> int:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    file_id = packet_id[:3]
    sampling_type = ADCS_SAMPLING_TYPES[file_id]
    rows = []

    for row in df.to_dict("records"):
        data_hex = row["Data"]
        timestamp_adcs_unix = _timestamp_adcs_unix(row["timestamp_adcs"])
        rows.append(
            (
                _adcs_unit_id(packet_id, timestamp_adcs_unix, data_hex),
                packet_id,
                sampling_type,
                _to_iso_utc(row["Received time"]),
                _to_iso_utc(row["timestamp_adcs"]),
                timestamp_adcs_unix,
                data_hex,
            )
        )

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {ADCS_HK_TABLE} (
                unit_id TEXT PRIMARY KEY,
                packet_id TEXT NOT NULL,
                sampling_type TEXT NOT NULL,
                received_time TEXT NOT NULL,
                timestamp_adcs TEXT NOT NULL,
                timestamp_adcs_unix INTEGER NOT NULL,
                data_hex TEXT NOT NULL
            )
            """
        )
        conn.executemany(
            f"""
            INSERT OR IGNORE INTO {ADCS_HK_TABLE}
            (unit_id, packet_id, sampling_type, received_time, timestamp_adcs, timestamp_adcs_unix, data_hex)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        return conn.total_changes
