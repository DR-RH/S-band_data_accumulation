from pipeline.decodable.constants import AUTO_PACKET_ID
import pandas as pd

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

def get_missing_packets(group):
    packets = group["Packet no."].sort_values()

    expected = set(range(packets.min(), packets.max() + 1))
    actual = set(packets.values)

    missing = sorted(expected - actual)
    return missing