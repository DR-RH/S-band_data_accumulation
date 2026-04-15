#!/usr/bin/python3

# import sys
import struct
import datetime
import pytz
import glob
import os
from bisect import bisect_left
# from adcs_decoding import extract_and_decode as adcs_extract_and_decode
from decoder.adcs_HK_list_of_main import adcs_HK_list
from decoder.decoder_adcs_of_main import extract_and_decode
# import tkinter as tk
# from tkinter import filedialog, messagebox

# -------- temperature sensor decoding ---------
MAIN_TELEMETLY_SIZE = 191

def bin_to_resistance(binary):
    """
    Convert binary ADC value to resistance.
    """
    if binary == 4095:
        binary = 4094  # Prevent division by zero
    return binary * 10000.0 / (4095.0 - binary)

LOOKUP_TABLE = [
    (28.3, 250), (28.7, 249), (29.1, 248), (29.6, 247), (30.1, 246), (30.5, 245), (31, 244), (31.5, 243), (32, 242), (32.5, 241),
    (33, 240), (33.6, 239), (34.1, 238), (34.7, 237), (35.2, 236), (35.8, 235), (36.4, 234), (37, 233), (37.6, 232), (38.2, 231),
    (38.9, 230), (39.5, 229), (40.2, 228), (40.9, 227), (41.6, 226), (42.3, 225), (43, 224), (43.7, 223), (44.5, 222), (45.3, 221),
    (46, 220), (46.8, 219), (47.7, 218), (48.5, 217), (49.4, 216), (50.2, 215), (51.1, 214), (52, 213), (53, 212), (53.9, 211),
    (54.9, 210), (55.9, 209), (56.9, 208), (57.9, 207), (59, 206), (60.1, 205), (61.2, 204), (62.3, 203), (63.5, 202), (64.7, 201),
    (65.9, 200), (67.1, 199), (68.4, 198), (69.7, 197), (71, 196), (72.4, 195), (73.8, 194), (75.2, 193), (76.7, 192), (78.2, 191),
    (79.7, 190), (81.3, 189), (82.9, 188), (84.5, 187), (86.2, 186), (87.9, 185), (89.7, 184), (91.5, 183), (93.3, 182), (95.2, 181),
    (97.2, 180), (99.2, 179), (101.2, 178), (103.3, 177), (105.5, 176), (107.7, 175), (109.9, 174), (112.2, 173), (114.6, 172), (117, 171),
    (119.5, 170), (122.1, 169), (124.7, 168), (127.4, 167), (130.2, 166), (133, 165), (135.9, 164), (138.9, 163), (142, 162), (145.1, 161),
    (148.3, 160), (151.7, 159), (155.1, 158), (158.6, 157), (162.2, 156), (165.8, 155), (169.6, 154), (173.5, 153), (177.5, 152), (181.7, 151),
    (185.9, 150), (190.2, 149), (194.7, 148), (199.3, 147), (204, 146), (208.9, 145), (213.9, 144), (219, 143), (224.3, 142), (229.7, 141),
    (235.3, 140), (241.1, 139), (247, 138), (253.1, 137), (259.4, 136), (265.9, 135), (272.5, 134), (279.4, 133), (286.5, 132), (293.8, 131),
    (301.3, 130), (309, 129), (316.9, 128), (325.2, 127), (333.6, 126), (342.3, 125), (351.3, 124), (360.6, 123), (370.2, 122), (380, 121),
    (390.2, 120), (400.7, 119), (411.5, 118), (422.7, 117), (434.3, 116), (446.2, 115), (458.5, 114), (471.2, 113), (484.3, 112), (497.9, 111),
    (511.9, 110), (526.3, 109), (541.3, 108), (556.7, 107), (572.7, 106), (589.2, 105), (606.2, 104), (623.9, 103), (642.1, 102), (661, 101),
    (680.6, 100), (700.8, 99), (721.7, 98), (743.4, 97), (765.8, 96), (789, 95), (813, 94), (837.9, 93), (863.7, 92), (890.4, 91),
    (918.1, 90), (946.8, 89), (976.6, 88), (1007, 87), (1039, 86), (1073, 85), (1107, 84), (1143, 83), (1180, 82), (1218, 81),
    (1258, 80), (1300, 79), (1343, 78), (1387, 77), (1434, 76), (1482, 75), (1532, 74), (1584, 73), (1639, 72), (1695, 71),
    (1753, 70), (1814, 69), (1878, 68), (1944, 67), (2012, 66), (2084, 65), (2158, 64), (2236, 63), (2317, 62), (2401, 61),
    (2488, 60), (2580, 59), (2675, 58), (2774, 57), (2878, 56), (2986, 55), (3099, 54), (3217, 53), (3339, 52), (3468, 51),
    (3602, 50), (3742, 49), (3888, 48), (4041, 47), (4200, 46), (4367, 45), (4542, 44), (4724, 43), (4915, 42), (5115, 41),
    (5325, 40), (5544, 39), (5773, 38), (6014, 37), (6266, 36), (6530, 35), (6806, 34), (7097, 33), (7401, 32), (7720, 31),
    (8055, 30), (8407, 29), (8776, 28), (9164, 27), (9572, 26), (10000, 25), (10450, 24), (10920, 23), (11420, 22), (11940, 21),
    (12490, 20), (13070, 19), (13680, 18), (14330, 17), (15000, 16), (15720, 15), (16470, 14), (17260, 13), (18100, 12), (18980, 11),
    (19910, 10), (20900, 9), (21930, 8), (23030, 7), (24190, 6), (25410, 5), (26710, 4), (28080, 3), (29530, 2), (31060, 1),
    (32680, 0), (34400, -1), (36230, -2), (38160, -3), (40200, -4), (42370, -5), (44680, -6), (47120, -7), (49720, -8), (52470, -9),
    (55400, -10), (58510, -11), (61820, -12), (65330, -13), (69080, -14), (73060, -15), (77300, -16), (81820, -17), (86640, -18), (91770, -19),
    (97240, -20), (103100, -21), (109300, -22), (116000, -23), (123100, -24), (130700, -25), (138800, -26), (147500, -27), (156700, -28), (166700, -29),
    (177300, -30), (188700, -31), (200900, -32), (214000, -33), (228100, -34), (243200, -35), (259300, -36), (276700, -37), (295400, -38), (315500, -39),
    (337100, -40)
]

