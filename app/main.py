from pipeline.step1_binarize.main import binarize
from pipeline.step2_verify_crc.main import verify_crc
from pipeline.step3_parse_into_df.main import parse_into_df
from pipeline.step4_concat_df.main import concat_data
from pipeline.step5_decode import decode
from pathlib import Path

"""
実装予定    
@dataclass
class PipelineContext:
    file_name: str
    gse: str
ctx = PipelineContext(file_name=file_name, gse="ISAS")
"""

def get_ges_type(file_name):
    print(file_name)
    if "RX_COM" in file_name:
        gse = "Kyutech"
    else:
        gse = "ISAS"
    return gse
file_name = "all_tlm_in_RX_COM_COM7_20260312_153552"
# file_name = "MAIN_EXE_LOG_RX_GSE_TCP_192_168_0_245_2000_20260225_113429"
# file_name = "Sun_tracking_RX_GSE_TCP_received_202603021739"
path = Path("tlm")/f"{file_name}.txt"
# gse = "Kyutech"
gse = get_ges_type(file_name)
binary = binarize(path, file_name)
valid_binary = verify_crc(binary, gse, file_name)
df = parse_into_df(valid_binary, gse, file_name)
# print(df)
out_dir = concat_data(df,file_name)
print(out_dir)
decode.run(out_dir)
# decodable_path = path/""
