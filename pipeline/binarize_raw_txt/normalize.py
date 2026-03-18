import re
from pipeline.utils import constants as CONST


def normalize_log_text(text: str) -> str:
    """
    Remove unexpected line breaks around hex streams.
    """

    ts_pattern = CONST.TIMESTAMP_REGEX_STR + CONST.TIMESTAMP_SEPARATOR

    target_hex_chars = "FA32"    
    for char in target_hex_chars:
        
        pattern = f"{char}\\n+{ts_pattern}"
        text = re.sub(pattern, char, text)

    return text
