import json
import re


def struct_fmt_to_bit_schema(fmt: str, column_names: list[str], group_name=""):
    """struct format を bit field schema に変換（byte境界項目のみ）"""
    
    # format を展開
    endian= fmt[0]
    tokens = re.findall(r"(\d*)([BHIx])", fmt)
    fields = []
    
    byte_pos = 1
    col_idx = 0
    
    for count_str, code in tokens:
        count = int(count_str) if count_str else 1
        
        if code == "x":
            byte_pos += count
            continue
            
        bit_width = {"B": 8, "H": 16, "I":32}[code]
        
        for i in range(count):
            if col_idx >= len(column_names):
                break
                
            fields.append({
                "name": column_names[col_idx],
                "start_byte": byte_pos,
                "shift_bit": 0,
                "bit_width": bit_width,
                "scale": 1,
                "status_strings": None
            })
            
            col_idx += 1
            byte_pos += 1 if code == "B" else 2
    
    schema = {
        "group": group_name,
        "byte_order": endian,
        "fields": fields
    }
    
    return schema


with open("scratch/decode_config.json", "r", encoding="utf-8") as f:
    config = json.load(f)
# print(type(config))
# data = []
db_schemas = {}
for group_name, group_spec in config["groups"].items():

    fmt = group_spec["format"] 
    columns = group_spec["columns"]
    schema = struct_fmt_to_bit_schema(fmt, columns, group_name)
    db_schemas[group_name] = schema
# print(db_schemas)
output_path = 'scratch/new_fmt.json'

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(db_schemas,f)
