from datetime import datetime, timezone

import pandas as pd


MAIN_HK_FILE_ID = "110"
ADCS_HK_FILE_IDS = {"011", "100"}
TIMESTAMP_OBC_START = 185
TIMESTAMP_OBC_END = 189
TIMESTAMP_ADCS_START = 2
TIMESTAMP_ADCS_END = 6


def extract_timestamp_obc(chunk: bytes) -> datetime:
    timestamp = int.from_bytes(chunk[TIMESTAMP_OBC_START:TIMESTAMP_OBC_END], "little")
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def extract_timestamp_adcs(chunk: bytes) -> datetime:
    timestamp = int.from_bytes(chunk[TIMESTAMP_ADCS_START:TIMESTAMP_ADCS_END], "little")
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)

def build_decodable_df(
    df: pd.DataFrame,
    missing: list[int],
    config,
    # decode_unit: int,
    # sync_code:bytes,
    ) -> pd.DataFrame:

    df = df.reset_index(drop=True)
    buffer = b""
    results = []
    lost_units = []
    unit_index = 0
    previous_pkt_no = None
    previous_ts = None
    pending_gap = None

    decode_unit = config.decode_unit
    sync_code = config.sync_code
    sync_code_offset = config.sync_code_offset

    for _, row in df.iterrows():
        pkt_no = row["Packet no."]
        data   = row["Data"]
        ts     = row["Datetime"]

        if previous_pkt_no is not None and pkt_no != previous_pkt_no + 1:
            if pkt_no > previous_pkt_no + 1:
                pending_gap = {
                    "lost_unit_index": unit_index,
                    "previous_packet_no": previous_pkt_no,
                    "next_packet_no": pkt_no,
                    "missing_packet_start": previous_pkt_no + 1,
                    "missing_packet_end": pkt_no - 1,
                    "missing_packet_count": pkt_no - previous_pkt_no - 1,
                    "received_time_before_gap": previous_ts,
                    "received_time_after_gap": ts,
                    "discarded_buffer_bytes": len(buffer),
                }
                unit_index += 1
            else:
                pending_gap = None
            buffer = b""

        previous_pkt_no = pkt_no
        previous_ts = ts

        buffer += data

        while True:
            pos = buffer.find(sync_code)
            if pos == -1:
                break

            start = pos - sync_code_offset
            if start < 0:
                # The prefix for this sync was already lost, usually because a
                # prior packet failed CRC. Skip this incomplete unit and look
                # for the next sync instead of getting stuck on the same bytes.
                if pending_gap is not None:
                    lost_units.append(
                        build_lost_unit_record(
                            pending_gap,
                            lost_unit_index=pending_gap["lost_unit_index"],
                            reason="missing_prefix_before_sync",
                            config=config,
                            decode_unit=decode_unit,
                            sync_code=sync_code,
                            sync_code_offset=sync_code_offset,
                            sync_position=pos,
                            missing_prefix_bytes=-start,
                            received_time=ts,
                        )
                    )
                    pending_gap = None
                buffer = buffer[pos + len(sync_code):]
                continue

            # 同期位置に揃える
            buffer = buffer[start:]

            # decode可能かチェック
            if len(buffer) < decode_unit:
                break

            if pending_gap is not None:
                lost_units.append(
                    build_lost_unit_record(
                        pending_gap,
                        lost_unit_index=pending_gap["lost_unit_index"],
                        reason="packet_gap_discarded_decodable_unit",
                        config=config,
                        decode_unit=decode_unit,
                        sync_code=sync_code,
                        sync_code_offset=sync_code_offset,
                        sync_position=None,
                        missing_prefix_bytes=None,
                        received_time=pending_gap.get("received_time_after_gap"),
                    )
                )
                pending_gap = None

            chunk = buffer[:decode_unit]

            record = {
                "Received time": ts,
                "Data": chunk.hex()
            }
            if config.file_id == MAIN_HK_FILE_ID:
                record["timestamp_obc"] = extract_timestamp_obc(chunk)
            if config.file_id in ADCS_HK_FILE_IDS:
                record["timestamp_adcs"] = extract_timestamp_adcs(chunk)

            results.append(record)
            unit_index += 1

            # 次を探すために進める
            buffer = buffer[decode_unit:]

    if pending_gap is not None and pending_gap.get("discarded_buffer_bytes", 0):
        lost_units.append(
            build_lost_unit_record(
                pending_gap,
                lost_unit_index=pending_gap["lost_unit_index"],
                reason="packet_gap_discarded_partial_unit",
                config=config,
                decode_unit=decode_unit,
                sync_code=sync_code,
                sync_code_offset=sync_code_offset,
                sync_position=None,
                missing_prefix_bytes=None,
                received_time=pending_gap.get("received_time_after_gap"),
            )
        )

    result_df = pd.DataFrame(results)
    result_df.attrs["lost_units"] = lost_units
    return result_df


def build_lost_unit_record(
    pending_gap: dict | None,
    *,
    lost_unit_index: int,
    reason: str,
    config,
    decode_unit: int,
    sync_code: bytes,
    sync_code_offset: int,
    sync_position: int | None,
    missing_prefix_bytes: int | None,
    received_time,
) -> dict:
    return {
        **(pending_gap or {}),
        "lost_unit_index": lost_unit_index,
        "reason": reason,
        "file_id": config.file_id,
        "decode_unit": decode_unit,
        "sync_code": sync_code.hex(),
        "sync_code_offset": sync_code_offset,
        "sync_position": sync_position,
        "missing_prefix_bytes": missing_prefix_bytes,
        "received_time": received_time,
    }
