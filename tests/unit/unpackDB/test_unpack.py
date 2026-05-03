import json

import pandas as pd
import pytest

from pipeline.unpackDB.unpack import (
    build_column_schema_from_config,
    decode_chunk_with_schema,
    decode_chunks_to_multiindex_df,
    extract_bits,
    my_extract_bits,
    unpack_to_multiindex_dict,
)


def _write_schema(path):
    schema = {
        "group_a": {
            "byte_order": ">",
            "fields": [
                {"name": "first_nibble", "start_byte": 1, "shift_bit": 0, "bit_width": 4},
                {"name": "second_byte", "start_byte": 2, "shift_bit": 0, "bit_width": 8},
            ],
        }
    }
    path.write_text(json.dumps(schema), encoding="utf-8")


def test_extract_bits_reads_big_endian_bit_range():
    assert extract_bits(bytes([0b10110000]), start_byte=1, shift_bit=0, bit_width=4, endian=">") == 0b1011


def test_my_extract_bits_reads_aligned_and_unaligned_fields():
    data = bytes([0x12, 0x34])

    assert my_extract_bits(data, start_byte=1, shift_bit=0, bit_width=8, endian=">") == 0x12
    assert my_extract_bits(data, start_byte=1, shift_bit=4, bit_width=4, endian=">") == 0x2


def test_my_extract_bits_rejects_ranges_past_data():
    with pytest.raises(ValueError):
        my_extract_bits(b"\x00", start_byte=1, shift_bit=4, bit_width=8, endian=">")


def test_unpack_to_multiindex_dict_zips_values_with_tuples():
    assert unpack_to_multiindex_dict([1, 2], [("a", "x"), ("a", "y")]) == {
        ("a", "x"): 1,
        ("a", "y"): 2,
    }


def test_decode_chunk_with_schema_uses_json_field_definitions(tmp_path):
    schema_path = tmp_path / "schema.json"
    _write_schema(schema_path)

    decoded = decode_chunk_with_schema(bytes([0x12, 0x34]), str(schema_path))

    assert decoded == {
        ("group_a", "first_nibble"): 0x1,
        ("group_a", "second_byte"): 0x34,
    }


def test_build_column_schema_from_config_preserves_field_order(tmp_path):
    schema_path = tmp_path / "schema.json"
    _write_schema(schema_path)

    columns = build_column_schema_from_config(str(schema_path))

    assert list(columns) == [("group_a", "first_nibble"), ("group_a", "second_byte")]


def test_decode_chunks_to_multiindex_df_skips_chunks_without_main_sync(tmp_path):
    schema_path = tmp_path / "schema.json"
    _write_schema(schema_path)
    valid_chunk = bytes([0x12, 0x34]) + b"\xb0\x0b"
    invalid_chunk = bytes([0xff, 0xff, 0x00, 0x00])

    df = decode_chunks_to_multiindex_df([invalid_chunk, valid_chunk], str(schema_path))

    assert isinstance(df.columns, pd.MultiIndex)
    assert len(df) == 1
    assert df[("group_a", "first_nibble")].tolist() == [0x1]
