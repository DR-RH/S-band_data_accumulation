import re
from pipeline.utils import constants as CONST


def normalize_log_text(text: str) -> str:
    """
    Remove logger timestamps that interrupt a split FAF320 sync code.
    """

    ts_pattern = CONST.TIMESTAMP_REGEX_STR + CONST.TIMESTAMP_SEPARATOR
    sync_code = "FAF320"

    for split_at in range(1, len(sync_code)):
        prefix = sync_code[:split_at]
        suffix = sync_code[split_at:]
        pattern = f"{prefix}(?:\\r?\\n)+{ts_pattern}{suffix}"
        text = re.sub(pattern, sync_code, text)

    return text
