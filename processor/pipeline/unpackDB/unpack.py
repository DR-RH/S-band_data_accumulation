import pandas as pd
import json

def extract_bits(data: bytes, start_byte: int, shift_bit: int, bit_width: int, endian:str) -> int:
    total_bits = len(data) * 8
    start_bit = (start_byte - 1) * 8 + shift_bit
    if endian == ">":
        endian_str = "big"
    else:
        endian_str = "little"
    x = int.from_bytes(data, endian_str)
    shift = total_bits - (start_bit + bit_width)
    mask = (1 << bit_width) - 1
    return (x >> shift) & mask


def my_extract_bits(data: bytes, start_byte: int, shift_bit: int, bit_width: int, endian: str) -> int:
    endian_str = "big" if endian == ">" else "little"
    byte_offset = start_byte - 1
    total_bits = len(data) * 8
    start_bit = byte_offset * 8 + shift_bit
    
    if start_bit + bit_width > total_bits:
        raise ValueError(f"Range exceed: {start_bit}+{bit_width}>{total_bits}")
    
    if bit_width % 8 == 0 and shift_bit == 0:
        # バイト整列完全field: 高速path
        n_bytes = bit_width // 8
        return int.from_bytes(data[byte_offset:byte_offset + n_bytes], endian_str)
    
    # 汎用bit field
    x = int.from_bytes(data, endian_str)
    mask = (1 << bit_width) - 1
    shift = total_bits - (start_bit + bit_width)
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
            raw_value = my_extract_bits(chunk, start_byte, shift_bit, bit_width, endian)
            values.append(raw_value)
            index_tuples.append((group_name, name))
    
    # dict(zip(index_tuples, values)) で MultiIndex 対応 dict に変換
    return dict(zip(index_tuples, values))


def decode_chunks_to_multiindex_df(chunks: list[bytes], schema_path: str) -> pd.DataFrame:
    """複数 chunk を MultiIndex DataFrame に"""
    
    rows = []
    for chunk in chunks:
        if chunk[-2:] != b'\xb0\x0b':
            continue 


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


def run(config_path):


    index_tuple = build_column_schema_from_config(config_path)


    filename = "test_data/data_sample.csv"
    df = pd.read_csv(filename)
    chunks = df["Data"].apply(bytes.fromhex)
    orig_hex = df["Data"]
    main_df = decode_chunks_to_multiindex_df(chunks, config_path)
    main_df.to_csv('scratch/value_converted.csv',index=False)

    return main_df
