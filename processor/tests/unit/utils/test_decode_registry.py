from decoder import decoder_real_time_telemetry
from pipeline.utils.decode_common import DECODER_REGISTRY, decode_hex_concat


def test_decode_hex_concat_returns_single_hex_record():
    assert decode_hex_concat(b"\x00\xfa\xf3\x20") == [{"hex": "00faf320"}]


def test_decoder_registry_includes_unassigned_hex_decoder():
    config = DECODER_REGISTRY["000"]

    assert config.file_id == "000"
    assert config.decoder is decode_hex_concat
    assert config.output_name == "unassigned_hex.csv"


def test_decoder_registry_includes_real_time_decoder():
    config = DECODER_REGISTRY["010"]

    assert config.file_id == "010"
    assert config.decoder is decoder_real_time_telemetry.decode
    assert config.decode_unit == decoder_real_time_telemetry.REALTIME_TLM_SIZE
    assert config.output_name == "real_time_TLM_decoded.csv"
