#!/usr/bin/python3

import sys
import struct
import datetime
import pytz
import os
import pandas as pd

telemetry_size = 7

def command_list(command):
    switcher = {
        0xABAA: "command_pcib_telemetry",
        0xABAA: "command_pcib_telemetry",
        0xAD90: "command_adcs_telemetry",
        0xADDA: "command_adcs_gps_time",
        0xB070: "command_time_change_ack",
        0xB0A0: "command_reset_telemetry",
        0xB0A2: "command_reset_warning",
        0xC000: "command_print_memory_address",
        0xC001: "command_set_clock",
        0xC003: "command_set_obc_variable",
        0xC008: "command_xmodem_receive_sector",
        0xC009: "command_xmodem_send_sector",
        0xC00A: "command_copy_memory_page",
        0xC00B: "command_copy_memory_sector",
        0xC00C: "command_erase_memory_page",
        0xC00D: "command_erase_memory_sector",
        0xC025: "command_boot_cmd_clear_nth",
        0xC026: "command_boot_cmd_clear_all",
        0xC028: "command_boot_cmd_add",
        0xC042: "command_reinitialize_memory_for_uplink",
        0xC043: "command_sband_downlink_notification",
        0xC050: "command_com_automatic_packet_request",
        0xC051: "command_copy_telemetry_to_com_shared_fm",
        0xC055: "command_save_state",
        0xC060: "command_obc_kill_on",
        0xC061: "command_obc_kill_off",
        0xC06C: "command_send_data_to_eps",
        0xC06D: "command_eps_set_heater_ref",
        0xC090: "command_request_reset",
        0xC091: "command_request_eps",
        0xC092: "command_request_pcib",
        0xC093: "command_request_adcs",
        0xC0A2: "command_reset_preparation_routine",
        0xC0A6: "command_adcs_default_mode",
        0xC0AC: "command_adcs_long_command",
        0xC0AD: "command_adcs_mode",
        0xC0AE: "command_ocp_state",
        0xC0AF: "command_adcs_raw",
        0xC0C5: "command_clear_state",
        0xC0CB: "command_ccb_raw",
        0xC0CC: "command_raw_relay",
        0xC0CD: "command_change_cw_mode_flags",
        0xC0CE: "command_ccb_time_synchronization",
        0xC0D0: "command_xmodem_send",
        0xC0D1: "command_xmodem_receive",
        0xC0DA: "command_deploy_dsap",
        0xC0DB: "command_debug",
        0xC0DD: "command_dump_memory",
        0xC0DE: "command_process_multipart_uplink",
        0xC0DF: "command_get_tris",
        0xC0EA: "command_copy_mission_to_com",
        0xC0F5: "command_send_data_to_reset",
        0xC0F6: "command_schedule_anything",
        0xC0F7: "command_adcs_schedule_mode",
        0xC0F8: "command_save_telemetry",
        0xC0F9: "command_clear_all_schedule_commands",
        0xC0FA: "command_trx_message",
        0xC0FB: "command_print_flags",
        0xC0FE: "command_boot_flag_set",
        0xC0FF: "command_reset_log",
        0xCBAE: "command_ccb_operation_ended",
        0xE033: "command_eps_telemetry",
    }
    return switcher.get(command, "command_unknown")


# Get input file path from command line argument
# input_file = sys.argv[1]

# # Generate output file path
# if input_file.lower().endswith('.hex'):
#     output_file = input_file[:-4] + '.csv'
# else:
#     output_file = input_file + '.csv'


#
def _break_bin(
    data: bytes,
    list_of_p_n: list[tuple[int, int]],
    block: int = 144
    ) -> bytes:

    data = bytearray(data)

    for position, number_loss in list_of_p_n:
        start = position * block
        end = start + number_loss * block

        if end > len(data):
            raise ValueError("packet loss range exceeds data length")

        data[start:end] = b"\xFF" * (block * number_loss)
    return bytes(data)

def _fix_broken_bin(
    data: bytes,
    posisions,
    decode_byte_unit: int = 7,
    block: int = 144,
    ) -> bytes:
    
    cut_off_start = 0
    decodable_data = b''
    for position in posisions:
        loss_start = block * position
        cut_off_end = (loss_start // decode_byte_unit) * decode_byte_unit
        decodable_data += data[cut_off_start:cut_off_end]
        # align to decode unit
        cut_off_start = (((position + 1)*block - 1) // decode_byte_unit + 1) * decode_byte_unit 
    decodable_data += data[cut_off_start:]

    # print(cut_off_end)
    # print(cut_off_start)

    return decodable_data

def decode(bin_file,):

    rows = []
    missing_path = bin_file.with_name(bin_file.stem + "_missing.csv")
    with open(bin_file, "rb") as f:
        bin_data = f.read()
    with open(missing_path,"r") as f:
        line = f.read()
        data_list = line.split(',')
        missing = map(int,data_list)

    decode_byte_unit = 7
    # list_of_p_n = ([1,2],[4,2])
    # bin_data = _break_bin(bin_data, list_of_p_n)
    bin_data = _fix_broken_bin(bin_data, missing, decode_byte_unit, )

    offset = 0
    data_len = len(bin_data)

    while offset + telemetry_size <= data_len:

        chunk = bin_data[offset:offset + telemetry_size]
        offset += telemetry_size

        record = _decode_chunk(chunk)

        if record is None:
            continue

        rows.append(record)

    df = pd.DataFrame(
        rows,
        columns=["timestamp", "source", "command", "command_name", "return"]
    )

    return df


def _decode_chunk(chunk):
    # print(line.hex())
    (timestamp, source, command, error_value) = struct.unpack("i3B", chunk)
    if timestamp != -1 or source != 0xFF or command != 0xFF or error_value != 0xFF:
        timestamp = datetime.datetime.fromtimestamp(timestamp,tz=pytz.UTC).strftime("%Y/%m/%d %H:%M:%S")
        full_command = (source << 8) | command
        command_name = command_list(full_command)
        # print(chunk)
        # print( f"{timestamp},'%02X,'%02X,{command_name},'%02X\n" % (source, command, error_value))
        record = [timestamp, command_name, format(source, "02X"), format(command,"02X"), format(error_value,"02X")]

        return record
    else:
        return "None"
        # write data to file
        # output_lines[j] = (f"{timestamp},'%02X,'%02X,{command_name},'%02X\n" % (source, command, error_value))

# def decode(bin_file):
#     # with open(output_file, 'w') as output:
#     #     # Write CSV header
#     # bin_file
#     with open(bin_file, "rb") as f:
#         # skip incomplete lines
#         line = f.read(telemetry_size)
#         first_byte = ((line.find(b'\xC0.{6}\xC0') + 1) % telemetry_size)
#         f.seek(first_byte)
#         line = f.read(telemetry_size)
#         output_lines = [""]*(len(line)+1)
#         output_lines.append("timestamp, source, command, command_name, error_value\n")
#         j = 1
#         while(len(line) == telemetry_size):
#             # process line here
#             print(line.hex())
#             (timestamp, source, command, error_value) = struct.unpack("i3B", line)
#             if timestamp != -1 or source != 0xFF or command != 0xFF or error_value != 0xFF:
#                 timestamp = datetime.datetime.fromtimestamp(timestamp,tz=pytz.UTC).strftime("%Y/%m/%d %H:%M:%S")
#                 full_command = (source << 8) | command
#                 command_name = command_list(full_command)
#                 # write data to file
#                 output_lines[j] = (f"{timestamp},'%02X,'%02X,{command_name},'%02X\n" % (source, command, error_value))
#                 j +=1
#     return output_lines
        # get next line