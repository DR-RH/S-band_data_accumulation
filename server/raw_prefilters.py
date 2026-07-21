from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Callable


@dataclass(frozen=True)
class RawPrefilter:
    clauses: list[str] = field(default_factory=list)
    params: list[object] = field(default_factory=list)
    supported_count: int = 0


@dataclass(frozen=True)
class LinearField:
    byte_offset: int
    width: int
    scale: float
    intercept: float = 0.0


@dataclass(frozen=True)
class EnumField:
    byte_offset: int
    values_for_decoded: Callable[[float | None, float | None], list[int] | None]


FLOAT_EPSILON = 1e-9


def build_main_hk_raw_prefilter(value_filters: list[dict[str, Any]]) -> RawPrefilter:
    clauses: list[str] = []
    params: list[object] = []
    supported_count = 0

    for value_filter in value_filters:
        element = value_filter["element"]
        lower = value_filter["lower"]
        upper = value_filter["upper"]
        if element in MAIN_HK_LINEAR_FIELDS:
            supported_count += 1
            field = MAIN_HK_LINEAR_FIELDS[element]
            raw_range = raw_range_for_linear(field, lower, upper)
            if raw_range is None:
                clauses.append("1 = 0")
                continue
            raw_min, raw_max = raw_range
            char_offset = field.byte_offset * 2 + 1
            char_width = field.width * 2
            clauses.append(f"lower(substr(data_hex, {char_offset}, {char_width})) BETWEEN ? AND ?")
            params.extend([f"{raw_min:0{char_width}x}", f"{raw_max:0{char_width}x}"])
            continue

        if element in MAIN_HK_ENUM_FIELDS:
            supported_count += 1
            field = MAIN_HK_ENUM_FIELDS[element]
            values = field.values_for_decoded(lower, upper)
            if values is None:
                continue
            if not values:
                clauses.append("1 = 0")
                continue
            char_offset = field.byte_offset * 2 + 1
            placeholders = ", ".join("?" for _ in values)
            clauses.append(f"lower(substr(data_hex, {char_offset}, 2)) IN ({placeholders})")
            params.extend(f"{value:02x}" for value in values)

    return RawPrefilter(clauses=clauses, params=params, supported_count=supported_count)


def raw_range_for_linear(field: LinearField, lower: float | None, upper: float | None) -> tuple[int, int] | None:
    max_raw = (1 << (8 * field.width)) - 1
    raw_min = 0
    raw_max = max_raw

    if lower is not None:
        threshold = (lower - field.intercept) / field.scale
        if field.scale > 0:
            raw_min = max(raw_min, math.ceil(threshold - FLOAT_EPSILON))
        else:
            raw_max = min(raw_max, math.floor(threshold + FLOAT_EPSILON))

    if upper is not None:
        threshold = (upper - field.intercept) / field.scale
        if field.scale > 0:
            raw_max = min(raw_max, math.floor(threshold + FLOAT_EPSILON))
        else:
            raw_min = max(raw_min, math.ceil(threshold - FLOAT_EPSILON))

    raw_min = max(0, raw_min)
    raw_max = min(max_raw, raw_max)
    if raw_min > raw_max:
        return None
    return raw_min, raw_max


def possible_integer_values(lower: float | None, upper: float | None, minimum: int, maximum: int) -> list[int]:
    lower_bound = minimum if lower is None else max(minimum, math.ceil(lower - FLOAT_EPSILON))
    upper_bound = maximum if upper is None else min(maximum, math.floor(upper + FLOAT_EPSILON))
    if lower_bound > upper_bound:
        return []
    return list(range(lower_bound, upper_bound + 1))


def byte_range_values(lower: float | None, upper: float | None) -> list[int] | None:
    return possible_integer_values(lower, upper, 0, 255)


def bit_values(byte_offset: int, bit: int) -> EnumField:
    def values_for_decoded(lower: float | None, upper: float | None) -> list[int] | None:
        decoded_values = possible_integer_values(lower, upper, 0, 1)
        if not decoded_values:
            return []
        if len(decoded_values) == 2:
            return None
        desired = decoded_values[0]
        return [value for value in range(256) if ((value >> bit) & 0x1) == desired]

    return EnumField(byte_offset=byte_offset, values_for_decoded=values_for_decoded)


def high_nibble_values(byte_offset: int) -> EnumField:
    def values_for_decoded(lower: float | None, upper: float | None) -> list[int] | None:
        decoded_values = possible_integer_values(lower, upper, 0, 15)
        if not decoded_values:
            return []
        if len(decoded_values) == 16:
            return None
        allowed = set(decoded_values)
        return [value for value in range(256) if (value >> 4) in allowed]

    return EnumField(byte_offset=byte_offset, values_for_decoded=values_for_decoded)


