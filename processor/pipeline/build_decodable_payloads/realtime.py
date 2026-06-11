from __future__ import annotations

import ast
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pandas as pd


MARKERS = (b"VERTECSUTELEMETRY", b"VERTECSVTELEMETRY")
PAIR_PREFIX_SIZE = len(b"VERTECSUTELEMETRY") + len(b" 0 ")
MAIN_FROM_PACKET_0_SIZE = 100
MAIN_FROM_PACKET_1_SIZE = 91
COM_FROM_PACKET_1_SIZE = 11
REALTIME_UNIT_SIZE = MAIN_FROM_PACKET_0_SIZE + MAIN_FROM_PACKET_1_SIZE + COM_FROM_PACKET_1_SIZE
TIMESTAMP_OBC_START = 185
TIMESTAMP_OBC_END = 189


@dataclass
class RealtimePacket:
    frame_counter: int
    indicator: str
    payload: bytes
    received_time: Any


def build_realtime_decodable_df(df: pd.DataFrame) -> pd.DataFrame:
    pending_packet_0: RealtimePacket | None = None
    last_combined: bytes | None = None
    results = []

    for _, row in df.reset_index(drop=True).iterrows():
        packet = parse_realtime_packet(row)
        if packet is None:
            continue

        if packet.indicator == "0":
            pending_packet_0 = packet
            continue

        if packet.indicator != "1" or pending_packet_0 is None:
            continue

        if packet.frame_counter != ((pending_packet_0.frame_counter + 1) & 0xFF):
            pending_packet_0 = None
            continue

        combined = combine_realtime_pair(pending_packet_0.payload, packet.payload)
        pending_packet_0 = None

        if combined is None or combined == last_combined:
            continue

        record = {
            "Received time": packet.received_time,
            "Data": combined.hex(),
        }
        timestamp_obc = extract_timestamp_obc(combined[: TIMESTAMP_OBC_END + 2])
        if timestamp_obc is not None:
            record["timestamp_obc"] = timestamp_obc

        results.append(record)
        last_combined = combined

    return pd.DataFrame(results)


def parse_realtime_packet(row: pd.Series) -> RealtimePacket | None:
    body = build_realtime_body(row)

    for marker in MARKERS:
        if not body.startswith(marker):
            continue

        suffix = body[len(marker) : len(marker) + 3]
        if suffix not in (b" 0 ", b" 1 "):
            return None

        return RealtimePacket(
            frame_counter=extract_frame_counter(row),
            indicator=chr(suffix[1]),
            payload=body[PAIR_PREFIX_SIZE:],
            received_time=row.get("Datetime"),
        )

    return None


def build_realtime_body(row: pd.Series) -> bytes:
    packet_id = packet_id_to_bytes(row["Packet ID"])
    total_number = int(row["Total number of packets"]).to_bytes(2, "big")
    packet_number = int(row["Packet no."]).to_bytes(2, "big")
    data = coerce_bytes(row["Data"])
    return packet_id + total_number + packet_number + data


def combine_realtime_pair(packet_0_payload: bytes, packet_1_payload: bytes) -> bytes | None:
    if len(packet_0_payload) < MAIN_FROM_PACKET_0_SIZE:
        return None
    if len(packet_1_payload) < MAIN_FROM_PACKET_1_SIZE + COM_FROM_PACKET_1_SIZE:
        return None

    main_pic_tlm = (
        packet_0_payload[:MAIN_FROM_PACKET_0_SIZE]
        + packet_1_payload[:MAIN_FROM_PACKET_1_SIZE]
    )
    com_pic_tlm = packet_1_payload[
        MAIN_FROM_PACKET_1_SIZE : MAIN_FROM_PACKET_1_SIZE + COM_FROM_PACKET_1_SIZE
    ]
    combined = main_pic_tlm + com_pic_tlm

    if len(combined) != REALTIME_UNIT_SIZE:
        return None
    return combined


def packet_id_to_bytes(value: Any) -> bytes:
    if isinstance(value, bytes):
        if len(value) != 2:
            raise ValueError(f"Packet ID must be 2 bytes, got {len(value)}")
        return value

    if isinstance(value, int):
        return value.to_bytes(2, "big")

    packet_id = str(value).strip()
    if set(packet_id) <= {"0", "1"}:
        return int(packet_id.zfill(16), 2).to_bytes(2, "big")

    raise ValueError(f"Unsupported Packet ID value: {value!r}")


def extract_frame_counter(row: pd.Series) -> int:
    high = int(row["Frame counter, higher bits"])
    low = int(row["Frame counter, lower bits"])
    return ((high & 0x1F) << 3) | (low & 0x07)


def coerce_bytes(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith(("b'", 'b"')):
            parsed = ast.literal_eval(stripped)
            if isinstance(parsed, bytes):
                return parsed
        return bytes.fromhex(stripped)

    raise TypeError(f"Cannot convert {type(value).__name__} to bytes")


def extract_timestamp_obc(main_pic_tlm: bytes) -> datetime | None:
    if len(main_pic_tlm) < TIMESTAMP_OBC_END:
        return None

    timestamp = int.from_bytes(
        main_pic_tlm[TIMESTAMP_OBC_START:TIMESTAMP_OBC_END], "little"
    )
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)
