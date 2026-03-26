import re
import logging
from typing import Optional
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
    
def hex_string_to_bytes(hex_str: str, strict: bool = False) -> bytes:
    validate_hex_string(hex_str)

    if len(hex_str) % 2 != 0:
        if strict:
            raise DataIntegrityError(
                f"Odd length hex string (len={len(hex_str)})"
            )
        hex_str += "F"

    try:
        return bytes.fromhex(hex_str)
    except ValueError as e:
        raise DataIntegrityError(f"Conversion failed: {e}") from e
# def hex_string_to_bytes(hex_str: str, strict: bool = False) -> bytes:
#     """
#     Convert hex string to bytes.
    
#     Args:
#         hex_str: Hexadecimal string to convert.
#         strict: If True, raise error on odd length. If False, pad with 'F' and log warning.
    
#     Raises:
#         DataIntegrityError: If validation fails or strict mode is violated.
#     """
#     # 基本的な形式チェック
#     try:
#         validate_hex_string(hex_str)
#     except DataIntegrityError as e:
#         logger.error(f"Invalid hex string detected: {str(e)}")
#         raise

#     # 長さチェックと処理
#     if len(hex_str) % 2 != 0:
#         msg = f"Odd length hex string detected (len={len(hex_str)}). Potential data corruption."
        
#         if strict:
#             logger.error(msg)
#             raise DataIntegrityError(msg)
#         else:
#             logger.warning(f"{msg} Padding with 'F' to proceed.")
#             hex_str += "F"
            
#     try:
#         return bytes.fromhex(hex_str)
#     except ValueError as e:
#         # validate_hex_stringを通過していればここには来ないはずだが、念のため
#         logger.critical(f"Unexpected conversion error: {e}")
#         raise DataIntegrityError(f"Conversion failed: {e}")

def build_timestamp_injected_binary(
    raw_log_text: str,
    timestamp_pattern: re.Pattern,
    strict_mode: bool = False
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
            except DataIntegrityError:
                logger.warning(f"Invalid characters found in segment {i} (Timestamp: {ts})")
                # 必要に応じてスキップするか、そのまま処理を試みる
            
            injected = inject_timestamp_into_faf320(segment, ts)
            injected_segments.append(injected)

        hex_stream = "".join(injected_segments)
        try:
            data = hex_string_to_bytes(hex_stream, strict=strict_mode) 
        except DataIntegrityError as e:
            logger.error(f"hex conversion failed: {e}")
            raise

        return data
        
    except Exception as e:
        logger.exception("Failed to build binary stream.")
        raise
