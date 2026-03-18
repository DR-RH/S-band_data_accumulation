from typing import Dict
import pandas as pd
# from .io import write_df
from pathlib import Path
FILL_VALUE = b'\xFF'
DUMMY_DATETIME = pd.Timestamp("2030-01-01")
AUTO_PACKET_ID = "0101011001000101"

# Archive
def insert_missing_packets(group: pd.DataFrame, missing):
    block = 116

    new_rows = pd.DataFrame({
        "Packet no.": missing,
        "Data": [FILL_VALUE * block for _ in range(len(missing))],
        "Datetime": [DUMMY_DATETIME for _ in range(len(missing))]
    })

    # 列構造を揃える（FutureWarning対策）
    new_rows = new_rows.reindex(columns=group.columns)

    group = pd.concat([group, new_rows], ignore_index=True)

    group = group.sort_values("Packet no.").reset_index(drop=True)

    return group

def detect_missing_packet(df: pd.DataFrame):
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

# def missing_packet_analysis(missing):
    
#     write_missing_report(missing,)
#     return 

def get_missing_packets(group):
    packets = group["Packet no."].sort_values()

    expected = set(range(packets.min(), packets.max() + 1))
    actual = set(packets.values)

    missing = sorted(expected - actual)
    return missing