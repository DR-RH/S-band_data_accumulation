import pandas as pd
import json

def extract_bits(data: bytes, start_byte: int, shift_bit: int, bit_width: int, endian:str) -> int:
    total_bits = len(data) * 8
    start_bit = (start_byte - 1) * 8 + shift_bit
    # print(endian)
    if endian == ">":
        endian_str = "little"
    else:
        endian_str = "big"

    x = int.from_bytes(data, endian_str)
    shift = total_bits - (start_bit + bit_width)
    mask = (1 << bit_width) - 1
    return (x >> shift) & mask

def unpack_to_multiindex_dict(values: list[int], index_tuples: list[tuple]) -> dict:
    """
    values と index_tuples を zip して MultiIndex 用 dict に変換
    """
    return dict(zip(index_tuples, values))


# 修正版デコード関数
def decode_chunk_with_schema(chunk: bytes, schema_path: str) -> dict:
    """統一スキーマで chunk をデコード（MultiIndex 対応）"""
    
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    
    values = []
    index_tuples = []
    
    # 全グループを順に処理
    for group_name, group_info in schema.items():
        endian = group_info["byte_order"]
        fields = group_info["fields"]
        
        for field in fields:
            name = field["name"]
            start_byte = field["start_byte"]
            shift_bit = field["shift_bit"]
            bit_width = field["bit_width"]
            
            # bit field 抽出
            raw_value = extract_bits(chunk, start_byte, shift_bit, bit_width, endian)
            values.append(raw_value)
            index_tuples.append((group_name, name))
    
    # dict(zip(index_tuples, values)) で MultiIndex 対応 dict に変換
    return dict(zip(index_tuples, values))


def decode_chunks_to_multiindex_df(chunks: list[bytes], schema_path: str) -> pd.DataFrame:
    """複数 chunk を MultiIndex DataFrame に"""
    
    rows = []
    
    for chunk in chunks:
        row_dict = decode_chunk_with_schema(chunk, schema_path)
        rows.append(row_dict)
    
    # 列名をスキーマ順に固定
    schema_columns = build_column_schema_from_config(schema_path)
    
    df = pd.DataFrame(rows)
    df.columns = pd.MultiIndex.from_tuples(df.columns, names=["group", "field"])
    df = df.reindex(columns=schema_columns)
    
    return df


def build_column_schema_from_config(config_path: str) -> pd.MultiIndex:
    """
    JSON config から列順を復元する MultiIndex を作成
    """
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    column_tuples = []

    # 各グループの fields を順番に追加
    for group_name, group_info in config.items():
        for field in group_info.get("fields", []):
            column_tuples.append((group_name, field["name"]))
    
    return pd.MultiIndex.from_tuples(
        column_tuples,
        names=["group", "field"]
    )

config_path = "scratch/new_fmt_conbined.json"
index_tuple = build_column_schema_from_config(config_path)

# def decode_adcs_chunks_to_df(chunks_73: list[bytes) -> pd.DataFrame:
#     rows = [decode_adcs_with_json(chunk) for chunk in chunks_73]
#     return pd.DataFrame(rows)


filename = "test_data/step4_concat_data_ID_110_main_HK_log_2026-03-12_1540.csv"
df = pd.read_csv(filename)
chunks = df["Data"].apply(bytes.fromhex)


df = decode_chunks_to_multiindex_df(chunks, config_path)
print(df)
df.to_csv('scratch/test.csv',index=False)


# group_dfs = []

# for group_name, spec in groups.items():
#     fmt = spec["format"]
#     columns = spec["columns"]
#     rows = []

#     for decodable_chunk in df["Data"]:
#         if decodable_chunk[-4:] != "b00b":
#             continue
#             # print(decodable_chunk[-4:] )
#             # print("skip")
#             # input()
#         chunk = bytes.fromhex(decodable_chunk)
#         chunk = chunk[:-2]  # cut CRC
#         row = unpack_by_config(chunk, fmt, columns)
#         rows.append(row)

#     group_df = pd.DataFrame(rows, columns=columns)
#     group_df.columns = pd.MultiIndex.from_product(
#         [[group_name], group_df.columns],
#         names=["group", "field"]
#     )
#     group_dfs.append(group_df)

# #decode adcs part
# rows = []

# for decodable_chunk in df["Data"]:
#     if decodable_chunk[-4:] != "b00b":
#         continue
#     chunk = bytes.fromhex(decodable_chunk)
#     chunk = chunk[:-2]           # CRCを落とす
#     chunk_73 = chunk[96:169]     # ADCS 73 bytes
#     row_dict = decode_adcs_with_json(chunk_73)
#     rows.append(row_dict)
# group_df = pd.DataFrame(rows)
# group_df.columns = pd.MultiIndex.from_product(
#     [["adcs pic"], group_df.columns],
#     names=["group", "field"]
# )
# group_dfs.append(group_df)
# # print(group_dfs)
# main_df = pd.concat(group_dfs, axis=1)


# # print(main_df.columns)
# # main_df = main_df.sort_values(by=["OBC pic","timestamp_obc"])
# main_df = main_df.sort_values(by=[("OBC pic", "timestamp_obc")])
# for timestamp in main_df["OBC pic","timestamp_obc"]:
#     time = datetime.fromtimestamp(timestamp , tz=pytz.UTC).strftime("%Y/%m/%d %H:%M:%S") 
#     print(timestamp)
# save_path = 'scratch/check.csv'
# main_df.to_csv(save_path,index=False)