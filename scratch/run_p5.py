from pipeline.step5_decode.flow import run
folder_name = 'data/intermediate_output/MAIN_EXE_LOG_RX_GSE_TCP_192_168_0_245_2000_20260225_113429'
files = run(folder_name) 
print(files)