def resistance_to_temperature(resistance):
    """
    Convert resistance to temperature using lookup table and linear interpolation.
    """
    resistances = [r for r, _ in LOOKUP_TABLE]
    index = bisect_left(resistances, resistance)

    if index == 0:
        return LOOKUP_TABLE[0][1]
    elif index >= len(LOOKUP_TABLE):
        return LOOKUP_TABLE[-1][1]
    
    r1, t1 = LOOKUP_TABLE[index - 1]
    r2, t2 = LOOKUP_TABLE[index]
    
    return t1 + (t2 - t1) * (resistance - r1) / (r2 - r1)

def bin_to_temperature(binary):
    """
    Convert binary ADC value to temperature.
    """
    resistance = bin_to_resistance(binary)
    return resistance_to_temperature(resistance)

# -------- telemetry decoding ---------

def process_timestamp (unix_time, delta):
    if delta == 0xFF:
        return datetime.datetime.fromtimestamp(0, tz=pytz.UTC).strftime("%Y/%m/%d %H:%M:%S")
    else:
        return datetime.datetime.fromtimestamp(unix_time - delta, tz=pytz.UTC).strftime("%Y/%m/%d %H:%M:%S")

# def process_timestamp (unix_time, delta):

#     # if delta == 0xFF:
#     #     return datetime.datetime.fromtimestamp(0, tz=pytz.UTC).strftime("%Y/%m/%d %H:%M:%S")
#     # else:
#     return datetime.datetime.fromtimestamp(unix_time , tz=pytz.UTC).strftime("%Y/%m/%d %H:%M:%S") 


# def process_realtime_telemetry(line):
#     manually_fixed_start_time = None
#     sampling_time = 60
#     sampling_time_set = False
#     previous_timestamp = None
#     line_count = 1
#     correction_delta = 0
#     MAIN_[parameters, previous_timestamp, correction_delta, line_count] = process_telemetry_chunk(line, MAIN_TELEMETLY_SIZE, manually_fixed_start_time, sampling_time, sampling_time_set, previous_timestamp, line_count, correction_delta)
#     return parameters

