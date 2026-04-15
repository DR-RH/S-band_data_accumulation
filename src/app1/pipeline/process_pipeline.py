from pathlib import Path
from src.app1.service.preprocess import build_timestamped_binary_from_log
from src.app1.service.crc import verify_crc
from src.app1.service.unpack import parse_into_df
from src.app1.service.postprocess import process_decodable_df
from src.app1.service.meta import get_gse_type


def run(input_dir: str):
    tlm_dir = Path(input_dir)
    to_dir = tlm_dir / "processed"
    to_dir.mkdir(exist_ok=True)

    for path in tlm_dir.glob("*.txt"):
        process_file(path)


def process_file(path: Path):
    file_name = path.stem

    gse = get_gse_type(file_name)

    raw = build_timestamped_binary_from_log(path)

    valid = verify_crc(raw, gse, file_name)

    df = parse_into_df(valid, gse, file_name)

    process_decodable_df(df, file_name)