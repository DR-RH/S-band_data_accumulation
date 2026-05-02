from typing import Iterator


def split_into_packets(binary: bytes, packet_size: int) -> Iterator[bytes]:
    remainder = len(binary) % packet_size
    if remainder:
        raise ValueError(
            f"Binary length {len(binary)} is not divisible by packet size {packet_size}"
        )

    total = len(binary) // packet_size
    for i in range(total):
        start = i * packet_size
        yield binary[start:start + packet_size]
