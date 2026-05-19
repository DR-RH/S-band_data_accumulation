import json
from collections import OrderedDict
with open('config/s_packet_structure_byte.json', 'r') as f:
    BIT_MAP_JSON = json.load(f)

length = len(BIT_MAP_JSON)+2
new_byte_map_json = []

def add_numeric(time_str,num):
    # コロンで分割して整数に変換
    left, right = map(int, time_str.split(':'))
    left += num
    right += num
    new_time_str = f"{left}:{right}"
    return new_time_str
# j = 0
for i, entry in enumerate(BIT_MAP_JSON):
    bytes = (entry["Byte(s)"])
    if i > 0:
        bytes = add_numeric(bytes,8+10)
#     new_bit_map_json.append(entry)
    new_byte_map_json.append({"Byte(s)": bytes, "Name": entry["Name"], "dtype": entry["dtype"]},)

    if i == 0:
        new_byte_map_json.append({"Byte(s)":"3:10", "Name": "Datetime", "dtype": "datetime"},)
        new_byte_map_json.append({"Byte(s)":"11:20", "Name": "Demodulator symbol", "dtype": "byte"})
#     # entry = BIT_MAP_JSON[j]
print(new_byte_map_json)
with open('config/s_packet_structure_byte_modified.json', 'w') as f:
    json.dump(new_byte_map_json,f,ensure_ascii=False)