def process_telemetry_chunk(chunk: bytes):

    # Initialize parameters dictionary
    parameters = {}
    chunk=chunk[0:MAIN_TELEMETLY_SIZE - 2]
    
    # Unpack reset pic data
    (timestamp_reset,
        year,
        month,
        day,
        hour,
        minute,
        second,
        voltage_raw_power,
        current_3v3_1,
        current_3v3_2,
        current_5v0,
        current_unreg1,
        current_unreg2,
        current_unreg3,
        current_12v,
        power_line_status,
        status_main_pic) = struct.unpack(">7B8H2B164x", chunk)

    # Unpack eps pic data
    (timestamp_fab,
        temp_minus_y,
        temp_plus_x,
        temp_minus_x,
        temp_dsap_plus_x,
        temp_dsap_minus_x,
        temp_plus_y,
        temp_bpb,
        no_data_1,
        no_data_2,
        no_data_3,
        voltage_BCR_1,
        voltage_BCR_2,
        voltage_BCR_3,
        current_minus_y,
        current_dsap_plus_x_3s3p,
        current_dsap_plus_x_3s2p,
        current_dsap_minus_x_3s2p,
        current_dsap_minus_x_3s3p,
        current_bm_plus_x,
        current_bm_minus_x,
        current_heater,
        voltage_raw,
        voltage_battery,
        current_raw,
        current_battery,
        temp_battery,
        heater_status,
        kill_switch_status,
        temp_heater_ref,
        voltage_heater_ref)= struct.unpack(">25x1B26H2B2H105x", chunk)

    # Unpack relay pic data
    (timestamp_pcib,
        temp_pl_1,
        temp_pl_2,
        temp_pl_3,
        payload_heater_status,
        payload_heater_sensor_config,
        status_tk_px,
        status_tk_mx) = struct.unpack("<84x1B3H4B94x", chunk)

    # Unpack adcs pic data
    timestamp_adcs = struct.unpack("<B", chunk[95:96])[0]
    adcs_data = b'\xAD\x90' + chunk[96:169] + b'\x00\x00'
    adcs_converted = extract_and_decode(adcs_data, adcs_HK_list)

    # Unpack com pic data
    (timestamp_com,
        operation_mode,
        bitrate_setting,
        test_mode,
        temp_stx,
        sband_rx_rssi,
        freq_err) = struct.unpack("<169x4B3H10x", chunk)

    # Unpack OBC data
    (number_scheduled_command_legacy,
        number_scheduled_command_flash,
        obc_mode,
        subsystem_communication,
        status_ocp,
        hours_after_reset,
        timestamp_obc) = struct.unpack("<179x6B1I", chunk)

    timestamp_in_memory = timestamp_obc


    # Reset HK
    timestamp_reset = process_timestamp(timestamp_obc, timestamp_reset)
    voltage_raw_power = voltage_raw_power * 3.3 * 3 / 4096

    # Current equations
    current_3v3_1 = (1606.822 * current_3v3_1 * 3.3 / 4096) - 37.39071
    current_3v3_2 = (1595.419618 * current_3v3_2 * 3.3 / 4096) - 0.252035868
    current_5v0 = (801.63197 * current_5v0 * 3.3 / 4096) - 3.163097
    current_unreg1 = (2407.441267 * current_unreg1 * 3.3 / 4096) - 6.117030991
    current_unreg2 = (2421.76513 * current_unreg2 * 3.3 / 4096) - 10.1421109
    current_unreg3 = (1973.436273 * current_unreg3 * 3.3 / 4096) - 9.717381297
    current_12v = (1567.774583 * current_12v * 3.3 / 4096) - 3.51635074

    # Power line status
    status_3v3_1 = (power_line_status & 0b10000000) >> 7
    status_3v3_2 = (power_line_status & 0b01000000) >> 6
    status_5v = (power_line_status & 0b00100000) >> 5
    status_unreg1 = (power_line_status & 0b00010000) >> 4
    status_unreg2 = (power_line_status & 0b00001000) >> 3
    status_unreg3 = (power_line_status & 0b00000100) >> 2
    status_12v = (power_line_status & 0b00000010) >> 1
    status_com_pic = (power_line_status & 0b00000001) >> 0
    status_main_pic = (status_main_pic & 0b00000001) >> 0

    timestamp_reset = process_timestamp(timestamp_obc, timestamp_reset)
    reset_date = ""
    voltage_raw_power = 0
    current_3v3_1 = 0
    current_3v3_2 = 0
    current_5v0 = 0
    current_unreg1 = 0
    current_unreg2 = 0
    current_unreg3 = 0
    current_12v = 0
    status_3v3_1 = 0
    status_3v3_2 = 0
    status_5v = 0
    status_unreg1 = 0
    status_unreg2 = 0
    status_unreg3 = 0
    status_12v = 0
    status_com_pic = 0
    status_main_pic = 0

    #EPS-1 HK
    timestamp_fab = process_timestamp(timestamp_obc, timestamp_fab)

    # Temperature equations
    temp_minus_y = ((temp_minus_y * 2500 / 4096) - 723.5) / -5.5
    temp_plus_x = ((temp_plus_x * 2500 / 4096) - 1030.9) / -5.5
    temp_minus_x = ((temp_minus_x * 2500 / 4096) - 1027.7 ) / -5.5
    temp_dsap_plus_x = ((temp_dsap_plus_x * 2500 / 4096) - 1014.8) / -5.5
    temp_dsap_minus_x = ((temp_dsap_minus_x * 2500 / 4096) - 1033.3) / -5.5
    temp_plus_y = ((temp_plus_y * 2500 / 4096) - 1013.77) / -5.5 
    temp_bpb = ((temp_bpb * 2500 / 4096) - 1022.4) / -5.5

    # Voltage equations
    voltage_BCR_1 = voltage_BCR_1 * 2.5 * 4 / 4096
    voltage_BCR_2 = voltage_BCR_2 * 2.5 * 4 / 4096
    voltage_BCR_3 = voltage_BCR_3 * 2.5 * 4 / 4096

    # Current equations
    current_minus_y = (0.327357 * (current_minus_y * 3.28 / 4096)) - 0.0314547
    current_dsap_plus_x_3s3p = (0.359681 * (current_dsap_plus_x_3s3p * 3.28 / 4096)) - 0.00566
    current_dsap_plus_x_3s2p = (0.317965 * (current_dsap_plus_x_3s2p * 3.28 / 4096)) - 0.03349
    current_dsap_minus_x_3s2p = (0.321226 * (current_dsap_minus_x_3s2p * 3.28 / 4096)) - 0.03196
    current_dsap_minus_x_3s3p = (0.311014 * (current_dsap_minus_x_3s3p * 3.28 / 4096)) - 0.0239
    current_bm_plus_x = (0.353379 * (current_bm_plus_x * 3.28 / 4096)) - 0.00472
    current_bm_minus_x = (0.305826 * (current_bm_minus_x * 3.28 / 4096)) - 0.01856
    current_heater = (4.020205 * (current_heater * 3.28 / 4096)) - 1.35776

    # Voltage raw equations
    voltage_raw = (voltage_raw * 3.3 / 4096) * 3
    voltage_battery = (voltage_battery * 3.3 / 4096) * 3

    # Current raw equations
    current_raw = (4.020205 * (current_raw * 3.28 / 4096)) - 1.35776
    current_battery = (3.863206 * (current_battery * 3.28 / 4096)) - 6.36292                                                

    # Temperature battery equation
    temp_battery = 75 - temp_battery * 3.256 / 4096 * 30

    # Heater status equation
    heater_status = heater_status
    battery_heater_enabled = (heater_status >> 4) & 0x1
    battery_heater_on_off = heater_status & 0x1

    # Kill switch status
    kill_switch_status_obc = kill_switch_status & 0x1
    kill_switch_status_eps = kill_switch_status >> 4

    # Temperature ref equation
    temp_heater_ref = 75 - (temp_heater_ref * 3.256 / 4096 * 30)

    # Voltage heater ref equation
    voltage_heater_ref = voltage_heater_ref * 3.3 * 3 / 4096
   
    #ADB HK
    timestamp_pcib = process_timestamp(timestamp_obc, timestamp_pcib)
    temp_pl_1 = bin_to_temperature(temp_pl_1)
    temp_pl_2 = bin_to_temperature(temp_pl_2)
    temp_pl_3 = bin_to_temperature(temp_pl_3)
    payload_heater_status = payload_heater_status
    payload_heater_enabled = payload_heater_status & 0x1
    payload_heater_on_off = (payload_heater_status >> 4) & 0x1
    payload_heater_sensor_config = payload_heater_sensor_config
    payload_heater_config = (payload_heater_sensor_config >> 4) & 0xF
    payload_sensor_config = payload_heater_sensor_config & 0xF
    """
    status_tk_px
    status_tk_mx
    """

    #ADCS HK:
    timestamp_adcs = process_timestamp(timestamp_obc, timestamp_adcs)
    v3v_status = adcs_converted["3V3 status"]
    v12v_low_power_status = adcs_converted["12V low power status"]
    v12v_high_power_status = adcs_converted["12V high power status"]
    v12vh_current = adcs_converted["12VH current"]
    v12vl_current = adcs_converted["12VL current"]
    boot_relay_status = adcs_converted["Boot Relay Status"]
    watchdog_reset_enable_status = adcs_converted["Watchdog Reset Enable Status"]
    watchdog_reset_event_status = adcs_converted["Watchdog Reset Event Status"]
    processor_reset_arm_status = adcs_converted["Processor reset arm status"]
    tai_seconds = adcs_converted["TAI_SECONDS"]
    refs_health_1pack_gps_valid = adcs_converted["GPS_VALID"]
    refs_health_1pack_refs_valid = adcs_converted["REFS_VALID"]
    refs_health_1pack_earth_penumbra_umbra = adcs_converted["EARTH_PENUMBRA_UMBRA"]
    mag_source_used = adcs_converted["MAG_SOURCE_USED"]
    att_status = adcs_converted["ATT_STATUS"]
    id_status = adcs_converted["ID_STATUS"]
    num_attitude_stars = adcs_converted["NUM_ATTITUDE_STARS"]
    inertia_index = adcs_converted["INERTIA_INDEX"]
    sun_point_state = adcs_converted["SUN_POINT_STATE"]
    cmd_accept_count = adcs_converted["CMD_ACCEPT_COUNT"]
    cmd_reject_count = adcs_converted["CMD_REJECT_COUNT"]
    position_wrt_eci_1 = adcs_converted["POSITION_WRT_ECI_1"]
    position_wrt_eci_2 = adcs_converted["POSITION_WRT_ECI_2"]
    position_wrt_eci_3 = adcs_converted["POSITION_WRT_ECI_3"]
    velocity_wrt_eci_1 = adcs_converted["VELOCITY_WRT_ECI_1"]
    velocity_wrt_eci_2 = adcs_converted["VELOCITY_WRT_ECI_2"]
    velocity_wrt_eci_3 = adcs_converted["VELOCITY_WRT_ECI_3"]
    mag_model_vector_body_1 = adcs_converted["MAG_MODEL_VECTOR_BODY_1"]
    mag_model_vector_body_2 = adcs_converted["MAG_MODEL_VECTOR_BODY_2"]
    mag_model_vector_body_3 = adcs_converted["MAG_MODEL_VECTOR_BODY_3"]
    mag_health_1pack_mag_power_state = adcs_converted["MAG_POWER_STATE"]
    mag_health_1pack_mag_vector_valid = adcs_converted["MAG_VECTOR_VALID"]
    mag_health_1pack_mag_vector_enabled = adcs_converted["MAG_VECTOR_ENABLED"]
    mag_health_1pack_mag_test_mode = adcs_converted["MAG_TEST_MODE"]
    mag_health_1pack_mag_sensor_used = adcs_converted["MAG_SENSOR_USED"]
    sun_vector_body_1 = adcs_converted["SUN_VECTOR_BODY_1"]
    sun_vector_body_2 = adcs_converted["SUN_VECTOR_BODY_2"]
    sun_vector_body_3 = adcs_converted["SUN_VECTOR_BODY_3"]
    css_health_1pack_css_power_state = adcs_converted["CSS_POWER_STATE"]
    css_health_1pack_meas_sun_valid = adcs_converted["MEAS_SUN_VALID"]
    css_health_1pack_sun_vector_enabled = adcs_converted["SUN_VECTOR_ENABLED"]
    css_health_1pack_css_test_mode = adcs_converted["CSS_TEST_MODE"]
    css_health_1pack_sun_sensor_used = adcs_converted["SUN_SENSOR_USED"]
    q_body_wrt_eci_1 = adcs_converted["Q_BODY_WRT_ECI_1"]
    q_body_wrt_eci_2 = adcs_converted["Q_BODY_WRT_ECI_2"]
    q_body_wrt_eci_3 = adcs_converted["Q_BODY_WRT_ECI_3"]
    q_body_wrt_eci_4 = adcs_converted["Q_BODY_WRT_ECI_4"]
    att_det_health_1pack_attitude_valid = adcs_converted["ATTITUDE_VALID"]
    att_det_health_1pack_meas_att_valid = adcs_converted["MEAS_ATT_VALID"]
    att_det_health_1pack_meas_rate_valid = adcs_converted["MEAS_RATE_VALID"]
    att_det_health_1pack_imu_data_valid = adcs_converted["IMU_DATA_VALID"]
    att_det_health_1pack_tracker_1data_valid = adcs_converted["TRACKER_1DATA_VALID"]
    body_rate_1 = adcs_converted["BODY_RATE_1"]
    body_rate_2 = adcs_converted["BODY_RATE_2"]
    body_rate_3 = adcs_converted["BODY_RATE_3"]
    operating_mode_1 = adcs_converted["OPERATING_MODE_1"]
    operating_mode_2 = adcs_converted["OPERATING_MODE_2"]
    operating_mode_3 = adcs_converted["OPERATING_MODE_3"]
    filtered_speed_rpm_1 = adcs_converted["FILTERED_SPEED_RPM_1"]
    filtered_speed_rpm_2 = adcs_converted["FILTERED_SPEED_RPM_2"]
    filtered_speed_rpm_3 = adcs_converted["FILTERED_SPEED_RPM_3"]
    motor_1_temp = adcs_converted["MOTOR_1TEMP"]
    motor_2_temp = adcs_converted["MOTOR_2TEMP"]
    motor_3_temp = adcs_converted["MOTOR_3TEMP"]
    att_cmd_health_1_packadcs_mode = adcs_converted["ADCS_MODE"]
    att_cmd_health_1_recommend_sun_point = adcs_converted["RECOMMEND_SUN_POINT"]
    att_cmd_health_1_sun_point_reason = adcs_converted["SUN_POINT_REASON"]
    att_ctrl_health_1pack_att_ctrl_active = adcs_converted["ATT_CTRL_ACTIVE"]
    att_ctrl_health_1pack_momentum_too_high = adcs_converted["MOMENTUM_TOO_HIGH"]
    att_ctrl_health_1pack_on_sun_flag = adcs_converted["ON_SUN_FLAG"]
    att_ctrl_health_1pack_sun_avoid_flag = adcs_converted["SUN_AVOID_FLAG"]
    att_ctrl_health_1pack_sun_source_failover = adcs_converted["SUN_SOURCE_FAILOVER"]
    sun_point_angle_error = adcs_converted["SUN_POINT_ANGLE_ERROR"]
    eigen_error = adcs_converted["EIGEN_ERROR"]
    
    
    #COM HK
    timestamp_com = process_timestamp(timestamp_obc, timestamp_com)

    A = operation_mode  & 0x0F   # ex.0x36 -> 0x6
    R = bitrate_setting & 0x0F   # ex.0x34 -> 0x4
    T = test_mode       & 0x0F   # ex.0x44 -> 0x4

        # ---- operation_mode ----
    d3 = (A >> 3) & 1
    d2 = (A >> 2) & 1
    power_tbl = {
        0b00: "RF OFF",  #RF_OFF
        0b01: "PWL",  #PWL 
        0b10: "PWL",  #PWL
        0b11: "PWH",  #PWH
    }
    operation_mode = power_tbl[(d3 << 1) | d2]

    # ---- bitrate_setting ----
    rate_tbl = {0: 10000, 1: 20000, 2: 32000, 3: 50000, 4: 64000}
    bitrate_setting = rate_tbl.get(R, 0) 

    # ---- test_mode ----
    test_mode_expected = 0x4  
    test_mode = "Normal" if (T & 0xF) == test_mode_expected else "Abnormal"

    #---- temp_stx (12bit) ----
    x = temp_stx & 0x0FFF
    temp_stx = 3.6438137698*((x * 3.3 * 1_000_000) / (7.5 * 1_000 * (2**12)) - 273.15) + 70.0851054839

    #---- sband_rx_rssi (12bit) ----
    y = sband_rx_rssi & 0x0FFF
    sband_rx_rssi = (y * 3.3) / (2**12)
    dbm_tbl = [-40, -45, -50, -55, -60, -65, -70, -75, -80, -85,
                -90, -95, -100, -105, -110, -115, -120, -125, -130, "-"]
    v_tbl   = [2.80, 2.77, 2.73, 2.65, 2.55, 2.41, 2.28, 2.13, 1.99, 1.85,
                1.71, 1.57, 1.44, 1.31, 1.19, 1.10, 1.04, 1.02, 1.01, 1.00]
    min_idx = 0
    min_diff = abs(sband_rx_rssi - v_tbl[0])
    for i in range(1, len(v_tbl)):
        diff = abs(sband_rx_rssi - v_tbl[i])
        if diff < min_diff:
            min_diff = diff
            min_idx = i
    sband_rx_rssi = dbm_tbl[min_idx]   

    #---- freq_err (12bit) ----
    z = freq_err & 0x0FFF
    freq_err = (z * 3.3) / (2**12)   # まず電圧[V]にする
    khz_tbl = [-80, -70, -60, -50, -40, -30, -20, -10, 0,
                +10, +20, +30, +40, +50, +60, +70, +80, +90,
            "UNLOCK"]
    vfreq_tbl = [0.02, 0.32, 0.64, 0.97, 1.29, 1.59, 1.88, 2.15, 2.40,
                2.63, 2.86, 3.08, 3.30, 3.53, 3.78, 4.08, 4.45, 4.94,
                2.52]
    min_idx = 0
    min_diff = abs(freq_err - vfreq_tbl[0])
    for i in range(1, len(vfreq_tbl)):
        diff = abs(freq_err - vfreq_tbl[i])
        if diff < min_diff:
            min_diff = diff
            min_idx = i
    freq_err = khz_tbl[min_idx]   

    #Main HK
    timestamp_obc = process_timestamp(timestamp_obc, 0)
    timestamp_in_memory = process_timestamp(timestamp_in_memory, 0)
    """
    number_shceduled_command_legacy
    number_shceduled_command_flash
    obc_mode
    subsystem_communication
    hours_after_reset
    """
    status_adcs = status_ocp & 0x1
    status_adb = (status_ocp >> 1) & 0x1
    status_ccb = (status_ocp >> 2) & 0x1

    parameters = {
        "timestamp_reset": timestamp_reset,
        "reset_date": reset_date,
        "voltage_raw_power": voltage_raw_power,
        "current_3v3_1": current_3v3_1,
        "current_3v3_2": current_3v3_2,
        "current_5v0": current_5v0,
        "current_unreg1": current_unreg1,
        "current_unreg2": current_unreg2,
        "current_unreg3": current_unreg3,
        "current_12v": current_12v,
        "status_3v3_1": status_3v3_1,
        "status_3v3_2": status_3v3_2,
        "status_5v": status_5v,
        "status_unreg1": status_unreg1,
        "status_unreg2": status_unreg2,
        "status_unreg3": status_unreg3,
        "status_12v": status_12v,
        "status_com_pic": status_com_pic,  
        "status_main_pic": status_main_pic,
        "timestamp_fab": timestamp_fab,
        "temp_minus_y": temp_minus_y,
        "temp_plus_x": temp_plus_x,
        "temp_minus_x": temp_minus_x,
        "temp_dsap_plus_x": temp_dsap_plus_x,
        "temp_dsap_minus_x": temp_dsap_minus_x,
        "temp_plus_y": temp_plus_y,
        "temp_bpb": temp_bpb,
        "no_data_1": no_data_1,
        "no_data_2": no_data_2,
        "no_data_3": no_data_3,
        "voltage_BCR_1": voltage_BCR_1,
        "voltage_BCR_2": voltage_BCR_2,
        "voltage_BCR_3": voltage_BCR_3,
        "current_minus_y": current_minus_y,
        "current_dsap_plus_x_3s3p": current_dsap_plus_x_3s3p,
        "current_dsap_plus_x_3s2p": current_dsap_plus_x_3s2p,
        "current_dsap_minus_x_3s2p": current_dsap_minus_x_3s2p,
        "current_dsap_minus_x_3s3p": current_dsap_minus_x_3s3p,
        "current_bm_plus_x": current_bm_plus_x,
        "current_bm_minus_x": current_bm_minus_x,
        "current_heater": current_heater,
        "voltage_raw": voltage_raw,
        "voltage_battery": voltage_battery,
        "current_raw": current_raw,
        "current_battery": current_battery,
        "temp_battery": temp_battery,
        "battery_heater_enabled": battery_heater_enabled,
        "battery_heater_on_off": battery_heater_on_off,  
        "kill_switch_status_obc": kill_switch_status_obc,
        "kill_switch_status_eps": kill_switch_status_eps,
        "temp_heater_ref": temp_heater_ref,
        "voltage_heater_ref": voltage_heater_ref,
        "timestamp_pcib": timestamp_pcib,
        "temp_pl_1": temp_pl_1,
        "temp_pl_2": temp_pl_2,
        "temp_pl_3": temp_pl_3,
        "payload_heater_enabled": payload_heater_enabled,
        "payload_heater_on_off": payload_heater_on_off,  
        "payload_heater_config": payload_heater_config,  
        "payload_sensor_config": payload_sensor_config,  
        "status_tk_px": status_tk_px,
        "status_tk_mx": status_tk_mx,
        "timestamp_adcs": timestamp_adcs,
        "v3v_status" : v3v_status,
        "v12v_low_power_status" : v12v_low_power_status,
        "v12v_high_power_status" : v12v_high_power_status,
        "v12vh_current" : v12vh_current,
        "v12vl_current" : v12vl_current,
        "boot_relay_status" : boot_relay_status,
        "watchdog_reset_enable_status" : watchdog_reset_enable_status,
        "watchdog_reset_event_status" : watchdog_reset_event_status,
        "processor_reset_arm_status" : processor_reset_arm_status,
        "tai_seconds" : tai_seconds,
        "refs_health_1pack_gps_valid" : refs_health_1pack_gps_valid,
        "refs_health_1pack_refs_valid" : refs_health_1pack_refs_valid,
        "refs_health_1pack_earth_penumbra_umbra" : refs_health_1pack_earth_penumbra_umbra,
        "mag_source_used" : mag_source_used,
        "att_status" : att_status,
        "id_status" : id_status,
        "num_attitude_stars" : num_attitude_stars,
        "inertia_index" : inertia_index,
        "sun_point_state" : sun_point_state,
        "cmd_accept_count" : cmd_accept_count,
        "cmd_reject_count" : cmd_reject_count,
        "position_wrt_eci_1" : position_wrt_eci_1,
        "position_wrt_eci_2" : position_wrt_eci_2,
        "position_wrt_eci_3" : position_wrt_eci_3,
        "velocity_wrt_eci_1" : velocity_wrt_eci_1,
        "velocity_wrt_eci_2" : velocity_wrt_eci_2,
        "velocity_wrt_eci_3" : velocity_wrt_eci_3,
        "mag_model_vector_body_1" : mag_model_vector_body_1,
        "mag_model_vector_body_2" : mag_model_vector_body_2,
        "mag_model_vector_body_3" : mag_model_vector_body_3,
        "mag_health_1pack_mag_power_state" : mag_health_1pack_mag_power_state,
        "mag_health_1pack_mag_vector_valid" : mag_health_1pack_mag_vector_valid,
        "mag_health_1pack_mag_vector_enabled" : mag_health_1pack_mag_vector_enabled,
        "mag_health_1pack_mag_test_mode" : mag_health_1pack_mag_test_mode,
        "mag_health_1pack_mag_sensor_used" : mag_health_1pack_mag_sensor_used,
        "sun_vector_body_1" : sun_vector_body_1,
        "sun_vector_body_2" : sun_vector_body_2,
        "sun_vector_body_3" : sun_vector_body_3,
        "css_health_1pack_css_power_state" : css_health_1pack_css_power_state,
        "css_health_1pack_meas_sun_valid" : css_health_1pack_meas_sun_valid,
        "css_health_1pack_sun_vector_enabled" : css_health_1pack_sun_vector_enabled,
        "css_health_1pack_css_test_mode" : css_health_1pack_css_test_mode,
        "css_health_1pack_sun_sensor_used" : css_health_1pack_sun_sensor_used,
        "q_body_wrt_eci_1" : q_body_wrt_eci_1,
        "q_body_wrt_eci_2" : q_body_wrt_eci_2,
        "q_body_wrt_eci_3" : q_body_wrt_eci_3,
        "q_body_wrt_eci_4" : q_body_wrt_eci_4,
        "att_det_health_1pack_attitude_valid" : att_det_health_1pack_attitude_valid,
        "att_det_health_1pack_meas_att_valid" : att_det_health_1pack_meas_att_valid,
        "att_det_health_1pack_meas_rate_valid" : att_det_health_1pack_meas_rate_valid,
        "att_det_health_1pack_imu_data_valid" : att_det_health_1pack_imu_data_valid,
        "att_det_health_1pack_tracker_1data_valid" : att_det_health_1pack_tracker_1data_valid,
        "body_rate_1" : body_rate_1,
        "body_rate_2" : body_rate_2,
        "body_rate_3" : body_rate_3,
        "operating_mode_1" : operating_mode_1,
        "operating_mode_2" : operating_mode_2,
        "operating_mode_3" : operating_mode_3,
        "filtered_speed_rpm_1" : filtered_speed_rpm_1,
        "filtered_speed_rpm_2" : filtered_speed_rpm_2,
        "filtered_speed_rpm_3" : filtered_speed_rpm_3,
        "motor_1_temp" : motor_1_temp,
        "motor_2_temp" : motor_2_temp,
        "motor_3_temp" : motor_3_temp,
        "att_cmd_health_1_packadcs_mode" : att_cmd_health_1_packadcs_mode,
        "att_cmd_health_1_recommend_sun_point" : att_cmd_health_1_recommend_sun_point,
        "att_cmd_health_1_sun_point_reason" : att_cmd_health_1_sun_point_reason,
        "att_ctrl_health_1pack_att_ctrl_active" : att_ctrl_health_1pack_att_ctrl_active,
        "att_ctrl_health_1pack_momentum_too_high" : att_ctrl_health_1pack_momentum_too_high,
        "att_ctrl_health_1pack_on_sun_flag" : att_ctrl_health_1pack_on_sun_flag,
        "att_ctrl_health_1pack_sun_avoid_flag" : att_ctrl_health_1pack_sun_avoid_flag,
        "att_ctrl_health_1pack_sun_source_failover" : att_ctrl_health_1pack_sun_source_failover,
        "sun_point_angle_error" : sun_point_angle_error,
        "eigen_error" : eigen_error,
        "timestamp_com": timestamp_com,
        "operation_mode": operation_mode,
        "bitrate_setting": bitrate_setting,
        "test_mode": test_mode,
        "temp_stx": temp_stx,
        "sband_rx_rssi": sband_rx_rssi,
        "freq_err": freq_err,
        "number_scheduled_command_legacy": number_scheduled_command_legacy,
        "number_scheduled_command_flash": number_scheduled_command_flash,  
        "obc_mode": obc_mode,
        "subsystem_communication": subsystem_communication,
        "hours_after_reset": hours_after_reset,
        "status_ccb": status_ccb,
        "status_adb": status_adb,
        "status_adcs": status_adcs,
        "timestamp_in_memory": timestamp_in_memory,
        "timestamp_obc": timestamp_obc,
    }

    return parameters

