from pathlib import Path
from typing import Dict
from pipeline.utils.decode_common import fix_broken_bin
from pipeline.utils.decode_common import get_decode_unit_from_key


def write_concat_binaries(
    data_map: Dict[int, Dict],
    out_dir: Path,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for key, value_dict in data_map.items():
        binary = value_dict["payload"]
        missing = value_dict["missing"]
        path = out_dir / f"step4_concat_data_ID_{key}_raw_filled.bin"
        with open(path, "wb") as f:
            f.write(binary)
        path_missing = out_dir / f"step4_concat_data_ID_{key}_missing.csv"
        with open(path_missing, "w") as f:
            f.write(",".join(map(str, missing)))
        decode_byte_unit = get_decode_unit_from_key(key)
        binary_decodable = fix_broken_bin(binary, missing,decode_byte_unit)

        path_decodable_bin = out_dir / f"step4_concat_data_ID_{key}_decodable.bin"
        with open(path_decodable_bin, "wb") as f:
            f.write(binary_decodable)

def extract_decodable_packet(
    binary,
    missing: list):

    return 
# def write_missing_report(
#     missing: list[int],
#     out_dir: Path,
# ) -> None:
#     out_dir.mkdir(parents=True, exist_ok=True)

#     for key, binary in data_map.items():
#         path = out_dir / f"step4_concat_data_length_{key}.bin"
#         with open(path, "wb") as f:
#             f.write(binary)