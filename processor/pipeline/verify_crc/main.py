from pathlib import Path

from pipeline.verify_crc import verify_packets


def verify_crc(binary: bytes, gse_name: str, out_dir: Path | None = None) -> bytes:
    valid_binary = verify_packets.process_data(binary, gse_name)

    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)

        with open(out_dir / "step2_valid_packets.bin", "wb") as f:
            f.write(valid_binary)

    return valid_binary
