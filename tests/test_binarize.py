from pipeline.binarize_raw_txt.binarize import build_timestamped_binary_from_log
from pipeline.binarize_raw_txt.assemble import build_timestamp_injected_binary
from pipeline.utils.constants import TIMESTAMP_PATTERN
from datetime import datetime, timezone


def test_build_timestamped_binary_pure(tmp_path):

    log_file = tmp_path / "test.log"
    log_file.write_text("dummy")

    result = build_timestamped_binary_from_log(
        log_file,
        TIMESTAMP_PATTERN
    )

    assert isinstance(result, bytes)

def test_timestamp_extraction():
    raw = "2026-03-12T15:37:35.783567 - 00FAF3207B00"

    result = build_timestamp_injected_binary(raw, TIMESTAMP_PATTERN)

    assert len(result) > 0

def test_contains_expected_header():
    raw = "2026-03-12T15:37:35.783567 - 00FAF3207B00"

    result = build_timestamp_injected_binary(raw, TIMESTAMP_PATTERN)

    assert result.startswith(b"\x00\xfa\xf3")

def test_exact_binary_small_case():
    raw = "2026-03-11T15:37:35.783567 - 00FAF3207B00"
    
    # 実際の関数呼び出し
    result = build_timestamp_injected_binary(raw, TIMESTAMP_PATTERN)

    # expected を計算で生成
    expected = generate_expected_binary(raw, header_bytes=4)  # 3バイトをヘッダと仮定

    # 比較
    assert result == expected
def generate_expected_binary(raw: str, header_bytes: int) -> bytes:
    """
    raw: "YYYY-MM-DDTHH:MM:SS.micro - PAYLOAD_HEX"
    header_bytes: PAYLOAD_HEX の何バイトまでをヘッダとみなすか
    """

    # 分割
    time_str, hex_payload = raw.split(" - ")
    payload = bytes.fromhex(hex_payload)

    # UTC変換
    ts_dt = datetime.fromisoformat(time_str).replace(tzinfo=timezone.utc)
    ts_us = int(ts_dt.timestamp() * 1_000_000 + 0.5)  # 丸め補正
    ts_bytes = ts_us.to_bytes(8, "big")

    # 挿入位置
    expected = payload[:header_bytes] + ts_bytes + payload[header_bytes:]
    return expected