from pathlib import Path
from typing import Dict
from pipeline.utils.decode_common import fix_broken_bin
from pipeline.utils.decode_common import get_decode_unit_from_key
import time
from datetime import datetime
import pandas as pd
DATATYPE = {
    "000": "unassigned",
    "001": "main_exe_log",
    "010": "real_time_TLM",
    "011": "adcs_high",
    "100": "adcs_normal",
    "101": "mission_data",
    "110": "main_HK_log",
    "111": "adcs_exe_log",
}

def get_filename_time(id_time):
    TIME_UNIT = 600
    CYCLE = 2**13

    offset = int(id_time, 2)
    now = int(time.time())
    cycle_index = now // TIME_UNIT // CYCLE
    candidate = cycle_index * CYCLE * TIME_UNIT + offset * TIME_UNIT
    if candidate > now:
        candidate -= CYCLE * TIME_UNIT
    dt = datetime.fromtimestamp(candidate)
    filename_time = dt.strftime("%Y-%m-%d_%H%M")
    return filename_time

def write_df(df:pd.DataFrame,
            key:str,
            out_dir:Path):

    id_type, id_time = key[:3], key[3:]
    filename_time = get_filename_time(id_time)

    csv = out_dir/ f"step4_concat_data_ID_{id_type}_{key}_{filename_time}.csv"
    df.to_csv(csv)
    return

def write_decodable_df(df:pd.DataFrame,key:str,save_datetime):
    id_type, id_time = key[:3], key[3:]
    data_type = DATATYPE[id_type]
    filename_time = get_filename_time(id_time)
    prefix = f"data/intermediate_output/step4_concat_data_ID_{id_type}_{data_type}_{filename_time}.csv"
    df.to_csv(prefix)

def write_concat_binaries(
    data_map: Dict[int, Dict],
    out_dir: Path,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    for key, value_dict in data_map.items():
        binary = value_dict["payload"]
        missing = value_dict["missing"]
        id_type, id_time = key[:3], key[3:]
        data_type = DATATYPE[id_type]
        
        filename_time = get_filename_time(id_time)

        decode_unit = get_decode_unit_from_key(key)
        binary_decodable = fix_broken_bin(binary, missing,decode_unit)

        prefix = f"step4_concat_data_ID_{id_type}_{data_type}_{filename_time}"
        raw_path = out_dir / f"{prefix}_raw_filled.bin"
        missing_path = out_dir / f"{prefix}_missing.csv"
        decodable_path = out_dir / f"{prefix}_decodable.bin"

        with open(raw_path, "wb") as f:
            f.write(binary)

        with open(missing_path, "w") as f:
            f.write(",".join(map(str, missing)))

        with open(decodable_path, "wb") as f:
            f.write(binary_decodable)

    return binary_decodable

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