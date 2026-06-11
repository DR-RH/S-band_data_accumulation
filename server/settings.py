from __future__ import annotations

import os
from pathlib import Path


SERVER_ROOT = Path(__file__).resolve().parent
DEFAULT_DB_PATH = SERVER_ROOT / "data" / "payloads.sqlite"
DB_PATH_ENV = "S_BAND_DECODER_DB"
DEFAULT_DECODER_DIR = Path(__file__).resolve().parents[1] / "decoder_core" / "decoder"
DECODER_DIR_ENV = "S_BAND_DECODER_DIR"


def db_path() -> Path:
    return Path(os.environ.get(DB_PATH_ENV, DEFAULT_DB_PATH))


def decoder_dir() -> Path:
    return Path(os.environ.get(DECODER_DIR_ENV, DEFAULT_DECODER_DIR))
