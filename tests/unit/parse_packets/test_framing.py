import pytest

from pipeline.parse_packets.framing import split_into_packets


def test_split_into_packets_returns_fixed_size_chunks():
    result = list(split_into_packets(b"AAABBB", 3))

    assert result == [b"AAA", b"BBB"]


def test_split_into_packets_rejects_trailing_bytes():
    with pytest.raises(ValueError, match="not divisible by packet size"):
        list(split_into_packets(b"AAABB", 3))
