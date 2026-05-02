from __future__ import annotations

import argparse
from pathlib import Path

try:
    from dev._common import artifact_name, intermediate_dir
except ModuleNotFoundError:
    from _common import artifact_name, intermediate_dir
from pipeline.ingest_raw_log.binarize import build_timestamped_binary_from_log
from pipeline.ingest_raw_log.io import write_step1_output


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ingest_raw_log for one raw telemetry log.")
    parser.add_argument("input", type=Path, help="Raw telemetry log text file.")
    parser.add_argument("--name", help="Artifact folder name. Defaults to input stem.")
    args = parser.parse_args()

    name = artifact_name(args.input, args.name)
    out_dir = intermediate_dir(name)

    data = build_timestamped_binary_from_log(args.input)
    write_step1_output(data, out_dir)

    print(out_dir / "step1_timestamp_injected.bin")


if __name__ == "__main__":
    main()
