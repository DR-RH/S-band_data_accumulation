from types import SimpleNamespace

import pandas as pd

from pipeline.build_decodable_payloads.builder import build_decodable_df


def test_build_decodable_df_builds_chunks_across_contiguous_packets():
    df = pd.DataFrame(
        [
            {"Packet no.": 1, "Data": b"AB", "Datetime": "t1"},
            {"Packet no.": 2, "Data": b"CD", "Datetime": "t2"},
        ]
    )
    config = SimpleNamespace(decode_unit=4, sync_code=b"", sync_code_offset=0)

    result = build_decodable_df(df, missing=[], config=config)

    assert result.to_dict("records") == [{"Datetime": "t2", "Data": "41424344"}]


def test_build_decodable_df_resets_buffer_when_packet_number_jumps():
    df = pd.DataFrame(
        [
            {"Packet no.": 1, "Data": b"AB", "Datetime": "t1"},
            {"Packet no.": 3, "Data": b"CD", "Datetime": "t3"},
            {"Packet no.": 4, "Data": b"EF", "Datetime": "t4"},
        ]
    )
    config = SimpleNamespace(decode_unit=4, sync_code=b"", sync_code_offset=0)

    result = build_decodable_df(df, missing=[2], config=config)

    assert result.to_dict("records") == [{"Datetime": "t4", "Data": "43444546"}]
