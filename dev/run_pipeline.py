from __future__ import annotations

import argparse
from pathlib import Path

try:
    from dev._common import artifact_name, intermediate_dir, resolve_gse
except ModuleNotFoundError:
    from _common import artifact_name, intermediate_dir, resolve_gse
from pipeline.build_decodable_payloads.process import process_decodable_df
from pipeline.decode_payloads.decode import run as decode_payloads
from pipeline.ingest_raw_log.binarize import build_timestamped_binary_from_log
from pipeline.parse_packets.main import parse_into_df
from pipeline.verify_crc.main import verify_crc


def run_file(path: Path, gse_arg: str, decode: bool) -> Path:
    name = artifact_name(path)
    gse = resolve_gse(gse_arg, name)

    timestamped_binary = build_timestamped_binary_from_log(path)
    out_dir = intermediate_dir(name)
    valid_binary = verify_crc(timestamped_binary, gse, out_dir)
    packets_df = parse_into_df(valid_binary, gse, out_dir)
    process_decodable_df(packets_df, out_dir)

    if decode:
        decode_payloads(out_dir, Path("data/decoded") / out_dir.name)
    return out_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full development pipeline.")
    parser.add_argument("input", type=Path, help="Raw telemetry log file or directory of .txt logs.")
    parser.add_argument("--gse", choices=["auto", "ISAS", "Kyutech"], default="auto")
    parser.add_argument("--no-decode", action="store_true", help="Stop after build_decodable_payloads.")
    args = parser.parse_args()

    paths = sorted(args.input.glob("*.txt")) if args.input.is_dir() else [args.input]
    for path in paths:
        out_dir = run_file(path, args.gse, decode=not args.no_decode)
        print(out_dir)


if __name__ == "__main__":
    main()
