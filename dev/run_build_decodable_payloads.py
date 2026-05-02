from __future__ import annotations

import argparse
from pathlib import Path

try:
    from dev._common import artifact_name, intermediate_dir, read_dataframe
except ModuleNotFoundError:
    from _common import artifact_name, intermediate_dir, read_dataframe
from pipeline.build_decodable_payloads.process import process_decodable_df


def main() -> None:
    parser = argparse.ArgumentParser(description="Run build_decodable_payloads for parsed packet rows.")
    parser.add_argument("input", type=Path, help="Parsed packet CSV or pickle, usually step3_decode_ready.csv.")
    parser.add_argument("--name", help="Artifact folder name. Defaults to parent folder or input stem.")
    args = parser.parse_args()

    name = args.name or args.input.parent.name or artifact_name(args.input)
    process_decodable_df(read_dataframe(args.input), name)
    print(intermediate_dir(name))


if __name__ == "__main__":
    main()
