from datetime import datetime, timezone

from pipeline.ingest_raw_log.inject import inject_timestamp_into_faf320
from pipeline.utils.convert_time import datetime_to_hex


def test_inject_timestamp_into_faf320_adds_timestamp_after_sync_code():
    timestamp = datetime(2026, 3, 12, 15, 37, 35, 783567, tzinfo=timezone.utc)
    ts_hex = datetime_to_hex(timestamp).hex()

    result = inject_timestamp_into_faf320("00FAF3207B00", timestamp)

    assert result == f"00FAF320{ts_hex}7B00"


def test_inject_timestamp_into_faf320_leaves_segment_without_sync_code_unchanged():
    timestamp = datetime(2026, 3, 12, 15, 37, 35, 783567, tzinfo=timezone.utc)

    result = inject_timestamp_into_faf320("007B00", timestamp)

    assert result == "007B00"
