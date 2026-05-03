import pandas as pd

def build_decodable_df(
    df: pd.DataFrame,
    missing: list[int],
    config,
    # decode_unit: int,
    # sync_code:bytes,
    ) -> pd.DataFrame:

    df = df.sort_values("Packet no.").reset_index(drop=True)
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

            results.append({
                "Datetime": ts,
                "Data": chunk.hex()
            })

            # 次を探すために進める
            buffer = buffer[decode_unit:]
    return pd.DataFrame(results)
