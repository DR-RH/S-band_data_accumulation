from datetime import datetime, timezone
from pipeline.utils.constants import SYNC_CODE_LEN


def parse_packet(packet: bytes, bit_map: list[dict], index: int) -> dict:
    packet_int = int.from_bytes(packet, "big")

    record = {
        "index": index,
        "Sync code": packet[:SYNC_CODE_LEN],
    }

    total_bits = len(packet) * 8

    for entry in bit_map:
        start, end = map(int, entry["Bit(s)"].split(":"))
        bit_length = end - start + 1
        mask = (1 << bit_length) - 1

        value = (packet_int >> (total_bits - end - 1)) & mask

        dtype = entry["dtype"]
        if dtype == "byte":
            record[entry["Name"]] = value.to_bytes(bit_length // 8, "big")
        elif dtype == "binary":
            # record[entry["Name"]] = bin(value)
            record[entry["Name"]] = format(value, f'0{bit_length}b')
        elif dtype == "int":
            record[entry["Name"]] = value
        elif dtype == "datetime":
            record[entry["Name"]] = datetime.fromtimestamp(
                value / 1_000_000, tz=timezone.utc
            )

    return record
