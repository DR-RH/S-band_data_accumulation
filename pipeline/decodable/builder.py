import pandas as pd

def build_decodable_df(
    df: pd.DataFrame,
    missing: list[int],
    config,
    # decode_unit: int,
    # sync_code:bytes,
) -> pd.DataFrame:

    df = df.sort_values("Packet no.").reset_index(drop=True)
    missing_set = set(missing)
    buffer = b""
    results = []
    decode_unit = config.decode_unit
    sync_code = config.sync_code
    sync_code_offset = config.sync_code_offset
    sync_code_is_found = False
    for _, row in df.iterrows():
        pkt_no = row["Packet no."]
        data   = row["Data"]
        ts     = row["Datetime"]
        if pkt_no in missing_set:
            buffer = b""
            continue
        buffer += data

        if not sync_code_is_found:
            
            pos = buffer.find(sync_code)
            if pos != -1:
                start = pos - sync_code_offset
                if start < 0:
                    continue
                print(sync_code)
                print('find a sync code')
                buffer = buffer[start:]
                print(buffer)
                sync_code_is_found = True
            continue

        while len(buffer) >= decode_unit:
            chunk = buffer[:decode_unit]
            results.append({
                "Datetime": ts,
                "Data": chunk.hex()
            })

            buffer = buffer[decode_unit:]

    return pd.DataFrame(results)