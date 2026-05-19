from pipeline.ingest_raw_log.normalize import normalize_log_text



def test_normalize_log_text_joins_timestamp_split_sync_code():
    timestamp = "2026-03-12T15:37:35.783567 - "

    raw = f"FA\n{timestamp}F3207B00"

    result = normalize_log_text(raw)

    assert result == "FAF3207B00"


def test_normalize_log_text_joins_timestamp_split_sync_code_B():
    timestamp = "2026-03-12T15:37:35.783567 - "

    raw = f"FAF3\n{timestamp}207B00"

    result = normalize_log_text(raw)

    assert result == "FAF3207B00"


def test_normalize_log_text_joins_all_timestamp_split_sync_code_positions():
    timestamp = "2026-03-12T15:37:35.783567 - "
    sync_code = "FAF320"

    for split_at in range(1, len(sync_code)):
        raw = f"{sync_code[:split_at]}\n{timestamp}{sync_code[split_at:]}7B00"

        result = normalize_log_text(raw)

        assert result == "FAF3207B00"

def test_normalize_log_text_preserves_non_sync_timestamp_boundary():
    timestamp = "2026-03-12T15:37:35.783567 - "

    raw = f"ABCF\n{timestamp}1234"

    result = normalize_log_text(raw)

    assert result == raw
