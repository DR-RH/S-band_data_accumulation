from pipeline.step1_binarize.main import binarize
from pipeline.step2_verify_crc.main import verify_crc
from pipeline.step3_parse_into_df.main import parse_into_df
from pipeline.step4_concat_df.main import concat_data

"""
実装予定    
@dataclass
class PipelineContext:
    file_name: str
    gse: str
ctx = PipelineContext(file_name=file_name, gse="ISAS")
"""

file_name = "received_20260219_102724"
path = f"tlm/{file_name}.txt"
gse = "ISAS"

binary = binarize(path, file_name)
valid_binary = verify_crc(binary, gse, file_name)
df = parse_into_df(valid_binary, gse, file_name)
concat_data(df,file_name)
