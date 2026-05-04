from types import SimpleNamespace
from datetime import datetime, timezone

import pandas as pd

from pipeline.build_decodable_payloads.builder import build_decodable_df, extract_timestamp_adcs, extract_timestamp_obc


def test_build_decodable_df_builds_chunks_across_contiguous_packets():
    df = pd.DataFrame(
        [
            {"Packet no.": 1, "Data": b"AB", "Datetime": "t1"},
            {"Packet no.": 2, "Data": b"CD", "Datetime": "t2"},
        ]
    )
    config = SimpleNamespace(file_id="001", decode_unit=4, sync_code=b"", sync_code_offset=0)

    result = build_decodable_df(df, missing=[], config=config)

    assert result.to_dict("records") == [{"Received time": "t2", "Data": "41424344"}]


def test_build_decodable_df_resets_buffer_when_packet_number_jumps():
    df = pd.DataFrame(
        [
            {"Packet no.": 1, "Data": b"AB", "Datetime": "t1"},
            {"Packet no.": 3, "Data": b"CD", "Datetime": "t3"},
            {"Packet no.": 4, "Data": b"EF", "Datetime": "t4"},
        ]
    )
    config = SimpleNamespace(file_id="001", decode_unit=4, sync_code=b"", sync_code_offset=0)

    result = build_decodable_df(df, missing=[2], config=config)

    assert result.to_dict("records") == [{"Received time": "t4", "Data": "43444546"}]


def test_build_decodable_df_handles_repeated_packet_number_sequences_in_stream_order():
    df = pd.DataFrame(
        [
            {"Packet no.": 0, "Data": b"AB", "Datetime": "t0"},
            {"Packet no.": 1, "Data": b"CD", "Datetime": "t1"},
            {"Packet no.": 0, "Data": b"EF", "Datetime": "t2"},
            {"Packet no.": 1, "Data": b"GH", "Datetime": "t3"},
        ]
    )
    config = SimpleNamespace(file_id="001", decode_unit=4, sync_code=b"", sync_code_offset=0)

    result = build_decodable_df(df, missing=[], config=config)

    assert result.to_dict("records") == [
        {"Received time": "t1", "Data": "41424344"},
        {"Received time": "t3", "Data": "45464748"},
    ]


def test_extract_timestamp_obc_reads_little_endian_unix_time():
    timestamp = int(datetime(2021, 1, 1, 0, 0, 16, tzinfo=timezone.utc).timestamp())
    chunk = bytearray(191)
    chunk[185:189] = timestamp.to_bytes(4, "little")

    assert extract_timestamp_obc(bytes(chunk)) == datetime(2021, 1, 1, 0, 0, 16, tzinfo=timezone.utc)


def test_build_decodable_df_adds_timestamp_obc_for_main_hk():
    timestamp = int(datetime(2021, 1, 1, 0, 0, 16, tzinfo=timezone.utc).timestamp())
    chunk = bytearray(191)
    chunk[185:189] = timestamp.to_bytes(4, "little")
    df = pd.DataFrame([{"Packet no.": 1, "Data": bytes(chunk), "Datetime": "received"}])
    config = SimpleNamespace(file_id="110", decode_unit=191, sync_code=b"", sync_code_offset=0)

    result = build_decodable_df(df, missing=[], config=config)

    assert result.to_dict("records") == [
        {
            "Received time": "received",
            "Data": bytes(chunk).hex(),
            "timestamp_obc": datetime(2021, 1, 1, 0, 0, 16, tzinfo=timezone.utc),
        }
    ]


def test_extract_timestamp_adcs_reads_little_endian_unix_time_from_byte_two():
    timestamp = int(datetime(2026, 3, 12, 15, 40, 27, tzinfo=timezone.utc).timestamp())
    chunk = bytearray(1473)
    chunk[2:6] = timestamp.to_bytes(4, "little")

    assert extract_timestamp_adcs(bytes(chunk)) == datetime(2026, 3, 12, 15, 40, 27, tzinfo=timezone.utc)


def test_build_decodable_df_adds_timestamp_adcs_for_high_and_normal_adcs():
    timestamp = int(datetime(2026, 3, 12, 15, 40, 27, tzinfo=timezone.utc).timestamp())
    chunk = bytearray(1473)
    chunk[2:6] = timestamp.to_bytes(4, "little")
    df = pd.DataFrame([{"Packet no.": 1, "Data": bytes(chunk), "Datetime": "received"}])

    for file_id in ("011", "100"):
        config = SimpleNamespace(file_id=file_id, decode_unit=1473, sync_code=b"", sync_code_offset=0)

        result = build_decodable_df(df, missing=[], config=config)

        assert result.iloc[0]["Received time"] == "received"
        assert result.iloc[0]["Data"] == bytes(chunk).hex()
        assert result.iloc[0]["timestamp_adcs"] == datetime(2026, 3, 12, 15, 40, 27, tzinfo=timezone.utc)
