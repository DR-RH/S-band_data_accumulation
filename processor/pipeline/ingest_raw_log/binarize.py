from __future__ import annotations

from pathlib import Path

from .io import read_raw_log
from .assemble import build_timestamp_injected_binary
from pipeline.utils import constants as CONST

DEFAULT_REPORT_PATH = Path(__file__).resolve().parents[2] / "output" / "reports.jsonl"



def build_timestamped_binary_from_log(
    log_path: Path,
    timestamp_pattern=CONST.TIMESTAMP_PATTERN,
    artifact_name: str | None = None,
    report_path: Path | None = DEFAULT_REPORT_PATH,
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
        source_path=log_path,
        artifact_name=artifact_name or log_path.stem,
        report_path=report_path,
    )

    return timestamped_binary
