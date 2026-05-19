from __future__ import annotations

import argparse
from pathlib import Path

try:
    from dev._common import decoded_output_dir
except ModuleNotFoundError:
    from _common import decoded_output_dir
from pipeline.decode_payloads.decode import run


def main() -> None:
    parser = argparse.ArgumentParser(description="Run decode_payloads for one intermediate artifact folder.")
    parser.add_argument("input", type=Path, help="Folder containing step4*.csv files.")
    args = parser.parse_args()

    out_dir = decoded_output_dir(args.input.name)
    written_paths = run(args.input, out_dir)
    for path in written_paths:
        print(path)


if __name__ == "__main__":
    main()
