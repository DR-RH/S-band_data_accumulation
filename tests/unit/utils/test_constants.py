import pytest

from pipeline.utils.constants import get_packet_size


def test_get_packet_size():
    assert get_packet_size("Kyutech") == 136
    assert get_packet_size("ISAS") == 146


def test_get_packet_size_uses_isas_size_for_unknown_gse():
    assert get_packet_size("unknown") == 146
