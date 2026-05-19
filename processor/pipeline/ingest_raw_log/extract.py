from datetime import datetime, timezone
from typing import List, Tuple
import re


def extract_timestamp_segments(
    text: str,
    timestamp_pattern: re.Pattern,
) -> List[Tuple[datetime, str]]:
    """
    Split text by timestamp and return:
    [(timestamp, corresponding_hex_segment), ...]
    """

    compact = "".join(text.split())
    matches = list(timestamp_pattern.finditer(compact))

    segments: List[Tuple[datetime, str]] = []

    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(compact)

        ts_str = match.group()
        ts_dt = datetime.fromisoformat(ts_str).replace(tzinfo=timezone.utc)
        segment = compact[start:end].lstrip("-")

        segments.append((ts_dt, segment))

    return segments
