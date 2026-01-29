from pathlib import Path

from .assemble import build_dataframe, load_structure_file
from .io import write_step3_output

def main(binary: bytes, gse: str, save_datetime: str = ""):


    df = build_dataframe(binary, gse)

    if save_datetime:
        out_dir = Path(f"data/intermediate_output/{save_datetime}") 
        write_step3_output(df, out_dir)

    return df


if __name__ == "__main__":
    packet_filename = 'data/intermediate_output/received_20251030_133938/step2_valid_packets'
    
    with open(packet_filename +'.bin', 'rb') as f:
        packets = f.read()

    save_datetime = packet_filename.split('/')[-2]
    gse = "ISAS" 
    df = main(packets, gse, save_datetime)
    print(df)

