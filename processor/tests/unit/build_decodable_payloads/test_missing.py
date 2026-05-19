import pandas as pd

from pipeline.build_decodable_payloads.constants import AUTO_PACKET_ID
from pipeline.build_decodable_payloads.missing import detect_missing_packet, get_missing_packets


def test_detect_missing_packet():
    df = pd.DataFrame(
        {
            "Packet ID": ["001A", "001A", "001A", AUTO_PACKET_ID, AUTO_PACKET_ID],
            "Packet no.": [1, 3, 4, 5, 7],
            "Data": [b"a", b"b", b"c", b"d", b"e"],
        }
    )

    result = detect_missing_packet(df)

    assert result["001A"]["missing"] == [2]
    assert result[AUTO_PACKET_ID]["missing"] == []
    assert result["001A"]["df"]["Packet no."].tolist() == [1, 3, 4]


def test_detect_missing_packet_preserves_stream_order_for_builder():
    df = pd.DataFrame(
        {
            "Packet ID": ["001A", "001A", "001A", "001A"],
            "Packet no.": [0, 1, 0, 1],
            "Data": [b"a", b"b", b"c", b"d"],
        }
    )

    result = detect_missing_packet(df)

    assert result["001A"]["missing"] == []
    assert result["001A"]["df"]["Data"].tolist() == [b"a", b"b", b"c", b"d"]


def test_get_missing_packets():
    group = pd.DataFrame({"Packet no.": [10, 12, 13, 16]})

    assert get_missing_packets(group) == [11, 14, 15]
