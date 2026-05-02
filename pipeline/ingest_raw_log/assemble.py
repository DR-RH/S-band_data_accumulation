import re
import logging
from .normalize import normalize_log_text
from .extract import extract_timestamp_segments
from .inject import inject_timestamp_into_faf320

# ロガーの設定（アプリケーション全体の設定に従うのが望ましい）
logger = logging.getLogger(__name__)

class DataIntegrityError(ValueError):
    """データの整合性に問題がある場合に発生させる例外"""
    pass

def validate_hex_string(hex_str: str) -> None:
    """
    16進数文字列として妥当か検証する
    """
    if not re.fullmatch(r"^[0-9A-Fa-f]*$", hex_str):
        raise DataIntegrityError("Hex string contains invalid characters.")
    
def hex_string_to_bytes(hex_str: str) -> bytes:
    validate_hex_string(hex_str)

    if len(hex_str) % 2 != 0:
        raise DataIntegrityError(
            f"Odd length hex string (len={len(hex_str)})"
        )

    try:
        return bytes.fromhex(hex_str)
    except ValueError as e:
        raise DataIntegrityError(f"Conversion failed: {e}") from e

def build_timestamp_injected_binary(
    raw_log_text: str,
    timestamp_pattern: re.Pattern,
    ) -> bytes:
    """
    Full step1 transformation:
    raw log text -> timestamp injected binary
    """
    
    try:
        normalized = normalize_log_text(raw_log_text)

        segments = extract_timestamp_segments(
            normalized,
            timestamp_pattern,
        )
        
        if not segments:
            logger.warning("No timestamp segments extracted. Output will be empty.")

        injected_segments = []
        for i, (ts, segment) in enumerate(segments):
            # 個別のセグメントに対しても検証を行うことが推奨される
            # ここで異常があれば、どのタイムスタンプ付近のデータか特定できる
            try:
                validate_hex_string(segment)
                injected = inject_timestamp_into_faf320(segment, ts)
                injected_segments.append(injected)
            except DataIntegrityError as e:
                raise DataIntegrityError(
                    f"Invalid characters found in segment {i} (Timestamp: {ts})"
                ) from e
            

        hex_stream = "".join(injected_segments)
        try:
            data = hex_string_to_bytes(hex_stream)
        except DataIntegrityError as e:
            logger.error(f"hex conversion failed: {e}")
            raise

        return data
        
    except Exception as e:
        logger.exception("Failed to build binary stream.")
        raise
