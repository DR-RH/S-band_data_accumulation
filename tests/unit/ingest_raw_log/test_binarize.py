from pipeline.ingest_raw_log.binarize import build_timestamped_binary_from_log
from pipeline.utils.constants import TIMESTAMP_PATTERN


def test_build_timestamped_binary_from_log_reads_and_converts_file(tmp_path):
    raw = "2026-03-11T15:37:35.783567 - 00FAF3207B00"
    log_file = tmp_path / "test.log"
    log_file.write_text(raw)

    result = build_timestamped_binary_from_log(log_file, TIMESTAMP_PATTERN)

    expected = b"\x00\xfa\xf3 \x00\x06L\xc1jHB\x8f{\x00"
    assert result == expected


def test_build_timestamped_binary_from_log_returns_empty_bytes_without_timestamps(tmp_path):
    log_file = tmp_path / "test.log"
    log_file.write_text("dummy")

    result = build_timestamped_binary_from_log(log_file, TIMESTAMP_PATTERN)

    assert result == b""
