
import struct
import pandas as pd


FMT = ">7B8H2B164x"
SIZE = struct.calcsize(FMT)

COLUMNS = [
    "timestamp_reset", "year", "month", "day", "hour", "minute", "second",
    "voltage_raw_power", "current_3v3_1", "current_3v3_2", "current_5v0",
    "current_unreg1", "current_unreg2", "current_unreg3", "current_12v",
    "power_line_status", "status_main_pic"
]

def unpack_data_chunk(decodable_chunk: bytes) -> pd.DataFrame:
    rows = []
    values = struct.unpack(">7B8H2B164x", decodable_chunk)
        
    return values

filename ="test_data/step4_concat_data_ID_110_main_HK_log_2026-03-12_1540.csv"
df = pd.read_csv(filename)


decodable_data_group = df.Data
# print(decodable_data_group)

rows = []
# for offset in range(0, len(data) - len(data) % SIZE, SIZE):
#     values = struct.unpack_from(FMT, data, offset)
for decodable_chunk in decodable_data_group:
    decodable_chunk = bytes.fromhex(decodable_chunk)
    decodable_chunk = decodable_chunk[:-2] # cut CRC
    values = unpack_data_chunk(decodable_chunk)
    rows.append(dict(zip(COLUMNS, values)))

main_df =  pd.DataFrame(rows, columns=COLUMNS)

print(main_df)