def decode(data:bytes): 
    # manually_fixed_start_time = None
    # sampling_time = None
    # sampling_time_set = False

    # if "_timefix_" in filename:
    #     try:
    #         manually_fixed_start_time = int(filename.split("_timefix_")[-1].split("_")[0])
    #         print("Manually fixed start time:", manually_fixed_start_time, file=sys.stderr)
    #     except ValueError:
    #         manually_fixed_start_time = None

    # if "_sampling_" in filename:
    #     try:
    #         sampling_time = int(filename.split("_sampling_")[-1].split("_")[0])
    #         print("Sampling time:", sampling_time, file=sys.stderr)
    #         sampling_time_set = True
    #     except ValueError:
    #         sampling_time = None
    
    # if(sampling_time == None):
    #     sampling_time = 20 # seconds

    # MAIN_MAIN_TELEMETLY_SIZE = 191

    # previous_timestamp = None
    # line_count = 1
    # correction_delta = 0

    parameters_array = []

    chunks = [data[i:i+MAIN_TELEMETLY_SIZE] for i in range(0, len(data), MAIN_TELEMETLY_SIZE)]
    for chunk in chunks:
        if len(chunk) < 191:
            continue
        # print(chunk[-2:])
        if chunk[-2:] != b"\xb0\x0b":
            continue
        parameters= process_telemetry_chunk(chunk)
        parameters_array.append(parameters)

    return parameters_array

