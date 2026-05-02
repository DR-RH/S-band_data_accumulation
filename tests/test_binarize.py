from pipeline.ingest_raw_log.binarize import build_timestamped_binary_from_log
from pipeline.ingest_raw_log.assemble import build_timestamp_injected_binary
from pipeline.utils.constants import TIMESTAMP_PATTERN
from datetime import datetime, timezone


def test_build_timestamped_binary_pure(tmp_path):

    log_file = tmp_path / "test.log"
    log_file.write_text("dummy")

    result = build_timestamped_binary_from_log(
        log_file,
        TIMESTAMP_PATTERN
    )

    assert isinstance(result, bytes)

def test_timestamp_extraction():
    raw = "2026-03-12T15:37:35.783567 - 00FAF3207B00"

    result = build_timestamp_injected_binary(raw, TIMESTAMP_PATTERN)

    assert len(result) > 0

def test_contains_expected_header():
    raw = "2026-03-12T15:37:35.783567 - 00FAF3207B00"

    result = build_timestamp_injected_binary(raw, TIMESTAMP_PATTERN)

    assert result.startswith(b"\x00\xfa\xf3")

def test_exact_binary_small_case():
    raw = "2026-03-11T15:37:35.783567 - 00FAF3207B00"

    result = build_timestamp_injected_binary(raw, TIMESTAMP_PATTERN)

    # # # 完全固定（事前に手計算）
    expected = b'\x00\xfa\xf3 \x00\x06L\xc1jHB\x8f{\x00'

    assert result == expected