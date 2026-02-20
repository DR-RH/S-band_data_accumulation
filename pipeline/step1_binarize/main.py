from pathlib import Path
import re

from .io import read_raw_log, write_step1_output
from .assemble import build_timestamp_injected_binary
from pipeline.utils.common import get_save_directory_name
from pipeline.utils import constants as CONST

def binarize(
    path: str,
    save_datetime: str = "",
) -> bytes:
    """
    Step1:
    raw telemetry log
        -> normalize
        -> inject timestamp into FAF320
        -> binary stream
    """

    raw_text = read_raw_log(path)

    binary = build_timestamp_injected_binary(
        raw_text=raw_text,
        timestamp_pattern=CONST.TIMESTAMP_PATTERN,
    )

    if save_datetime:
        out_dir = Path(f"data/intermediate_output/{save_datetime}")  
        write_step1_output(binary, out_dir)

    return binary

def main(
    path: str,
    save_datetime: str = "",
    ) -> bytes:
    binary = binarize(path, save_datetime)

    return binary


if __name__ == "__main__":
    file_name = 'jpg4_received_20260129_110648'
    path = f"tlm/{file_name}.txt"
    save_datetime = get_save_directory_name(path)
    main(path, save_datetime)
