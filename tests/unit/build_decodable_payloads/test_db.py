import sqlite3
from datetime import datetime, timezone

import pandas as pd

from pipeline.build_decodable_payloads.db import ADCS_HK_TABLE, MAIN_HK_TABLE, store_adcs_hk_payloads, store_main_hk_payloads


def test_store_main_hk_payloads_writes_recommended_timestamp_columns(tmp_path):
    db_path = tmp_path / "main_hk.sqlite"
    df = pd.DataFrame(
        [
            {
                "Received time": pd.Timestamp("2026-03-12T15:46:03.527611Z"),
                "timestamp_obc": datetime(2021, 1, 1, 0, 0, 16, tzinfo=timezone.utc),
                "Data": "0c150101",
            }
        ]
    )

    inserted = store_main_hk_payloads(db_path, "1101011001000101", df)

    assert inserted == 1
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            f"""
            SELECT packet_id, received_time, timestamp_obc, timestamp_obc_unix, data_hex
            FROM {MAIN_HK_TABLE}
            """
        ).fetchone()

    assert row == (
        "1101011001000101",
        "2026-03-12T15:46:03.527611+00:00",
        "2021-01-01T00:00:16+00:00",
        1609459216,
        "0c150101",
    )


def test_store_main_hk_payloads_ignores_duplicate_units(tmp_path):
    db_path = tmp_path / "main_hk.sqlite"
    df = pd.DataFrame(
        [
            {
                "Received time": "2026-03-12T15:46:03.527611+00:00",
                "timestamp_obc": "2021-01-01T00:00:16+00:00",
                "Data": "0c150101",
            }
        ]
    )

    assert store_main_hk_payloads(db_path, "1101011001000101", df) == 1
    assert store_main_hk_payloads(db_path, "1101011001000101", df) == 0

    with sqlite3.connect(db_path) as conn:
        count = conn.execute(f"SELECT COUNT(*) FROM {MAIN_HK_TABLE}").fetchone()[0]

    assert count == 1


def test_store_adcs_hk_payloads_writes_high_and_normal_sampling_rows(tmp_path):
    db_path = tmp_path / "adcs.sqlite"
    df = pd.DataFrame(
        [
            {
                "Received time": "2026-03-12T15:40:27.259500+00:00",
                "timestamp_adcs": "2026-03-12T15:40:27+00:00",
                "Data": "aabbcc",
            }
        ]
    )

    assert store_adcs_hk_payloads(db_path, "0111011001000101", df) == 1
    assert store_adcs_hk_payloads(db_path, "1001011001000101", df) == 1

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT packet_id, sampling_type, received_time, timestamp_adcs, timestamp_adcs_unix, data_hex
            FROM {ADCS_HK_TABLE}
            ORDER BY sampling_type
            """
        ).fetchall()

    assert rows == [
        (
            "0111011001000101",
            "high",
            "2026-03-12T15:40:27.259500+00:00",
            "2026-03-12T15:40:27+00:00",
            1773330027,
            "aabbcc",
        ),
        (
            "1001011001000101",
            "normal",
            "2026-03-12T15:40:27.259500+00:00",
            "2026-03-12T15:40:27+00:00",
            1773330027,
            "aabbcc",
        ),
    ]


def test_store_adcs_hk_payloads_ignores_duplicate_units(tmp_path):
    db_path = tmp_path / "adcs.sqlite"
    df = pd.DataFrame(
        [
            {
                "Received time": "2026-03-12T15:40:27.259500+00:00",
                "timestamp_adcs": "2026-03-12T15:40:27+00:00",
                "Data": "aabbcc",
            }
        ]
    )

    assert store_adcs_hk_payloads(db_path, "0111011001000101", df) == 1
    assert store_adcs_hk_payloads(db_path, "0111011001000101", df) == 0
