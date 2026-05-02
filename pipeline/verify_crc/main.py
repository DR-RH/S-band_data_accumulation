# pipeline/step2_extract_packets.py (推奨名)

from pipeline.verify_crc import verify_packets

def verify_crc(binary, gse_name:str , save_filename: str, ):

        
    valid_binary = verify_packets.process_data(binary, gse_name)
    
    if save_filename:
        # パス操作は pathlib 推奨
        from pathlib import Path
        out_dir = Path(f"data/intermediate_output/{save_filename}")
        out_dir.mkdir(parents=True, exist_ok=True)
        
        with open(out_dir / "step2_valid_packets.bin", "wb") as f:
            f.write(valid_binary)
    return valid_binary

# def main(input_path: str, save_filename: str, gse_name):
#     with open(input_path, "rb") as f:
#         raw_streaming_data = f.read()
#     verify_crc(input_path, save_filename, gse_name)

if __name__ == "__main__":
    # テスト用
    gse_name = 'ISAS'
    # gse_name = 'Kyutech'
    save_filename = 'jpg4_received_20260129_110648'
    main(f'data/intermediate_output/{save_filename}/step1_timestamp_injected.bin', save_filename, gse_name)
