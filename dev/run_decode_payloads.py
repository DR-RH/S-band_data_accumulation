from __future__ import annotations

import argparse
from pathlib import Path

try:
    import dev._common  # noqa: F401
except ModuleNotFoundError:
    import _common  # noqa: F401
from pipeline.decode_payloads.decode import run


def main() -> None:
    parser = argparse.ArgumentParser(description="Run decode_payloads for one intermediate artifact folder.")
    parser.add_argument("input", type=Path, help="Folder containing step4*.csv files.")
    args = parser.parse_args()

    run(str(args.input))
    print(Path("data/decoded") / args.input.name)


if __name__ == "__main__":
    main()
