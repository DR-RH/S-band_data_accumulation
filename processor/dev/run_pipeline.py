from __future__ import annotations

import argparse
import shutil
from pathlib import Path

try:
    from dev._common import (
        DEFAULT_DB_PATH,
        DEFAULT_DB_SERVER_URL,
        PENDING_UPLOAD_DIR,
        REPORTS_PATH,
        UNPROCESSED_INPUT_DIR,
        artifact_name,
        decoded_output_dir,
        intermediate_dir,
        is_unprocessed_input,
        processed_input_path,
        resolve_gse,
    )
except ModuleNotFoundError:
    from _common import (
        DEFAULT_DB_PATH,
        DEFAULT_DB_SERVER_URL,
        PENDING_UPLOAD_DIR,
        REPORTS_PATH,
        UNPROCESSED_INPUT_DIR,
        artifact_name,
        decoded_output_dir,
        intermediate_dir,
        is_unprocessed_input,
        processed_input_path,
        resolve_gse,
    )
from pipeline.build_decodable_payloads.process import process_decodable_df
from pipeline.decode_payloads.decode import run as decode_payloads
from pipeline.ingest_raw_log.binarize import build_timestamped_binary_from_log
from pipeline.parse_packets.main import parse_into_df
from pipeline.verify_crc.main import verify_crc


def run_file(
    path: Path,
    gse_arg: str,
    decode: bool,
    db_path: Path | None = None,
    db_server_url: str | None = None,
) -> Path:
    name = artifact_name(path)
    gse = resolve_gse(gse_arg, name)

    timestamped_binary = build_timestamped_binary_from_log(path, artifact_name=name, report_path=REPORTS_PATH)
    out_dir = intermediate_dir(name)
    valid_binary = verify_crc(timestamped_binary, gse, out_dir)
    packets_df = parse_into_df(valid_binary, gse, out_dir)
    process_decodable_df(packets_df, out_dir, db_path, db_server_url, PENDING_UPLOAD_DIR, gse)

    if decode:
        decode_payloads(out_dir, decoded_output_dir(out_dir.name))
    return out_dir


def move_to_processed(path: Path) -> Path:
    destination = processed_input_path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    counter = 1
    while destination.exists():
        destination = processed_input_path(path).with_name(f"{path.stem}_{counter}{path.suffix}")
        counter += 1
    shutil.move(str(path), destination)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full development pipeline.")
    parser.add_argument("input", type=Path, nargs="?", default=UNPROCESSED_INPUT_DIR, help="Raw telemetry log file or directory of .txt logs.")
    parser.add_argument("--gse", choices=["auto", "ISAS", "Kyutech"], default="auto")
    parser.add_argument("--db-server", default=DEFAULT_DB_SERVER_URL, help="DB server URL for payload upload. Defaults to S_BAND_DECODER_DB_SERVER or http://127.0.0.1:8000.")
    parser.add_argument("--local-db", action="store_true", help="Write to local SQLite instead of uploading to the DB server.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="SQLite DB path used with --local-db.")
    parser.add_argument("--no-db", action="store_true", help="Do not upload or write payload rows.")
    parser.add_argument("--no-decode", action="store_true", help="Stop after build_decodable_payloads.")
    parser.add_argument("--no-move", action="store_true", help="Do not move files from input/unprocessed to input/processed after successful processing.")
    args = parser.parse_args()

    paths = sorted(args.input.glob("*.txt")) if args.input.is_dir() else [args.input]
    for path in paths:
        out_dir = run_file(
            path,
            args.gse,
            decode=not args.no_decode,
            db_path=args.db if args.local_db and not args.no_db else None,
            db_server_url=None if args.no_db or args.local_db else args.db_server,
        )
        print(out_dir)
        if not args.no_move and is_unprocessed_input(path):
            moved_path = move_to_processed(path)
            print(moved_path)


if __name__ == "__main__":
    main()
