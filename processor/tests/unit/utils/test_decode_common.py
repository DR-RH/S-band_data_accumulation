from pathlib import Path

import pandas as pd
import pytest

from pipeline.utils.decode_common import (
    _extract_file_id,
    _replace_folder_name,
    _save_csv,
    adcs_offset,
    decode_file,
    decode_undefined,
    decode_valid_chunks,
    extract_decode_units_with_time,
    fix_broken_bin,
    get_config_from_file,
    get_config_from_key,
    get_decode_unit,
    get_decode_unit_from_key,
    main_offset,
    no_offset,
)


def test_adcs_offset_returns_data_starting_36_bytes_before_sync():
    data = bytes(range(40)) + b"\xca\xfe" + b"tail"

    assert adcs_offset(data) == data[4:]


def test_adcs_offset_returns_empty_when_sync_missing():
    assert adcs_offset(b"no sync here") == b""


def test_main_offset_returns_data_starting_189_bytes_before_sync():
    data = bytes(range(200)) + b"\xb0\x0b" + b"tail"

    assert main_offset(data) == data[11:]


def test_no_offset_returns_same_data():
    data = b"abc"

    assert no_offset(data) is data


def test_decode_undefined_returns_placeholder_record():
    assert decode_undefined(b"abc") == ["NO", "data"]


def test_get_config_from_file_extracts_id_from_step4_filename():
    path = Path("step4_concat_data_ID_110_main_HK_log_2026-03-12_1540.csv")

    assert get_config_from_file(path).file_id == "110"


def test_get_config_from_key_uses_first_three_bits():
    assert get_config_from_key("0011011001000101").file_id == "001"


def test_get_config_returns_none_for_unsupported_id():
    assert get_config_from_key("abc1011001000101") is None


def test_decode_file_delegates_to_decoder_callable():
    assert decode_file(b"\x0a", lambda data: [{"hex": data.hex()}]) == [{"hex": "0a"}]


def test_get_decode_unit_from_file_and_key():
    path = Path("step4_concat_data_ID_000_unassigned_2026-03-12_1540.csv")

    assert get_decode_unit(path) == 8
    assert get_decode_unit_from_key("1101011001000101") == 191
    assert get_decode_unit_from_key("abc1011001000101") is None


def test_extract_file_id_reads_step4_prefix():
    path = Path("step4_concat_data_ID_011_adcs_high_2026-03-12_1530.csv")

    assert _extract_file_id(path) == "011"


def test_replace_folder_name_changes_second_path_component():
    assert _replace_folder_name(Path("output/intermediate/sample")) == Path("output/decoded/sample")


def test_replace_folder_name_rejects_shallow_path():
    with pytest.raises(ValueError):
        _replace_folder_name(Path("sample"))


def test_save_csv_creates_parent_and_writes_rows(tmp_path, capsys):
    csv_path = tmp_path / "decoded" / "out.csv"

    _save_csv(csv_path, [{"a": 1}, {"a": 2}])

    assert pd.read_csv(csv_path)["a"].tolist() == [1, 2]
    assert str(csv_path) in capsys.readouterr().out


def test_extract_decode_units_with_time_builds_decode_sized_chunks():
    df = pd.DataFrame(
        [
            {"Datetime": "t1", "Data": b"ab"},
            {"Datetime": "t2", "Data": b"cd"},
            {"Datetime": "t3", "Data": b"ef"},
        ]
    )

    result = extract_decode_units_with_time(df, positions=[], decode_unit=4, packet_size=2)

    assert result.to_dict("records") == [{"datetime": "t1", "data": b"abcd"}]


def test_decode_valid_chunks_skips_chunks_with_loss():
    df = pd.DataFrame(
        [
            {"Datetime": "t1", "Data": b"ab", "IsLoss": False},
            {"Datetime": "t2", "Data": b"cd", "IsLoss": False},
            {"Datetime": "t3", "Data": b"ef", "IsLoss": True},
            {"Datetime": "t4", "Data": b"gh", "IsLoss": False},
        ]
    )

    result = decode_valid_chunks(df, decode_unit=4, packet_size=2)

    assert result.to_dict("records") == [{"Datetime": "t1", "Data": b"abcd"}]


def test_fix_broken_bin_drops_decode_unit_containing_lost_packet():
    data = bytes(range(12))

    assert fix_broken_bin(data, loss_positions=[1], decode_unit=4, packet_size=2) == bytes(range(4, 12))
