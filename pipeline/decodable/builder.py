import pandas as pd

def build_decodable_df(
    df: pd.DataFrame,
    missing: list[int],
    decode_unit: int,
) -> pd.DataFrame:

    df = df.sort_values("Packet no.").reset_index(drop=True)
    missing_set = set(missing)

    buffer = b""
    results = []

    for _, row in df.iterrows():
        pkt_no = row["Packet no."]
        data   = row["Data"]
        ts     = row["Datetime"]

        if pkt_no in missing_set:
            buffer = b""
            continue
        buffer += data

        while len(buffer) >= decode_unit:
            chunk = buffer[:decode_unit]

            results.append({
                "Datetime": ts,
                "Data": chunk
            })

            buffer = buffer[decode_unit:]

    return pd.DataFrame(results)