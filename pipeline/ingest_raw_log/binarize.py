from pathlib import Path

from .io import read_raw_log
from .assemble import build_timestamp_injected_binary
from pipeline.utils import constants as CONST




def build_timestamped_binary_from_log(
    log_path: Path,
    timestamp_pattern=CONST.TIMESTAMP_PATTERN
) -> bytes:
    """
    Step1:
    raw telemetry log
        -> inject timestamp into FAF320
        -> binary stream
    """

    raw_log_text = read_raw_log(log_path)

    timestamped_binary = build_timestamp_injected_binary(
        raw_log_text=raw_log_text,
        timestamp_pattern=timestamp_pattern,
    )

    return timestamped_binary