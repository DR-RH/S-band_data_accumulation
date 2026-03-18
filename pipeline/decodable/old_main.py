from pathlib import Path

from .io import write_decodable_df
import pandas as pd
from pipeline.utils.decode_common import get_decode_unit_from_key


FILL_VALUE = b'\xFF'
DUMMY_DATETIME = pd.Timestamp("2030-01-01")
AUTO_PACKET_ID = "0101011001000101"

# def _break_packets(df):
#     # number_of_list = len(df)
#     rand_vals = np.random.rand(len(df))
#     df = df[rand_vals > 0.2]

#     return df
"""
def process_decodable_df(df: pd.DataFrame, output_path: Path):

    order_key = "Packet no."

    sorted_df = df.sort_values(order_key)
    debug_df = _break_packets(sorted_df)  # debug用途

    grouped = detect_missing_packet(debug_df)

    for packet_id, group_info in grouped.items():

        if packet_id == AUTO_PACKET_ID:
            continue

        process_packet_group(packet_id, group_info, output_path)
"""
# def process_packet_group(packet_id, group_info, output_path: Path):

#     group_df = group_info["df"]
#     missing_packets = group_info["missing"]

#     data_type = packet_id[:3]
#     decode_unit = get_decode_unit_from_key(data_type)

#     decodable_df = build_decodable_df(
#         group_df,
#         missing_packets,
#         decode_unit
#     )

#     write_decodable_df(decodable_df, packet_id, output_path)
"""
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

    return pd.DataFrame(results)"""

# # Archive
# def insert_missing_packets(group: pd.DataFrame, missing):
#     block = 116

#     new_rows = pd.DataFrame({
#         "Packet no.": missing,
#         "Data": [FILL_VALUE * block for _ in range(len(missing))],
#         "Datetime": [DUMMY_DATETIME for _ in range(len(missing))]
#     })

#     # 列構造を揃える（FutureWarning対策）
#     new_rows = new_rows.reindex(columns=group.columns)

#     group = pd.concat([group, new_rows], ignore_index=True)

#     group = group.sort_values("Packet no.").reset_index(drop=True)

#     return group

"""def detect_missing_packet(df: pd.DataFrame):
    group_key = "Packet ID"
    result = {}

    for key, group in df.groupby(group_key, sort=True):
        group = group.sort_values("Packet no.")

        missing = []
        if key != AUTO_PACKET_ID:
            missing = get_missing_packets(group)

        result[key] = {
            "df": group,
            "missing": missing
        }

    return result

def get_missing_packets(group):
    packets = group["Packet no."].sort_values()

    expected = set(range(packets.min(), packets.max() + 1))
    actual = set(packets.values)

    missing = sorted(expected - actual)
    return missing"""