from __future__ import annotations

from pathlib import Path


SHARED_DECODER_DIR = Path(__file__).resolve().parents[2] / "decoder_core" / "decoder"

if SHARED_DECODER_DIR.exists():
    __path__.append(str(SHARED_DECODER_DIR))
