import json
with open("scratch/adcs_main_HK_list.json", "r", encoding="utf-8") as f:
    adcs_config= json.load(f)
# print(adcs_config)
offset = 96
for i, item in enumerate(adcs_config["adcs pic"]["fields"]):
    
    adcs_config["adcs pic"]["fields"][i]["start_byte"] = item["start_byte"] + offset

    # 上書き保存
with open("scratch/adcs_main_HK_list_offset.json", "w", encoding="utf-8") as f:
    json.dump(adcs_config, f, ensure_ascii=False, indent=2)
