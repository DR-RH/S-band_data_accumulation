from pathlib import Path
import sqlite3

import pandas as pd
import pytest

from pipeline.build_decodable_payloads.db import ADCS_HK_TABLE, MAIN_HK_TABLE
from dev._common import infer_gse
from pipeline.build_decodable_payloads.process import process_decodable_df
from pipeline.decode_payloads.decode import run as decode_payloads
from pipeline.ingest_raw_log.binarize import build_timestamped_binary_from_log
from pipeline.ingest_raw_log.io import write_step1_output
from pipeline.parse_packets.main import parse_into_df
from pipeline.verify_crc.main import verify_crc


SAMPLE_LOG = Path("debug_tlm/all_tlm_in_RX_COM_COM7_20260312_153552.txt")


def test_debug_sample_runs_through_full_pipeline(tmp_path):
    if not SAMPLE_LOG.exists():
        pytest.skip(f"{SAMPLE_LOG} is not available")

    out_dir = tmp_path / "intermediate" / SAMPLE_LOG.stem
    decoded_dir = tmp_path / "decoded" / SAMPLE_LOG.stem
    db_path = tmp_path / "main_hk.sqlite"
    gse = infer_gse(SAMPLE_LOG.name)

    timestamped_binary = build_timestamped_binary_from_log(SAMPLE_LOG)
    write_step1_output(timestamped_binary, out_dir)
    valid_binary = verify_crc(timestamped_binary, gse, out_dir)
    packets_df = parse_into_df(valid_binary, gse, out_dir)
    process_decodable_df(packets_df, out_dir, db_path)
    decoded_paths = decode_payloads(out_dir, decoded_dir)

    assert gse == "Kyutech"
    assert (out_dir / "step1_timestamp_injected.bin").is_file()
    assert (out_dir / "step2_valid_packets.bin").is_file()
    assert (out_dir / "step3_decode_ready.csv").is_file()
    assert (out_dir / "step3_decode_ready.pickle").is_file()

    step4_names = {path.name for path in out_dir.glob("step4_concat_data_ID_*.csv")}
    assert step4_names == {
        "step4_concat_data_ID_001_main_exe_log_2026-03-12_1540.csv",
        "step4_concat_data_ID_011_adcs_high_2026-03-12_1530.csv",
        "step4_concat_data_ID_100_adcs_normal_2026-03-12_1540.csv",
        "step4_concat_data_ID_110_main_HK_log_2026-03-12_1540.csv",
        "step4_concat_data_ID_111_adcs_exe_log_2026-03-12_1540.csv",
    }

    decoded_names = {path.name for path in decoded_paths}
    assert decoded_names == {
        "decoded_step4_concat_data_ID_001_main_exe_log_2026-03-12_1540.csv",
        "decoded_step4_concat_data_ID_011_adcs_high_2026-03-12_1530.csv",
        "decoded_step4_concat_data_ID_110_main_HK_log_2026-03-12_1540.csv",
        "decoded_step4_concat_data_ID_111_adcs_exe_log_2026-03-12_1540.csv",
    }

    assert len(valid_binary) > 0
    assert not packets_df.empty
    for decoded_path in decoded_paths:
        assert decoded_path.is_file()
        assert not pd.read_csv(decoded_path).empty

    with sqlite3.connect(db_path) as conn:
        count = conn.execute(f"SELECT COUNT(*) FROM {MAIN_HK_TABLE}").fetchone()[0]
        row = conn.execute(
            f"""
            SELECT packet_id, received_time, timestamp_obc, timestamp_obc_unix, data_hex
            FROM {MAIN_HK_TABLE}
            LIMIT 1
            """
        ).fetchone()
        adcs_sampling_types = {
            row[0]
            for row in conn.execute(
                f"""
            SELECT DISTINCT sampling_type
            FROM {ADCS_HK_TABLE}
            """
            ).fetchall()
        }
        adcs_table_name = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = ?
            """,
            (ADCS_HK_TABLE,),
        ).fetchone()

    assert count > 0
    assert row[0].startswith("110")
    assert row[1].endswith("+00:00")
    assert row[2].endswith("+00:00")
    assert isinstance(row[3], int)
    assert len(row[4]) == 382
    assert adcs_table_name == (ADCS_HK_TABLE,)
    assert "high" in adcs_sampling_types
