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
    parser.add_argument("--db", type=Path, default=Path("data/main_hk.sqlite"), help="SQLite DB path for Main HK payload rows.")
    parser.add_argument("--db-server", help="Upload payload rows to a running DB server, for example http://127.0.0.1:8000.")
    parser.add_argument("--no-db", action="store_true", help="Do not write Main HK rows to SQLite.")
    args = parser.parse_args()

    name = args.name or args.input.parent.name or artifact_name(args.input)
    out_dir = intermediate_dir(name)
    process_decodable_df(
        read_dataframe(args.input),
        out_dir,
        None if args.no_db or args.db_server else args.db,
        None if args.no_db else args.db_server,
    )
    print(out_dir)


if __name__ == "__main__":
    main()
