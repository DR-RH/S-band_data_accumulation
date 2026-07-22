from __future__ import annotations

from dataclasses import dataclass, field
import datetime as dt
import math
from typing import Any, Callable


def identity_value(value: int) -> int:
    return value


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
    zero_if_reset_invalid: bool = False


@dataclass(frozen=True)
class EnumField:
    byte_offset: int
    values_for_decoded: Callable[[float | None, float | None], list[int] | None]
    decode_value: Callable[[int], Any] = identity_value
    zero_if_reset_invalid: bool = False


@dataclass(frozen=True)
class TimestampDeltaField:
    byte_offset: int


FLOAT_EPSILON = 1e-9
RESET_INVALID = 0xFF


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


def bit_values(byte_offset: int, bit: int, *, zero_if_reset_invalid: bool = False) -> EnumField:
    def values_for_decoded(lower: float | None, upper: float | None) -> list[int] | None:
        decoded_values = possible_integer_values(lower, upper, 0, 1)
        if not decoded_values:
            return []
        if len(decoded_values) == 2:
            return None
        desired = decoded_values[0]
        return [value for value in range(256) if ((value >> bit) & 0x1) == desired]

    def decode_value(value: int) -> int:
        return (value >> bit) & 0x1

    return EnumField(
        byte_offset=byte_offset,
        values_for_decoded=values_for_decoded,
        decode_value=decode_value,
        zero_if_reset_invalid=zero_if_reset_invalid,
    )


def high_nibble_values(byte_offset: int, *, zero_if_reset_invalid: bool = False) -> EnumField:
    def values_for_decoded(lower: float | None, upper: float | None) -> list[int] | None:
        decoded_values = possible_integer_values(lower, upper, 0, 15)
        if not decoded_values:
            return []
        if len(decoded_values) == 16:
            return None
        allowed = set(decoded_values)
        return [value for value in range(256) if (value >> 4) in allowed]

    def decode_value(value: int) -> int:
        return value >> 4

    return EnumField(
        byte_offset=byte_offset,
        values_for_decoded=values_for_decoded,
        decode_value=decode_value,
        zero_if_reset_invalid=zero_if_reset_invalid,
    )


def low_nibble_values(byte_offset: int, *, zero_if_reset_invalid: bool = False) -> EnumField:
    def values_for_decoded(lower: float | None, upper: float | None) -> list[int] | None:
        decoded_values = possible_integer_values(lower, upper, 0, 15)
        if not decoded_values:
            return []
        if len(decoded_values) == 16:
            return None
        allowed = set(decoded_values)
        return [value for value in range(256) if (value & 0xF) in allowed]

    def decode_value(value: int) -> int:
        return value & 0xF

    return EnumField(
        byte_offset=byte_offset,
        values_for_decoded=values_for_decoded,
        decode_value=decode_value,
        zero_if_reset_invalid=zero_if_reset_invalid,
    )


def linear_uint16(
    byte_offset: int,
    scale: float,
    intercept: float = 0.0,
    *,
    zero_if_reset_invalid: bool = False,
) -> LinearField:
    return LinearField(
        byte_offset=byte_offset,
        width=2,
        scale=scale,
        intercept=intercept,
        zero_if_reset_invalid=zero_if_reset_invalid,
    )


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

MAIN_HK_RESET_LINEAR_FIELDS = {
    "voltage_raw_power": linear_uint16(7, 9.9 / 4096, zero_if_reset_invalid=True),
    "current_3v3_1": linear_uint16(9, 1606.822 * 3.3 / 4096, -37.39071, zero_if_reset_invalid=True),
    "current_3v3_2": linear_uint16(11, 1595.419618 * 3.3 / 4096, -0.252035868, zero_if_reset_invalid=True),
    "current_5v0": linear_uint16(13, 801.63197 * 3.3 / 4096, -3.163097, zero_if_reset_invalid=True),
    "current_unreg1": linear_uint16(15, 2407.441267 * 3.3 / 4096, -6.117030991, zero_if_reset_invalid=True),
    "current_unreg2": linear_uint16(17, 2421.76513 * 3.3 / 4096, -10.1421109, zero_if_reset_invalid=True),
    "current_unreg3": linear_uint16(19, 1973.436273 * 3.3 / 4096, -9.717381297, zero_if_reset_invalid=True),
    "current_12v": linear_uint16(21, 1567.774583 * 3.3 / 4096, -3.51635074, zero_if_reset_invalid=True),
}

MAIN_HK_RESET_ENUM_FIELDS = {
    "status_3v3_1": bit_values(23, 7, zero_if_reset_invalid=True),
    "status_3v3_2": bit_values(23, 6, zero_if_reset_invalid=True),
    "status_5v": bit_values(23, 5, zero_if_reset_invalid=True),
    "status_unreg1": bit_values(23, 4, zero_if_reset_invalid=True),
    "status_unreg2": bit_values(23, 3, zero_if_reset_invalid=True),
    "status_unreg3": bit_values(23, 2, zero_if_reset_invalid=True),
    "status_12v": bit_values(23, 1, zero_if_reset_invalid=True),
    "status_com_pic": bit_values(23, 0, zero_if_reset_invalid=True),
    "status_main_pic": bit_values(24, 0, zero_if_reset_invalid=True),
}

MAIN_HK_TIMESTAMP_DELTA_FIELDS = {
    "timestamp_reset": TimestampDeltaField(0),
    "timestamp_fab": TimestampDeltaField(25),
    "timestamp_pcib": TimestampDeltaField(84),
    "timestamp_adcs": TimestampDeltaField(95),
    "timestamp_com": TimestampDeltaField(169),
}

