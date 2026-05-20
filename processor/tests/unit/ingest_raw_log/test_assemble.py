import json

import pytest

from pipeline.ingest_raw_log.assemble import (
    DataIntegrityError,
    build_timestamp_injected_binary,
    choose_odd_hex_recovery,
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


def test_build_timestamp_injected_binary_recovers_odd_length_hex_and_reports(tmp_path):
    raw = "2026-03-12T15:37:35.783567 - A"
    source_path = tmp_path / "input" / "unprocessed" / "example.txt"
    source_path.parent.mkdir(parents=True)
    source_path.write_text(raw, encoding="utf-8")
    report_path = tmp_path / "output" / "reports.jsonl"

    result = build_timestamp_injected_binary(
        raw,
        TIMESTAMP_PATTERN,
        source_path=source_path,
        artifact_name="example",
        report_path=report_path,
    )

    assert result == b"\xa0"
    report = json.loads(report_path.read_text(encoding="utf-8").strip())
    assert report["type"] == "odd_hex_recovery"
    assert report["stage"] == "ingest_raw_log"
    assert report["input_file"] == str(source_path)
    assert report["artifact_name"] == "example"
    assert report["artifact_copy"].startswith("output/report_artifacts/odd_hex_recovery/example_")
    assert report["action"] == "append_trailing_zero"
    assert report["original_hex_length"] == 1
    assert report["recovered_hex_length"] == 2
    assert report["appended"] == "0"
    assert report["crc_check_follows"] is True
    assert (tmp_path / report["artifact_copy"]).read_text(encoding="utf-8") == raw


def test_choose_odd_hex_recovery_prefers_candidate_with_more_sync_words():
    recovered, selected, candidates = choose_odd_hex_recovery("AFAF320")

    assert selected["action"] == "prepend_leading_zero"
    assert selected["prepended"] == "0"
    assert bytes.fromhex(recovered).count(bytes.fromhex("FAF320")) == 1
    assert {candidate["action"]: candidate["sync_count"] for candidate in candidates} == {
        "append_trailing_zero": 0,
        "prepend_leading_zero": 1,
        "drop_first_nibble": 1,
        "drop_trailing_nibble": 0,
    }
