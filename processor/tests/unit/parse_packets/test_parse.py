from pipeline.parse_packets.parse import parse_packet


def test_parse_packet_extracts_supported_field_types():
    packet = b"\xFA\xF3\x20\x12\x34\xA0"
    bit_map = [
        {"Bit(s)": "24:31", "Name": "Counter", "dtype": "int"},
        {"Bit(s)": "32:39", "Name": "Payload byte", "dtype": "byte"},
        {"Bit(s)": "40:43", "Name": "Nibble", "dtype": "binary"},
    ]

    result = parse_packet(packet, bit_map, 7)

    assert result == {
        "index": 7,
        "Sync code": b"\xFA\xF3\x20",
        "Counter": 0x12,
        "Payload byte": b"\x34",
        "Nibble": "1010",
    }
