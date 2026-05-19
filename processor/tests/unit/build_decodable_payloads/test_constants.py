from pipeline.build_decodable_payloads.constants import AUTO_PACKET_ID


def test_auto_packet_id_is_16_bit_binary_string():
    assert AUTO_PACKET_ID == "0101011001000101"
    assert len(AUTO_PACKET_ID) == 16
    assert set(AUTO_PACKET_ID) <= {"0", "1"}
