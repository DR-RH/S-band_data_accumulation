import struct
from datetime import datetime, timezone
import re 
def datetime_to_hex(dt):
    # --- 日時をミリ秒timestampに ---
    timestamp_datetime = int(dt.timestamp() * 1000*1000)
    binary = timestamp_datetime.to_bytes(8, "big")
    return binary

def hex_to_datetime(binary):
    timestamp = int.from_bytes(binary, "big")
    if not (-62135596800000000 <= timestamp <= 2534023007999999700):
        timestamp = 253402300799999970
    dt = datetime.fromtimestamp(timestamp / 1000/1000, tz=timezone.utc)
    return dt


def add_timestamp(lines):
    pattern = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+')

    # erase unmatched format
    filtered_lines = [line for line in lines if pattern.match(line)]
    # print(filtered_lines)
    timestamp_added_lines = []
    for line in filtered_lines:
        if "FAF320" not in line:
            timestamp_added_lines.append(line)
        else: 
            # " - " で区切り、タイムスタンプ部分を取得
            # print(line.split("-"))
            timestamp_str = line.split(" - ", 1)[0]
            timestamp_dt = datetime.fromisoformat(timestamp_str).replace(tzinfo=timezone.utc)
            ts_binary = datetime_to_hex(timestamp_dt)

            ts_hex = ts_binary.hex().upper()
            result = re.sub(r'(FAF320)', ts_hex + r'\1', line)
            # print(result)
            timestamp_added_lines.append(result)
    return timestamp_added_lines

if __name__ == '__main__':
    # dt = datetime.fromisoformat("2025-10-21T14:38:29.268815").replace(tzinfo=timezone.utc)
    # binary = datetime_to_binary(dt)
    # timestamp_datetime_recovered = binary_datetime(binary)
    # print(binary)
    # print(timestamp_datetime_recovered)

    bin = b'\xff\xff\xff\xff\xff\xff`\xa9'
    text = bin.hex()
    print(text)
    dt = hex_to_datetime(bin)
    print(dt)
    # path = '/Users/rh/Desktop/vertecs/experiment/S-band_data/received_20251021_135448.txt'
    # with open(path) as f:
    #     lines = f.readlines()
    # timestamp_added_lines = add_timestamp(lines)
    # print(timestamp_added_lines)
