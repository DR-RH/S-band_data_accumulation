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
    previous_pkt_no = None

    decode_unit = config.decode_unit
    sync_code = config.sync_code
    sync_code_offset = config.sync_code_offset

    for _, row in df.iterrows():
        pkt_no = row["Packet no."]
        data   = row["Data"]
        ts     = row["Datetime"]

        if previous_pkt_no is not None and pkt_no != previous_pkt_no + 1:
            buffer = b""

        previous_pkt_no = pkt_no

        buffer += data

        while True:
            pos = buffer.find(sync_code)
            if pos == -1:
                break

            start = pos - sync_code_offset
            if start < 0:
                # sync codeが途中にかかってる → 次のデータ待ち
                break

            # 同期位置に揃える
            buffer = buffer[start:]

            # decode可能かチェック
            if len(buffer) < decode_unit:
                break

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

            # 次を探すために進める
            buffer = buffer[decode_unit:]
    return pd.DataFrame(results)
