import json
from collections import OrderedDict
with open('config/s_packet_structure.json', 'r') as f:
    BIT_MAP_JSON = json.load(f)

length = len(BIT_MAP_JSON)+2
new_bit_map_json = []

def add_numeric(time_str,num):
    # コロンで分割して整数に変換
    left, right = map(int, time_str.split(':'))
    left += num
    right += num
    new_time_str = f"{left}:{right}"
    return new_time_str
# j = 0
for i, entry in enumerate(BIT_MAP_JSON):
    bits = (entry["Bit(s)"])
    if i > 0:
        bits = add_numeric(bits,8*8+10*8)
#     new_bit_map_json.append(entry)
    new_bit_map_json.append({"Bit(s)": bits, "Name": entry["Name"], "dtype": entry["dtype"]},)

    if i == 0:
        new_bit_map_json.append({"Bit(s)":"24:87", "Name": "Datetime", "dtype": "datetime"},)
        new_bit_map_json.append({"Bit(s)":"88:167", "Name": "Demodulator symbol", "dtype": "byte"})
#     # entry = BIT_MAP_JSON[j]
print(new_bit_map_json)
with open('config/s_packet_structure_modified.json', 'w') as f:
    json.dump(new_bit_map_json,f,ensure_ascii=False)