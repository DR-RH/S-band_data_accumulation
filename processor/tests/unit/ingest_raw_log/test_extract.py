from datetime import datetime, timezone

from pipeline.ingest_raw_log.extract import extract_timestamp_segments
from pipeline.utils.constants import TIMESTAMP_PATTERN


def test_extract_timestamp_segments_returns_timestamp_and_segment():
    raw = "2026-03-12T15:37:35.783567 - 00FAF3207B00"

    result = extract_timestamp_segments(raw, TIMESTAMP_PATTERN)

    assert result == [
        (
            datetime(2026, 3, 12, 15, 37, 35, 783567, tzinfo=timezone.utc),
            "00FAF3207B00",
        )
    ]


def test_extract_timestamp_segments_splits_multiple_timestamps():
    raw = (
        "2026-03-12T15:37:35.783567 - 00FAF3207B00"
        "2026-03-12T15:37:36.000000 - AAFAF320BB"
    )

    result = extract_timestamp_segments(raw, TIMESTAMP_PATTERN)

    assert [segment for _, segment in result] == ["00FAF3207B00", "AAFAF320BB"]


def test_extract_timestamp_segments_returns_empty_list_without_timestamp():
    assert extract_timestamp_segments("00FAF3207B00", TIMESTAMP_PATTERN) == []
