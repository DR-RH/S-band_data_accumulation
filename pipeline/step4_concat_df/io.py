from pathlib import Path
from typing import Dict


def write_concat_binaries(
    data_map: Dict[int, Dict],
    out_dir: Path,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for key, value_dict in data_map.items():
        binary = value_dict["payload"]
        missing = value_dict["missing"]
        path = out_dir / f"step4_concat_data_ID_{key}.bin"
        with open(path, "wb") as f:
            f.write(binary)
        path_missing = out_dir / f"step4_concat_data_ID_{key}_missing.csv"
        with open(path_missing, "w") as f:
            f.write(",".join(map(str, missing)))


# def write_missing_report(
#     missing: list[int],
#     out_dir: Path,
# ) -> None:
#     out_dir.mkdir(parents=True, exist_ok=True)

#     for key, binary in data_map.items():
#         path = out_dir / f"step4_concat_data_length_{key}.bin"
#         with open(path, "wb") as f:
#             f.write(binary)