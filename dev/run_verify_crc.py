from __future__ import annotations

import argparse
from pathlib import Path

try:
    from dev._common import artifact_name, intermediate_dir, read_bytes, resolve_gse
except ModuleNotFoundError:
    from _common import artifact_name, intermediate_dir, read_bytes, resolve_gse
from pipeline.verify_crc.main import verify_crc


def main() -> None:
    parser = argparse.ArgumentParser(description="Run verify_crc for one binary artifact.")
    parser.add_argument("input", type=Path, help="Binary input, usually step1_timestamp_injected.bin.")
    parser.add_argument("--name", help="Artifact folder name. Defaults to parent folder or input stem.")
    parser.add_argument("--gse", choices=["auto", "ISAS", "Kyutech"], default="auto")
    args = parser.parse_args()

    name = args.name or args.input.parent.name or artifact_name(args.input)
    gse = resolve_gse(args.gse, name)

    verify_crc(read_bytes(args.input), gse, name)
    print(intermediate_dir(name) / "step2_valid_packets.bin")


if __name__ == "__main__":
    main()
