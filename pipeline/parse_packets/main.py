from pathlib import Path

from .assemble import build_dataframe
from .io import write_step3_output


def parse_into_df(valid_binary: bytes, gse: str, out_dir: Path | None = None):
    df = build_dataframe(valid_binary, gse)

    if out_dir is not None:
        write_step3_output(df, out_dir)

    return df
