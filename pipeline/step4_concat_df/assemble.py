from typing import Dict
import pandas as pd
AUTO_PACKET_ID = "0101011001000101"

def insert_missing_packets(group, missing):
    block = 116
    new_rows = pd.DataFrame({
        "Packet no.": missing,
        "Data": [b'\xFF' * block] * len(missing)
    })

    group = pd.concat([group, new_rows], ignore_index=True)

    group = group.sort_values("Packet no.").reset_index(drop=True)

    return group

def concat_payloads_by_key(
    df: pd.DataFrame,
    # group_key: str,
    # data_column: str,
    ) -> Dict[int, bytes]:
    """
    Group dataframe by group_key and concat bytes in data_column.
    """

    group_key="Packet ID"
    data_column="Data"
    result = {}

    for key, group in df.groupby(group_key, sort=True):
        group = group.sort_values("Packet no.")
        payloads = group[data_column]
        missing = []

        if not all(isinstance(x, (bytes, bytearray)) for x in payloads):
            raise TypeError("data_column must contain bytes")

        if  key != AUTO_PACKET_ID:
            missing = get_missing_packets(group)
            group = insert_missing_packets(group, missing)
            group = group.sort_values("Packet no.")
            # payload = b"".join(group[data_column])
        #     decode_byte_unit = get_decode_unit_from_key(key)
        #     payload = _fix_broken_bin(payload,missing,decode_byte_unit)
        # else:
        payload = b"".join(group[data_column])
        result[key] = {
            "payload": payload,
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