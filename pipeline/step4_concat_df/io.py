from pathlib import Path
from typing import Dict


def write_concat_binaries(
    data_map: Dict[int, bytes],
    out_dir: Path,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    for key, binary in data_map.items():
        path = out_dir / f"step4_concat_data_length_{key}.bin"
        with open(path, "wb") as f:
            f.write(binary)
