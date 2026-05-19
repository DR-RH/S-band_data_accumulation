from __future__ import annotations

import re
from pathlib import Path


DATED_DECODER_RE = re.compile(r"^(\d{8})_.+\.py$")


def list_decoders(decoder_dir: Path) -> list[dict[str, str]]:
    decoders = [{"value": "latest", "label": "latest"}]
    if not decoder_dir.exists():
        return decoders

    versions = sorted(
        {
            match.group(1)
            for path in decoder_dir.glob("*.py")
            if path.name != "__init__.py"
            if (match := DATED_DECODER_RE.match(path.name))
        },
        reverse=True,
    )
    decoders.extend({"value": version, "label": version} for version in versions)
    return decoders
