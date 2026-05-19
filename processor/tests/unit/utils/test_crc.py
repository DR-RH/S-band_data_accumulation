from pipeline.utils.crc import calculate_crc16, verify_packet_crc


def test_calculate_crc16_known_vector():
    assert calculate_crc16(b"123456789") == bytes.fromhex("906e")


def test_verify_packet_crc_accepts_matching_crc():
    payload = b"abcdef"
    packet = b"\x00\x01" + payload + calculate_crc16(payload) + b"\xff"

    assert verify_packet_crc(packet, calc_start=2, calc_len=len(payload))


def test_verify_packet_crc_rejects_short_or_mismatched_packet():
    assert not verify_packet_crc(b"\x00\x01", calc_start=0, calc_len=2)
    assert not verify_packet_crc(b"\x00\x01abcd\x00\x00", calc_start=2, calc_len=4)
