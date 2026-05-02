import pytest

from pipeline.verify_crc import verify_packets
from pipeline.verify_crc.verify_packets import extract_packets, process_data

SYNC = b"\xFA\xF3\x20"


def test_extract_packets_uses_gse_packet_size():
    packet = SYNC + bytes(133)
    data = b"noise" + packet + b"tail"

    result = list(extract_packets(data, "Kyutech"))

    assert result == [packet]


def test_extract_packets_uses_isas_packet_size_for_unknown_gse():
    packet = SYNC + bytes(143)
    data = b"noise" + packet + b"tail"

    result = list(extract_packets(data, "unknown"))

    assert result == [packet]


def test_process_data_does_not_print_to_stdout(capsys, monkeypatch):
    monkeypatch.setattr(verify_packets, "verify_packet_crc", lambda packet, start, length: True)

    process_data(SYNC + bytes(133), "Kyutech")

    captured = capsys.readouterr()
    assert captured.out == ""
