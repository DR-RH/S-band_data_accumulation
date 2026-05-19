import pytest
from pipeline.ingest_raw_log.io import *



def test_read_raw_log_basic(tmp_path):
    file_path = tmp_path / "log.txt"
    content = "sample log"

    file_path.write_text(content)

    result = read_raw_log(str(file_path))

    assert result == content

def test_read_raw_log_empty(tmp_path):
    file_path = tmp_path / "empty.txt"
    file_path.write_text("")

    result = read_raw_log(str(file_path))

    assert result == ""

def test_read_raw_log_file_not_found():
    with pytest.raises(FileNotFoundError):
        read_raw_log("non_existent_file.txt")

def test_write_step1_output_creates_file(tmp_path):
    data = b"\x00\x01\x02"

    write_step1_output(data, tmp_path)

    out_file = tmp_path / "step1_timestamp_injected.bin"

    assert out_file.exists()


def test_write_step1_output_content(tmp_path):
    data = b"\xAA\xBB"

    write_step1_output(data, tmp_path)

    out_file = tmp_path / "step1_timestamp_injected.bin"

    assert out_file.read_bytes() == data


def test_write_step1_output_overwrite(tmp_path):
    data1 = b"\x00"
    data2 = b"\xFF"

    write_step1_output(data1, tmp_path)
    write_step1_output(data2, tmp_path)

    out_file = tmp_path / "step1_timestamp_injected.bin"

    assert out_file.read_bytes() == data2