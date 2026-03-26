import struct
import pandas as pd
import json
from datetime import datetime
import pytz
with open("scratch/decode_config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

groups = config["groups"]

def unpack_by_config(chunk: bytes, fmt: str, columns: list[str]) -> dict:
    size = struct.calcsize(fmt)
    if len(chunk) != size:
        raise ValueError(f"size mismatch: {len(chunk)} != {size}")

    values = struct.unpack(fmt, chunk)
    return dict(zip(columns, values))

def extract_bits_be(data: bytes, start_byte: int, shift_bit: int, bit_width: int) -> int:
    total_bits = len(data) * 8
    start_bit = (start_byte - 1) * 8 + shift_bit
    x = int.from_bytes(data, "big")
    right_shift = total_bits - (start_bit + bit_width)
    mask = (1 << bit_width) - 1
    return (x >> right_shift) & mask

def decode_adcs_with_json(chunk_73: bytes,) -> dict:
    json_path: str = "scratch/adcs_main_HK_list.json"
    if len(chunk_73) != 73:
        raise ValueError(f"chunk length must be 73 bytes, got {len(chunk_73)}")
    with open(json_path, "r", encoding="utf-8") as f:
        spec = json.load(f)

    row_dict = {}
    for field in spec:
        name = field["name"]
        start_byte = field["start_byte"]
        shift_bit = field["shift_bit"]
        bit_width = field["bit_width"]
        raw_value = extract_bits_be(chunk_73, start_byte, shift_bit, bit_width)
        row_dict[name] = raw_value
    return row_dict

# def decode_adcs_chunks_to_df(chunks_73: list[bytes) -> pd.DataFrame:
#     rows = [decode_adcs_with_json(chunk) for chunk in chunks_73]
#     return pd.DataFrame(rows)


filename = "test_data/step4_concat_data_ID_110_main_HK_log_2026-03-12_1540.csv"
df = pd.read_csv(filename)

group_dfs = []

for group_name, spec in groups.items():
    fmt = spec["format"]
    columns = spec["columns"]
    rows = []

    for decodable_chunk in df["Data"]:
        if decodable_chunk[-4:] != "b00b":
            continue
            # print(decodable_chunk[-4:] )
            # print("skip")
            # input()
        chunk = bytes.fromhex(decodable_chunk)
        chunk = chunk[:-2]  # cut CRC
        row = unpack_by_config(chunk, fmt, columns)
        rows.append(row)

    group_df = pd.DataFrame(rows, columns=columns)
    group_df.columns = pd.MultiIndex.from_product(
        [[group_name], group_df.columns],
        names=["group", "field"]
    )
    group_dfs.append(group_df)

#decode adcs part
rows = []

for decodable_chunk in df["Data"]:
    if decodable_chunk[-4:] != "b00b":
        continue
    chunk = bytes.fromhex(decodable_chunk)
    chunk = chunk[:-2]           # CRCを落とす
    chunk_73 = chunk[96:169]     # ADCS 73 bytes
    row_dict = decode_adcs_with_json(chunk_73)
    rows.append(row_dict)
group_df = pd.DataFrame(rows)
group_df.columns = pd.MultiIndex.from_product(
    [["adcs pic"], group_df.columns],
    names=["group", "field"]
)
group_dfs.append(group_df)
# print(group_dfs)
main_df = pd.concat(group_dfs, axis=1)


# print(main_df.columns)
# main_df = main_df.sort_values(by=["OBC pic","timestamp_obc"])
main_df = main_df.sort_values(by=[("OBC pic", "timestamp_obc")])
for timestamp in main_df["OBC pic","timestamp_obc"]:
    time = datetime.fromtimestamp(timestamp , tz=pytz.UTC).strftime("%Y/%m/%d %H:%M:%S") 
    print(timestamp)
save_path = 'scratch/check.csv'
main_df.to_csv(save_path,index=False)