from __future__ import annotations

import pickle
import sys
import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SHARED_DECODER_ROOT = ROOT.parent / "decoder_core"
if str(SHARED_DECODER_ROOT) not in sys.path:
    sys.path.insert(0, str(SHARED_DECODER_ROOT))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

INPUT_DIR = ROOT / "input"
UNPROCESSED_INPUT_DIR = INPUT_DIR / "unprocessed"
PROCESSED_INPUT_DIR = INPUT_DIR / "processed"
OUTPUT_DIR = ROOT / "output"
DECODED_OUTPUT_DIR = OUTPUT_DIR / "decoded"
ACCUMULATED_OUTPUT_DIR = OUTPUT_DIR / "accumulated"
PENDING_UPLOAD_DIR = OUTPUT_DIR / "pending_uploads"
REPORTS_PATH = OUTPUT_DIR / "reports.jsonl"
DEFAULT_DB_PATH = ACCUMULATED_OUTPUT_DIR / "payloads.sqlite"
DEFAULT_DB_SERVER_URL = os.environ.get("S_BAND_DECODER_DB_SERVER", "http://127.0.0.1:8000")


def infer_gse(name: str) -> str:
    return "Kyutech" if "RX_COM" in name else "ISAS"


def resolve_gse(value: str, name: str) -> str:
    return infer_gse(name) if value == "auto" else value


def artifact_name(path: Path, name: str | None = None) -> str:
    return name or path.stem


def intermediate_dir(name: str) -> Path:
    return ROOT / "data" / "intermediate_output" / name


def decoded_output_dir(name: str) -> Path:
    return DECODED_OUTPUT_DIR / name


def processed_input_path(path: Path) -> Path:
    return PROCESSED_INPUT_DIR / path.name


def is_unprocessed_input(path: Path) -> bool:
    try:
        return path.resolve().parent == UNPROCESSED_INPUT_DIR.resolve()
    except FileNotFoundError:
        return path.parent == UNPROCESSED_INPUT_DIR


def read_bytes(path: Path) -> bytes:
    with path.open("rb") as f:
        return f.read()


def read_dataframe(path: Path) -> pd.DataFrame:
    if path.suffix == ".pickle":
        with path.open("rb") as f:
            return pickle.load(f)
    return pd.read_csv(path)
