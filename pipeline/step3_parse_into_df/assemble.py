import pandas as pd
from .framing import split_into_packets
from .parse import parse_packet
import json
from pipeline.utils.constants import get_packet_size


def load_structure_file(gse):
    if gse == 'ISAS':
        path = "config/s_packet_structure_modified_for_ISAS.json"
    else:
        path = "config/s_packet_structure_modified_for_Kyutech.json"
    with open(path, "r") as f:
        bit_map = json.load(f)
    return bit_map


def build_dataframe(
    binary: bytes,
    gse: str,
) -> pd.DataFrame:
    
    packet_size = get_packet_size(gse)
    bit_map = load_structure_file(gse)   

    records = []
    for i, packet in enumerate(split_into_packets(binary, packet_size)):
        records.append(parse_packet(packet, bit_map, i))

    return pd.DataFrame(records)
