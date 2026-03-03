import struct

import pandas as pd
from decoder import adcs_HK_list
from datetime import datetime 
def get_fmt_size(fmt):
    # struct.calcsize returns the number of bytes from the format string
    if fmt == 'B' or fmt == 'b':
        return 1
    elif fmt == 'H' or fmt == 'h':
        return 2
    elif fmt == 'I' or fmt == 'i':
        return 4
    elif fmt == 'f':
        return 4
    elif fmt == 'T':
        return 4
    elif fmt == 'd':
        return 8
    
def convert_strint2bytes(s):
    """
    Convert a string to a byte sequence.
    :param s: String in hexadecimal representation (e.g., '1A2B')
    :return: Byte sequence
    """
    # Remove newline characters
    s = s.strip()
    if len(s) % 2 != 0:
        raise ValueError("String length must be even.")
    return bytes.fromhex(s)


def mask_lower_bits(value: int, bit_str: str) -> int:
    num_bits = int(bit_str)
    mask = (1 << num_bits) - 1  # 例えば 2ビットなら (1<<2)-1 = 0b11
    return value & mask

def extract_and_decode(
    data,
    params_list,
    endian='big',
    ):
    """
    Analyze multiple items (name, sbyte, num_bytes, shift, fmt) together.

    :param data: Binary data (bytes type)
    :param params_list: [{'name':str, 'sbyte':int, 'num_bytes':int, 'shift':int, 'fmt':str}]
    :param endian: Endian ('little' or 'big')
    :param plot: Whether to draw a graph
    :return: Dictionary of decoded values for each item
    """
    
    results = {}
    for param in params_list:
        name = param[0]
        sbyte = param[1] + 6  # offset by 1 for 1-based index
        shift = param[2]
        fmt_raw = param[3]
        conversion_factor = param[4]
        if fmt_raw == '1' or fmt_raw == '2' or fmt_raw == '3' or fmt_raw == '4' or fmt_raw == '5':
            fmt = 'B'
        else:
            fmt = fmt_raw
        # print(fmt)
        num_bytes = get_fmt_size(fmt)
        endian_prefix = '<' if endian == 'little' else '>'
        # print(endian_prefix, fmt)
        format_str = endian_prefix + fmt
        
        if sbyte + num_bytes > len(data):
            print(f"{name}: Out of range access: sbyte={sbyte}, num_bytes={num_bytes}, data_length={len(data)}")
            results[name] = None
            continue
        
        segment = data[sbyte:sbyte+num_bytes+1]
        
        int_value = int.from_bytes(segment, byteorder='big',signed=False)
        if shift >= 0:
            if fmt_raw == '1' or fmt_raw == '2'or fmt_raw == '3' or fmt_raw == '4' or fmt_raw == '5':
                int_value >>= 8-int(fmt_raw) 
            int_value >>= 8 - shift
            int_value &= (1 << (num_bytes*8))-1
            
        try:
            if fmt_raw == "T":
                #Little EndianでUNIX時間を取得
                unix_time = struct.unpack('<I', int_value.to_bytes(num_bytes, byteorder='big',signed=False))[0]
                
                dt_object = datetime.fromtimestamp(unix_time)
                results[name] = dt_object.strftime('%Y-%m-%d %H:%M:%S')
            else:
                value = struct.unpack(format_str, int_value.to_bytes(num_bytes, byteorder='big',signed=False))[0]
                if fmt_raw == '1' or fmt_raw == '2'or fmt_raw == '3':
                    value = mask_lower_bits(value,fmt_raw)
                results[name] = value*conversion_factor
        except Exception as e:
            print(f"{name}: Decode error: {e}")
            results[name] = None


    return results

def decode(bin_path):

    # # timestamp = 'before_copy_again_received_20251113_185025'
    # sample_mode = "high"
    # sample_mode_dict = {"high":"3392","normal":"9608"}
    with open(bin_path, 'rb') as f:
        data = f.read()
    # print(data)
    decoded_list = []
    packet_nubmer = len(data)//1473
    for i in range(packet_nubmer):
        single_packet = data[i*1473: (i+1)*1473]
        # print(f"Processing line {i}")
        # print(f"{single_packet}")
        # decoded_data = convert_strint2bytes(single_packet)

        # print(data)
        decoded_data = extract_and_decode(
            single_packet, adcs_HK_list.adcs_HK
        )
        # print(decoded_data)
        decoded_list.append(decoded_data)
    return decoded_list
    # df = pd.DataFrame(decoded_list)
    # os.makedirs(f'final_products/{timestamp}',exist_ok=True)
    # output_file = f'final_products/{timestamp}/{timestamp}_{sample_mode}.csv'
    # df.to_csv(output_file)
    # Write each line as csv

    # writer.writerow(convert.values())