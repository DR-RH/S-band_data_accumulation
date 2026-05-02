import pytest
from pipeline.ingest_raw_log.binarize import *



def test_build_timestamped_binary_from_log():
    # TODO: test build_timestamped_binary_from_log
    assert False
    
def test_build_timestamped_binary_pure(tmp_path):

    log_file = tmp_path / "test.log"
    log_file.write_text("dummy")

    result = build_timestamped_binary_from_log(
        log_file,
        TIMESTAMP_PATTERN
    )

    assert isinstance(result, bytes)