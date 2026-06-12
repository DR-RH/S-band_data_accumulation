import pandas as pd

from pipeline.build_decodable_payloads.constants import AUTO_PACKET_ID
from pipeline.build_decodable_payloads.realtime import build_realtime_decodable_df


MARKER_TAIL = b"SUTELEMETRY"
TOTAL_NUMBER = int.from_bytes(b"RT", "big")
PACKET_NUMBER = int.from_bytes(b"EC", "big")


def make_row(frame: int, indicator: str, payload: bytes, data_as_literal=False):
    data = MARKER_TAIL + f" {indicator} ".encode("ascii") + payload
    return {
        "Datetime": f"2026-05-23T19:19:06.{frame:06d}+00:00",
        "Frame counter, higher bits": frame >> 3,
        "Frame counter, lower bits": frame & 0x07,
        "Packet ID": AUTO_PACKET_ID,
        "Total number of packets": TOTAL_NUMBER,
        "Packet no.": PACKET_NUMBER,
        "Data": repr(data) if data_as_literal else data,
    }


def test_build_realtime_decodable_df_pairs_0_and_1_payloads():
    packet_0_payload = bytes(range(102))
    packet_1_payload = bytes(range(102, 204))
    df = pd.DataFrame(
        [
            make_row(0x78, "0", packet_0_payload),
            make_row(0x79, "1", packet_1_payload),
        ]
    )

    result = build_realtime_decodable_df(df)

    expected = (
        packet_0_payload[2:102]
        + packet_1_payload[:91]
        + packet_1_payload[91:102]
    )
    assert result["Data"].tolist() == [expected.hex()]
    assert result["Received time"].tolist() == ["2026-05-23T19:19:06.000121+00:00"]


def test_build_realtime_decodable_df_skips_consecutive_duplicates():
    packet_0_payload = bytes(range(102))
    packet_1_payload = bytes(range(102, 204))
    df = pd.DataFrame(
        [
            make_row(0x78, "0", packet_0_payload),
            make_row(0x79, "1", packet_1_payload),
            make_row(0x7A, "0", packet_0_payload),
            make_row(0x7B, "1", packet_1_payload),
        ]
    )

    result = build_realtime_decodable_df(df)

    assert len(result) == 1


def test_build_realtime_decodable_df_accepts_csv_style_values():
    packet_0_payload = bytes(range(102))
    packet_1_payload = bytes(range(102, 204))
    df = pd.DataFrame(
        [
            make_row(0x78, "0", packet_0_payload, data_as_literal=True),
            make_row(0x79, "1", packet_1_payload, data_as_literal=True),
        ]
    )
    df["Packet ID"] = df["Packet ID"].str.lstrip("0")

    result = build_realtime_decodable_df(df)

    assert len(result) == 1
