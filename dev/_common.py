from __future__ import annotations

import pickle
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def infer_gse(name: str) -> str:
    return "Kyutech" if "RX_COM" in name else "ISAS"


def resolve_gse(value: str, name: str) -> str:
    return infer_gse(name) if value == "auto" else value


def artifact_name(path: Path, name: str | None = None) -> str:
    return name or path.stem


def intermediate_dir(name: str) -> Path:
    return ROOT / "data" / "intermediate_output" / name


def read_bytes(path: Path) -> bytes:
    with path.open("rb") as f:
        return f.read()


def read_dataframe(path: Path) -> pd.DataFrame:
    if path.suffix == ".pickle":
        with path.open("rb") as f:
            return pickle.load(f)
    return pd.read_csv(path)
