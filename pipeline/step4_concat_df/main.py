from pathlib import Path
import pickle
from .assemble import concat_payloads_by_key
from .io import write_concat_binaries
import pandas as pd


def concat_data(df: pd.DataFrame , save_datetime: str):
    order_key = 'Packet no.'
    df = df.sort_values(order_key)
    concat_map = concat_payloads_by_key(
        df,
        group_key="Packet ID",
        data_column="Data",
    )
    out_dir = Path("data/intermediate_output") / save_datetime
    write_concat_binaries(concat_map, out_dir)

def main(df: pd.DataFrame , save_datetime: str):
    concat_data(df,save_datetime)
    return 

if __name__ == "__main__":
    save_datetime = 'jpg4_received_20260129_110648'

    input_path = Path("data/intermediate_output") / save_datetime / "step3_decode_ready.pickle"

    with open(input_path, "rb") as f:
        df = pickle.load(f)

    main(df, save_datetime)
