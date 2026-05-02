from __future__ import annotations

import argparse
from pathlib import Path

try:
    from dev._common import artifact_name, intermediate_dir, read_bytes, resolve_gse
except ModuleNotFoundError:
    from _common import artifact_name, intermediate_dir, read_bytes, resolve_gse
from pipeline.parse_packets.main import parse_into_df


def main() -> None:
    parser = argparse.ArgumentParser(description="Run parse_packets for one verified binary artifact.")
    parser.add_argument("input", type=Path, help="Binary input, usually step2_valid_packets.bin.")
    parser.add_argument("--name", help="Artifact folder name. Defaults to parent folder or input stem.")
    parser.add_argument("--gse", choices=["auto", "ISAS", "Kyutech"], default="auto")
    args = parser.parse_args()

    name = args.name or args.input.parent.name or artifact_name(args.input)
    gse = resolve_gse(args.gse, name)

    parse_into_df(read_bytes(args.input), gse, name)
    print(intermediate_dir(name) / "step3_decode_ready.csv")


if __name__ == "__main__":
    main()
