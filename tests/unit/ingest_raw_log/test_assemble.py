import pytest

from pipeline.ingest_raw_log.assemble import (
    DataIntegrityError,
    build_timestamp_injected_binary,
    hex_string_to_bytes,
    validate_hex_string,
)
from pipeline.utils.constants import TIMESTAMP_PATTERN


def test_validate_hex_string_accepts_hex_characters():
    validate_hex_string("00FAF3207B00abcdef")


def test_validate_hex_string_rejects_non_hex_characters():
    with pytest.raises(DataIntegrityError, match="invalid characters"):
        validate_hex_string("00FAF320ZZ")


def test_hex_string_to_bytes_converts_even_length_hex():
    assert hex_string_to_bytes("00FAF320") == b"\x00\xfa\xf3\x20"


def test_hex_string_to_bytes_rejects_odd_length_hex():
    with pytest.raises(DataIntegrityError, match="Odd length hex string"):
        hex_string_to_bytes("ABC")


def test_build_timestamp_injected_binary_injects_timestamp():
    raw = "2026-03-11T15:37:35.783567 - 00FAF3207B00"

    result = build_timestamp_injected_binary(raw, TIMESTAMP_PATTERN)

    expected = b"\x00\xfa\xf3 \x00\x06L\xc1jHB\x8f{\x00"
    assert result == expected


def test_build_timestamp_injected_binary_rejects_invalid_hex_segment():
    raw = "2026-03-12T15:37:35.783567 - 00FAF3207BZZ"

    with pytest.raises(DataIntegrityError, match="Invalid characters found in segment 0"):
        build_timestamp_injected_binary(raw, TIMESTAMP_PATTERN)