# def write_parameters_array(parameters_array, filename):
#     if ".hex" in filename:
#         filename = filename.replace(".hex", ".csv")
#     else:
#         filename += ".csv"
#     with open(filename, "w") as file:
#         if parameters_array:
#             file.write(",".join(parameters_array[0].keys()) + "\n")

#         for parameters in parameters_array:
#             for key, value in parameters.items():
#                 if isinstance(value, float):
#                     file.write(f"{value:.3f},")
#                 else:
#                     file.write(f"{value},")
#             file.write("\n")  # Add a newline after each parameter set
#     return filename

# def write_combined_csv(parameters_arrays, output_filename):
#     with open(output_filename, "w") as file:
#         if parameters_arrays:
#             # Write the header from the first non-empty parameters array
#             for parameters_array in parameters_arrays:
#                 if parameters_array:
#                     file.write(",".join(parameters_array[0].keys()) + "\n")
#                     break

#         for parameters_array in parameters_arrays:
#             for parameters in parameters_array:
#                 for key, value in parameters.items():
#                     if isinstance(value, float):
#                         file.write(f"{value:.3f},")
#                     else:
#                         file.write(f"{value},")
#                 file.write("\n")  # Add a newline after each parameter set

# def process_file(filename):
#     print("Processing file:", filename, file=sys.stderr)
#     parameters_array = tlm_process(filename)
#     output_filename = write_parameters_array(parameters_array, filename)
#     print("Wrote file:", output_filename, file=sys.stderr)
#     return parameters_array
