from __future__ import annotations

import argparse
from pathlib import Path

try:
    from dev._common import DEFAULT_DB_SERVER_URL, PENDING_UPLOAD_DIR
except ModuleNotFoundError:
    from _common import DEFAULT_DB_SERVER_URL, PENDING_UPLOAD_DIR

from pipeline.build_decodable_payloads.upload_queue import retry_pending_uploads


def main() -> None:
    parser = argparse.ArgumentParser(description="Retry pending DB server uploads.")
    parser.add_argument("--db-server", default=DEFAULT_DB_SERVER_URL, help="DB server URL. Defaults to S_BAND_DECODER_DB_SERVER or http://127.0.0.1:8000.")
    parser.add_argument("--queue-dir", default=PENDING_UPLOAD_DIR, type=Path, help="Pending upload JSON directory.")
    args = parser.parse_args()

    result = retry_pending_uploads(args.queue_dir, args.db_server)
    print(f"uploaded={result['uploaded']} failed={result['failed']}")


if __name__ == "__main__":
    main()
