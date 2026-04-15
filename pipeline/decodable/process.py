
from pipeline.decodable.builder import build_decodable_df
from pipeline.decodable.missing import detect_missing_packet
from pipeline.decodable.constants import AUTO_PACKET_ID
from pipeline.decodable.debug import _break_packets
from pipeline.decodable.io import write_decodable_df
from pipeline.utils.decode_common import get_decode_unit_from_key, DECODER_REGISTRY
import pandas as pd
from pathlib import Path

def process_decodable_df(input_df: pd.DataFrame, output_path: Path):

    packet_order_key = "Packet no."

    ordered_df = input_df.sort_values(packet_order_key)
    # sampled_df = _break_packets(ordered_df)  # debug用途
    sampled_df = ordered_df
    packet_groups = detect_missing_packet(sampled_df)

    for packet_id, packet_bundle in packet_groups.items():

        if packet_id == AUTO_PACKET_ID:
            continue

        decodable_df = build_decodable_from_group(packet_id, packet_bundle)
        write_decodable_df(decodable_df, packet_id, output_path)


def build_decodable_from_group(packet_id, packet_bundle) -> pd.DataFrame:

    packet_df = packet_bundle["df"]
    missing_packets = packet_bundle["missing"]

    data_type = extract_data_type(packet_id)
    config = DECODER_REGISTRY.get(data_type)
    # decode_unit = get_decode_unit_from_key(data_type)
    # data_offset_by_sync_code()

    decodable_df = build_decodable_df(
        packet_df,
        missing_packets,
        config
    )
    return decodable_df

def extract_data_type(packet_id: str) -> str:
    return packet_id[:3]