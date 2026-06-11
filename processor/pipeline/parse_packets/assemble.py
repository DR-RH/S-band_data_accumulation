import pandas as pd
from .framing import split_into_packets
from .parse import parse_packet
import json
from pathlib import Path
from pipeline.utils.constants import get_packet_size

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def load_structure_file(gse):
    if gse == 'Kyutech':
        path = CONFIG_DIR / "s_packet_structure_modified_for_Kyutech.json"
    else:
        path = CONFIG_DIR / "s_packet_structure_modified_for_ISAS.json"
    with open(path, "r", encoding="utf-8") as f:
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
