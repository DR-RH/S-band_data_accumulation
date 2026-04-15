import json
import pandas as pd

def load_schema(schema_path: str) -> dict:
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_column_schema_from_config(config_path: str) -> pd.MultiIndex:
    config = load_schema(config_path)
    column_tuples = []

    for group_name, group_info in config.items():
        for field in group_info.get("fields", []):
            column_tuples.append((group_name, field["name"]))

    return pd.MultiIndex.from_tuples(column_tuples, names=["group", "field"])


def load_fields(schema_path: str) -> tuple[list[dict], int]:
    schema = load_schema(schema_path)
    fields = []
    max_end_bit = 0

    for group_name, group_info in schema.items():
        byte_order = group_info["byte_order"]

        for field in group_info["fields"]:
            start_byte = field["start_byte"]
            shift_bit = field["shift_bit"]
            bit_width = field["bit_width"]

            start_bit = (start_byte - 1) * 8 + shift_bit
            end_bit = start_bit + bit_width

            max_end_bit = max(max_end_bit, end_bit)

            fields.append({
                "group": group_name,
                "name": field["name"],
                "start_byte": start_byte,
                "shift_bit": shift_bit,
                "bit_width": bit_width,
                "byte_order": byte_order,
                "start_bit": start_bit,
                "end_bit": end_bit,
            })

    total_bits = ((max_end_bit + 7) // 8) * 8
    return fields, total_bits

def normalize_field_value_for_packing(value: int, bit_width: int, byte_order: str, shift_bit: int) -> int:
    if bit_width % 8 == 0 and shift_bit == 0 and bit_width > 8 and byte_order == "<":
        n_bytes = bit_width // 8
        return int.from_bytes(value.to_bytes(n_bytes, byteorder="little"), byteorder="big")
    return value


def pack_row_to_int(row: pd.Series, fields: list[dict], total_bits: int) -> int:
    acc = 0
    used_mask = 0

    for f in fields:
        value = int(row[(f["group"], f["name"])])
        bit_width = f["bit_width"]
        shift_bit = f["shift_bit"]

        if value < 0:
            raise ValueError(f"negative value: {(f['group'], f['name'])}={value}")
        if value >= (1 << bit_width):
            raise ValueError(f"value too large: {(f['group'], f['name'])}={value}, bit_width={bit_width}")

        packed_value = normalize_field_value_for_packing(
            value=value,
            bit_width=bit_width,
            byte_order=f["byte_order"],
            shift_bit=shift_bit,
        )

        shift = total_bits - (f["start_bit"] + bit_width)
        field_mask = ((1 << bit_width) - 1) << shift

        if acc & field_mask:
            raise ValueError(f"bit overlap: {(f['group'], f['name'])}")

        acc |= packed_value << shift
        used_mask |= field_mask

    return acc


def pack_row_to_bytes(row: pd.Series, fields: list[dict], total_bits: int) -> bytes:
    acc = pack_row_to_int(row, fields, total_bits)
    return acc.to_bytes(total_bits // 8, byteorder="big")


def df_to_hex_series(df: pd.DataFrame, schema_path: str) -> pd.Series:
    fields, total_bits = load_fields(schema_path)
    return df.apply(lambda row: pack_row_to_bytes(row, fields, total_bits).hex(), axis=1)


def load_value_df(value_csv_path: str, schema_path: str) -> pd.DataFrame:
    df = pd.read_csv(value_csv_path, header=[0, 1])
    schema_columns = build_column_schema_from_config(schema_path)
    df = df.reindex(columns=schema_columns)
    return df


def compare_with_original(recovered_hex: pd.Series, orig_csv_path: str) -> pd.DataFrame:
    orig_df = pd.read_csv(orig_csv_path)
    result = pd.DataFrame({
        "orig_hex": orig_df["Data"],
        "recovered_hex": recovered_hex
    })
    result["match"] = result["orig_hex"].str.lower() == result["recovered_hex"].str.lower()
    return result


def main():
    config_path = "scratch/new_fmt_conbined.json"
    csv_path = 'scratch/value_converted.csv'

    main_df = load_value_df(csv_path, config_path)
    recovered_hex = df_to_hex_series(main_df, config_path)
    orig_csv_path = "test_data/step4_concat_data_ID_110_main_HK_log_2026-03-12_1540.csv"
    output_hex_path = "scratch/compaire.csv"
    comparison_df = compare_with_original(recovered_hex, orig_csv_path)
    comparison_df.to_csv(output_hex_path, index=False)

    print(comparison_df[["match"]])
    print("match rate:", comparison_df["match"].mean())

    bad = comparison_df.index[~comparison_df["match"]].tolist()
    if bad:
        i = bad[0]
        print("first mismatch row:", i)
        print("orig     :", comparison_df.loc[i, "orig_hex"])
        print("recovered:", comparison_df.loc[i, "recovered_hex"])


if __name__ == "__main__":
    main()
# import pandas as pd
# import json


# config_path = "scratch/new_fmt_conbined.json"
# # index_tuple = build_column_schema_from_config(config_path)

# data_path = 'scratch/value_converted.csv'

# main_df = pd.read_csv(data_path,header=[0,1])
# print(main_df)


# import json
# import pandas as pd
# from collections import OrderedDict


# def load_pack_units(schema_path: str) -> list[dict]:
#     """
#     同じ group・同じ start_bit の field を 1 unit にまとめる。
#     unit ごとに total_bits を byte 境界まで pad して持つ。
#     """
#     with open(schema_path, "r", encoding="utf-8") as f:
#         schema = json.load(f)

#     units = []

#     for group_name, group_info in schema.items():
#         byte_order = group_info["byte_order"]

#         grouped = OrderedDict()

#         for field in group_info["fields"]:
#             anchor_start_bit = field.get("start_bit")
#             if anchor_start_bit is None:
#                 anchor_start_bit = (field["start_byte"] - 1) * 8

#             shift_bit = field.get("shift_bit", 0)

#             key = (group_name, anchor_start_bit)

#             if key not in grouped:
#                 grouped[key] = {
#                     "group": group_name,
#                     "start_bit": anchor_start_bit,
#                     "byte_order": byte_order,
#                     "fields": []
#                 }

#             grouped[key]["fields"].append({
#                 "name": field["name"],
#                 "bit_width": field["bit_width"],
#                 "shift_bit": shift_bit,
#             })

#         for unit in grouped.values():
#             used_bits = max(f["shift_bit"] + f["bit_width"] for f in unit["fields"])
#             pad_bits = (8 - (used_bits % 8)) % 8
#             total_bits = used_bits + pad_bits

#             unit["used_bits"] = used_bits
#             unit["pad_bits"] = pad_bits
#             unit["total_bits"] = total_bits

#             units.append(unit)

#     units.sort(key=lambda u: (u["start_bit"], u["group"]))
#     return units


# def pack_unit(row: pd.Series, unit: dict) -> bytes:
#     """
#     1 unit 内の複数 field を shift_bit で配置し、
#     unit 全体を byte 境界まで pad して bytes 化する。
#     """
#     total_bits = unit["total_bits"]
#     byte_order = unit["byte_order"]
#     endian_str = "big" if byte_order == ">" else "little"

#     acc = 0
#     used_mask = 0

#     for field in unit["fields"]:
#         name = field["name"]
#         bit_width = field["bit_width"]
#         shift_bit = field["shift_bit"]

#         value = int(row[(unit["group"], name)])

#         if value < 0:
#             raise ValueError(f"negative value: {(unit['group'], name)}={value}")

#         if value >= (1 << bit_width):
#             raise ValueError(
#                 f"value too large: {(unit['group'], name)}={value}, bit_width={bit_width}"
#             )

#         if byte_order == ">":
#             local_shift = total_bits - (shift_bit + bit_width)
#         else:
#             local_shift = shift_bit

#         field_mask = ((1 << bit_width) - 1) << local_shift

#         if used_mask & field_mask:
#             raise ValueError(
#                 f"bit overlap detected in unit start_bit={unit['start_bit']} "
#                 f"field={(unit['group'], name)}"
#             )

#         acc |= value << local_shift
#         used_mask |= field_mask

#     return acc.to_bytes(total_bits // 8, byteorder=endian_str)


# def row_to_bytes_grouped(row: pd.Series, units: list[dict]) -> bytes:
#     parts = [pack_unit(row, unit) for unit in units]
#     return b"".join(parts)


# def df_to_hex_series_grouped(df: pd.DataFrame, schema_path: str) -> pd.Series:
#     units = load_pack_units(schema_path)
#     return df.apply(lambda row: row_to_bytes_grouped(row, units).hex(), axis=1)

# # 事前に main_df は schema 順へ並べておくのが安全
# # main_df = main_df.reindex(columns=schema_columns)

# hex_series = df_to_hex_series_grouped(main_df, config_path)

# main_df[("recovered", "hex")] = hex_series
# hex_series.to_csv("scratch/recovered_grouped.csv", index=False)

# # def load_group_fields(schema_path: str):
# #     """グループ別: fieldsリスト + 累積bit範囲 + endian"""
# #     with open(schema_path, "r", encoding="utf-8") as f:
# #         schema = json.load(f)
    
# #     groups = []
# #     total_bits = 0
# #     for group_name, group_info in schema.items():
# #         print(group_info)
# #         endian = group_info["byte_order"]
# #         group_bits = sum(f["bit_width"] for f in group_info["fields"])
# #         groups.append({
# #             "name": group_name,
# #             "endian": endian,
# #             "fields": group_info["fields"],  # name, bit_width
# #             "width_bits": group_bits
# #         })
# #         total_bits += group_bits
# #     return groups

# # def field_to_bytes(field: dict, value: int) -> bytes:
# #     """1field → bit_width/endian bytes (端数pad対応)"""
# #     bit_width = field["bit_width"]
# #     endian_str = "big" if field["byte_order"] == ">" else "little"
# #     start_bit = field["start_bit"]
# #     shift_bit = field["shift_bit"]
# #     n_bytes = (bit_width + 7) // 8  # ceil division
    
# #     # valueをn_bytesに展開
# #     bytes_field = value.to_bytes(n_bytes, byteorder=endian_str)
    
# #     # bit_width %8 !=0: 高位bit 0埋め (MSB align)
# #     extra_bits = n_bytes * 8 - bit_width
# #     if extra_bits > 0:
# #         bytes_field = bytes_field[extra_bits // 8:] + b'\x00' * (extra_bits // 8)
    
# #     return bytes_field

# # def row_to_hex_fieldwise(data: pd.Series, groups: list[dict]) -> bytes:
# #     """1row → 全field bytes結合 (物理順)"""
# #     all_bytes = []
# #     for group in groups:
# #         for field_def in group["fields"]:
# #             field = {**field_def, "byte_order": group["endian"]}  # merge
# #             value = int(data[(group["name"], field["name"])])
# #             field_bytes = field_to_bytes(field, value)
# #             all_bytes.append(field_bytes)
# #     return b''.join(all_bytes).hex()

# # # 使用例 (あなたのコード完成形)
# # groups = load_group_fields(config_path)  # 前回の関数
# # data = main_df.apply(row_to_hex_fieldwise, axis=1,args=(groups,))
# # print(data)
# # print(f"Recovered: {data.hex()}")
# # print(f"Orig chunk: {chunks.iloc[1].hex()}")
# # print(f"Match: {recovered_bytes == chunks.iloc[1]}")

# # def group_row_to_bytes(row: pd.Series, group: dict) -> bytes:
# #     """1グループのrow → endian bytes"""
# #     bits = []
# #     byteorder = "big" if group["endian"] == ">" else "little"
# #     for field in group["fields"]:
# #         name = field["name"]
# #         bit_width = field["bit_width"]
# #         value = int(row[(group["name"], name)])
# #         bits.append(format(value, f"0{bit_width}b"))
# #     bitstring = "".join(bits)
# #     return int(bitstring, 2).to_bytes(group["width_bits"] // 8, byteorder=byteorder)

# # def df_rows_to_bytes_grouped(df: pd.DataFrame, schema_path: str) -> pd.Series:
# #     """グループendian考慮復元 → hex Series"""
# #     groups = load_group_fields(schema_path)
# #     # print(groups)
# #     data = df.iloc[1]
# #     print(data)
# #     for group in groups:
# #         for field in group["fields"]:
# #             name = field["name"]
# #             bit_width = field["bit_width"]
# #             endian = field["endian"]
# #             value = data[(group["name"], name)]
# #             hex_ = value.hex(bitwidth, endian)
# #             print(value)
# #     # def row_to_combined_bytes(row):
# #     #     group_bytes_list = [group_row_to_bytes(row, g) for g in groups]
# #     #     return bytes().join(group_bytes_list).hex()
# #     # return df.apply(row_to_combined_bytes, axis=1)

# # bytes_series = df_rows_to_bytes_grouped(main_df, config_path)
