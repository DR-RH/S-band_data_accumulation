from pathlib import Path


def read_raw_log(path: str) -> str:
    """
    Read raw telemetry log as text.
    """
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_step1_output(data: bytes, out_dir: Path) -> None:
    """
    Write step1 binary output.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "step1_timestamp_injected.bin"

    with open(out_path, "wb") as f:
        f.write(data)