def low_nibble_values(byte_offset: int) -> EnumField:
    def values_for_decoded(lower: float | None, upper: float | None) -> list[int] | None:
        decoded_values = possible_integer_values(lower, upper, 0, 15)
        if not decoded_values:
            return []
        if len(decoded_values) == 16:
            return None
        allowed = set(decoded_values)
        return [value for value in range(256) if (value & 0xF) in allowed]

    return EnumField(byte_offset=byte_offset, values_for_decoded=values_for_decoded)


def linear_uint16(byte_offset: int, scale: float, intercept: float = 0.0) -> LinearField:
    return LinearField(byte_offset=byte_offset, width=2, scale=scale, intercept=intercept)


def raw_uint16(byte_offset: int) -> LinearField:
    return linear_uint16(byte_offset, 1.0, 0.0)


def temp_sensor(byte_offset: int, reference_mv: float) -> LinearField:
    return linear_uint16(byte_offset, -(2500 / 4096) / 5.5, reference_mv / 5.5)


MAIN_HK_LINEAR_FIELDS = {
    "temp_minus_y": temp_sensor(26, 723.5),
    "temp_plus_x": temp_sensor(28, 1030.9),
    "temp_minus_x": temp_sensor(30, 1027.7),
    "temp_dsap_plus_x": temp_sensor(32, 1014.8),
    "temp_dsap_minus_x": temp_sensor(34, 1033.3),
    "temp_plus_y": temp_sensor(36, 1013.77),
    "temp_bpb": temp_sensor(38, 1022.4),
    "no_data_1": raw_uint16(40),
    "no_data_2": raw_uint16(42),
    "no_data_3": raw_uint16(44),
    "voltage_BCR_1": linear_uint16(46, 10 / 4096),
    "voltage_BCR_2": linear_uint16(48, 10 / 4096),
    "voltage_BCR_3": linear_uint16(50, 10 / 4096),
    "current_minus_y": linear_uint16(52, 0.327357 * 3.28 / 4096, -0.0314547),
    "current_dsap_plus_x_3s3p": linear_uint16(54, 0.359681 * 3.28 / 4096, -0.00566),
    "current_dsap_plus_x_3s2p": linear_uint16(56, 0.317965 * 3.28 / 4096, -0.03349),
    "current_dsap_minus_x_3s2p": linear_uint16(58, 0.321226 * 3.28 / 4096, -0.03196),
    "current_dsap_minus_x_3s3p": linear_uint16(60, 0.311014 * 3.28 / 4096, -0.0239),
    "current_bm_plus_x": linear_uint16(62, 0.353379 * 3.28 / 4096, -0.00472),
    "current_bm_minus_x": linear_uint16(64, 0.305826 * 3.28 / 4096, -0.01856),
    "current_heater": linear_uint16(66, 4.020205 * 3.28 / 4096, -1.35776),
    "voltage_raw": linear_uint16(68, 9.9 / 4096),
    "voltage_battery": linear_uint16(70, 9.9 / 4096),
    "current_raw": linear_uint16(72, 4.020205 * 3.28 / 4096, -1.35776),
    "current_battery": linear_uint16(74, 3.863206 * 3.28 / 4096, -6.36292),
    "temp_battery": linear_uint16(76, -(3.256 * 30) / 4096, 75),
    "temp_heater_ref": linear_uint16(80, -(3.256 * 30) / 4096, 75),
    "voltage_heater_ref": linear_uint16(82, 9.9 / 4096),
}

MAIN_HK_ENUM_FIELDS = {
    "battery_heater_enabled": bit_values(78, 4),
    "battery_heater_on_off": bit_values(78, 0),
    "kill_switch_status_obc": bit_values(79, 0),
    "kill_switch_status_eps": high_nibble_values(79),
    "payload_heater_enabled": bit_values(91, 0),
    "payload_heater_on_off": bit_values(91, 4),
    "payload_heater_config": high_nibble_values(92),
    "payload_sensor_config": low_nibble_values(92),
    "status_tk_px": EnumField(93, byte_range_values),
    "status_tk_mx": EnumField(94, byte_range_values),
    "number_scheduled_command_legacy": EnumField(179, byte_range_values),
    "number_scheduled_command_flash": EnumField(180, byte_range_values),
    "obc_mode": EnumField(181, byte_range_values),
    "subsystem_communication": EnumField(182, byte_range_values),
    "status_adcs": bit_values(183, 0),
    "status_adb": bit_values(183, 1),
    "status_ccb": bit_values(183, 2),
    "hours_after_reset": EnumField(184, byte_range_values),
}
