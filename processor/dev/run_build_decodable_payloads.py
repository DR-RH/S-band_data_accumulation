from __future__ import annotations

import argparse
from pathlib import Path

try:
    from dev._common import DEFAULT_DB_PATH, DEFAULT_DB_SERVER_URL, PENDING_UPLOAD_DIR, artifact_name, intermediate_dir, read_dataframe, resolve_gse
except ModuleNotFoundError:
    from _common import DEFAULT_DB_PATH, DEFAULT_DB_SERVER_URL, PENDING_UPLOAD_DIR, artifact_name, intermediate_dir, read_dataframe, resolve_gse
from pipeline.build_decodable_payloads.process import process_decodable_df


def main() -> None:
    parser = argparse.ArgumentParser(description="Run build_decodable_payloads for parsed packet rows.")
    parser.add_argument("input", type=Path, help="Parsed packet CSV or pickle, usually step3_decode_ready.csv.")
    parser.add_argument("--name", help="Artifact folder name. Defaults to parent folder or input stem.")
    parser.add_argument("--db-server", default=DEFAULT_DB_SERVER_URL, help="DB server URL for payload upload. Defaults to S_BAND_DECODER_DB_SERVER or http://127.0.0.1:8000.")
    parser.add_argument("--local-db", action="store_true", help="Write to local SQLite instead of uploading to the DB server.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="SQLite DB path used with --local-db.")
    parser.add_argument("--no-db", action="store_true", help="Do not upload or write payload rows.")
    parser.add_argument("--gse", choices=["auto", "ISAS", "Kyutech"], default="auto")
    args = parser.parse_args()

    name = args.name or args.input.parent.name or artifact_name(args.input)
    gse = resolve_gse(args.gse, name)
    out_dir = intermediate_dir(name)
    process_decodable_df(
        read_dataframe(args.input),
        out_dir,
        args.db if args.local_db and not args.no_db else None,
        None if args.no_db or args.local_db else args.db_server,
        PENDING_UPLOAD_DIR,
        gse,
    )
    print(out_dir)


if __name__ == "__main__":
    main()
