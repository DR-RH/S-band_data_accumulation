from dev._common import (
    DEFAULT_DB_SERVER_URL,
    PENDING_UPLOAD_DIR,
    REPORTS_PATH,
    UNPROCESSED_INPUT_DIR,
    decoded_output_dir,
    intermediate_dir,
    processed_input_path,
)
from pipeline.build_decodable_payloads.process import process_decodable_df
from pipeline.decode_payloads.decode import run as decode_payloads
from pipeline.ingest_raw_log.binarize import build_timestamped_binary_from_log
from pipeline.parse_packets.main import parse_into_df
from pipeline.verify_crc.main import verify_crc
from pathlib import Path
import shutil

TLM_DIR = UNPROCESSED_INPUT_DIR

def get_ges_type(file_name):
    if "RX_COM" in file_name:
        gse = "Kyutech"
    else:
        gse = "ISAS"
    return gse


def process_file(path: Path):
    folder_name = path.stem

    gse = get_ges_type(folder_name)

    timestamped_binary = build_timestamped_binary_from_log(path, artifact_name=folder_name, report_path=REPORTS_PATH)

    out_dir = intermediate_dir(folder_name)
    valid_binary = verify_crc(timestamped_binary, gse, out_dir)
    df = parse_into_df(valid_binary, gse, out_dir)

    process_decodable_df(df, out_dir, db_server_url=DEFAULT_DB_SERVER_URL, pending_upload_dir=PENDING_UPLOAD_DIR, gse=gse)
    decode_payloads(out_dir, decoded_output_dir(out_dir.name))


def main():
    TLM_DIR.mkdir(parents=True, exist_ok=True)
    for path in TLM_DIR.glob("*.txt"):
        process_file(path)
        destination = processed_input_path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), destination)

if __name__ == "__main__":
    main()
