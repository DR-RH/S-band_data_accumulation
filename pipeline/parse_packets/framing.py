from typing import Iterator
from pipeline.utils.constants import SYNC_CODE_LEN


def split_into_packets(binary: bytes, packet_size: int) -> Iterator[bytes]:
    total = len(binary) // packet_size
    for i in range(total):
        start = i * packet_size
        yield binary[start:start + packet_size]
