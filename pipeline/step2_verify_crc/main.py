# pipeline/step2_extract_packets.py (推奨名)

from pipeline.step2_verify_crc import verify_packets

def main(input_path: str, save_filename: str, gse_name):
    with open(input_path, "rb") as f:
        raw_streaming_data = f.read()
        
    valid_binary = verify_packets.process_data(raw_streaming_data, gse_name)
    
    if save_filename:
        # パス操作は pathlib 推奨
        from pathlib import Path
        out_dir = Path(f"data/intermediate_output/{save_filename}")
        out_dir.mkdir(parents=True, exist_ok=True)
        
        with open(out_dir / "step2_valid_packets.bin", "wb") as f:
            f.write(valid_binary)

if __name__ == "__main__":
    # テスト用
    gse_name = 'ISAS'
    save_filename = 'received_20251030_133938'
    main('data/intermediate_output/received_20251030_133938/step1_timestamp_injected.bin', save_filename, gse_name)
