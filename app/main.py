from pipeline.step1_binarize.main import binarize
from pipeline.step2_verify_crc.main import verify_crc
from pipeline.step3_parse_into_df.main import parse_into_df
# from pipeline.step4_concat_df.old_main import process_decodable_df
from pipeline.decodable.process import process_decodable_df
from pipeline.step5_decode import decode
from pathlib import Path
from glob import glob
import shutil
import os
"""
実装予定    
@dataclass
class PipelineContext:
    file_name: str
    gse: str
ctx = PipelineContext(file_name=file_name, gse="ISAS")
"""
TLM_DIR = Path("tlm")

def get_ges_type(file_name):
    print(file_name)
    if "RX_COM" in file_name:
        gse = "Kyutech"
    else:
        gse = "ISAS"
    return gse


def process_file(path: Path):
    file_name = path.stem

    gse = get_ges_type(file_name)

    binary = binarize(path, file_name)
    valid_binary = verify_crc(binary, gse, file_name)
    df = parse_into_df(valid_binary, gse, file_name)

    out_dir = process_decodable_df(df, file_name)
    

    # decode.run(out_dir)


def main():
    to_dir = Path("tlm")/"processed"
    os.makedirs(to_dir,exist_ok=True)
    for path in TLM_DIR.glob("*.txt"):
        process_file(path)
        # shutil.move(str(path), to_dir / path.name)

if __name__ == "__main__":
    main()