MAIN_HK_SINGLE_LINEAR_FIELDS = {
    **MAIN_HK_RESET_LINEAR_FIELDS,
    **MAIN_HK_LINEAR_FIELDS,
}

MAIN_HK_SINGLE_ENUM_FIELDS = {
    **MAIN_HK_RESET_ENUM_FIELDS,
    **MAIN_HK_ENUM_FIELDS,
}

MAIN_HK_SINGLE_BASE_COLUMNS = {
    "unit_id",
    "gse",
    "packet_id",
    "received_time",
    "timestamp_obc",
    "sort_timestamp",
}

MAIN_HK_SINGLE_SPECIAL_COLUMNS = {
    "reset_date",
    "timestamp_in_memory",
}


def can_decode_main_hk_single_columns(columns: list[str]) -> bool:
    return not unsupported_main_hk_single_columns(columns)


def unsupported_main_hk_single_columns(columns: list[str]) -> list[str]:
    return [column for column in columns if not is_main_hk_single_column(column)]


def is_main_hk_single_column(column: str) -> bool:
    return (
        column in MAIN_HK_SINGLE_BASE_COLUMNS
        or column in MAIN_HK_SINGLE_LINEAR_FIELDS
        or column in MAIN_HK_SINGLE_ENUM_FIELDS
        or column in MAIN_HK_TIMESTAMP_DELTA_FIELDS
        or column in MAIN_HK_SINGLE_SPECIAL_COLUMNS
    )


def decode_main_hk_single_rows(rows: list[Any], columns: list[str]) -> list[dict[str, Any]]:
    return [decode_main_hk_single_row(row, columns) for row in rows]


def decode_main_hk_single_row(row: Any, columns: list[str]) -> dict[str, Any]:
    data = data_bytes(row_get(row, "data_hex"))
    values: dict[str, Any] = {}
    for column in columns:
        if column in MAIN_HK_SINGLE_BASE_COLUMNS:
            continue
        if column in MAIN_HK_SINGLE_LINEAR_FIELDS:
            values[column] = decode_linear_value(data, MAIN_HK_SINGLE_LINEAR_FIELDS[column])
            continue
        if column in MAIN_HK_SINGLE_ENUM_FIELDS:
            values[column] = decode_enum_value(data, MAIN_HK_SINGLE_ENUM_FIELDS[column])
            continue
        if column in MAIN_HK_TIMESTAMP_DELTA_FIELDS:
            values[column] = decode_timestamp_delta(row, data, MAIN_HK_TIMESTAMP_DELTA_FIELDS[column])
            continue
        if column == "reset_date":
            values[column] = decode_reset_date(data)
            continue
        if column == "timestamp_in_memory":
            values[column] = format_unix_timestamp(base_unix_timestamp(row))
            continue
        values[column] = ""
    return values


def decode_linear_value(data: bytes, field: LinearField) -> float | int | str:
    if field.zero_if_reset_invalid and reset_is_invalid(data):
        return 0
    raw_value = raw_uint(data, field.byte_offset, field.width)
    if raw_value is None:
        return ""
    return raw_value * field.scale + field.intercept


def decode_enum_value(data: bytes, field: EnumField) -> Any:
    if field.zero_if_reset_invalid and reset_is_invalid(data):
        return 0
    raw_value = raw_uint(data, field.byte_offset, 1)
    if raw_value is None:
        return ""
    return field.decode_value(raw_value)


def decode_timestamp_delta(row: Any, data: bytes, field: TimestampDeltaField) -> str:
    delta = raw_uint(data, field.byte_offset, 1)
    if delta is None:
        return ""
    if delta == RESET_INVALID:
        return format_unix_timestamp(0)
    return format_unix_timestamp(base_unix_timestamp(row) - delta)


def decode_reset_date(data: bytes) -> str:
    if reset_is_invalid(data) or len(data) < 7:
        return ""
    try:
        value = dt.datetime(
            2000 + data[1],
            data[2],
            data[3],
            data[4],
            data[5],
            data[6],
            tzinfo=dt.timezone.utc,
        )
    except ValueError:
        return ""
    return value.strftime("%Y/%m/%d %H:%M:%S")


def reset_is_invalid(data: bytes) -> bool:
    return len(data) <= 0 or data[0] == RESET_INVALID


def raw_uint(data: bytes, byte_offset: int, width: int) -> int | None:
    end = byte_offset + width
    if byte_offset < 0 or len(data) < end:
        return None
    return int.from_bytes(data[byte_offset:end], "big", signed=False)


def data_bytes(data_hex: Any) -> bytes:
    if not isinstance(data_hex, str):
        return b""
    try:
        return bytes.fromhex(data_hex)
    except ValueError:
        return b""


def base_unix_timestamp(row: Any) -> float:
    sort_timestamp = row_get(row, "sort_timestamp")
    try:
        return float(sort_timestamp)
    except (TypeError, ValueError):
        pass

    timestamp_obc = row_get(row, "timestamp_obc")
    if not isinstance(timestamp_obc, str):
        return 0
    timestamp_text = timestamp_obc.strip().replace("Z", "+00:00")
    try:
        return dt.datetime.fromisoformat(timestamp_text).timestamp()
    except ValueError:
        try:
            parsed = dt.datetime.strptime(timestamp_obc.strip(), "%Y/%m/%d %H:%M:%S")
        except ValueError:
            return 0
        return parsed.replace(tzinfo=dt.timezone.utc).timestamp()


def format_unix_timestamp(unix_time: float) -> str:
    return dt.datetime.fromtimestamp(unix_time, tz=dt.timezone.utc).strftime("%Y/%m/%d %H:%M:%S")


def row_get(row: Any, column: str) -> Any:
    try:
        return row[column]
    except (KeyError, IndexError, TypeError):
        return None
