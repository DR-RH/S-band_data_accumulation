from pathlib import Path
import pickle
from .assemble import detect_missing_packet
from .io import write_concat_binaries,write_decodable_df
import pandas as pd
import numpy as np
from pipeline.utils.decode_common import get_decode_unit_from_key

AUTO_PACKET_ID = "0101011001000101"

def _break_packets(df):
    # number_of_list = len(df)
    rand_vals = np.random.rand(len(df))
    df = df[rand_vals > 0.2]

    return df

def concat_data(df: pd.DataFrame, output_path: Path):

    order_key = "Packet no."

    sorted_df = df.sort_values(order_key)
    debug_df = _break_packets(sorted_df)  # debug用途

    grouped = detect_missing_packet(debug_df)

    for packet_id, group_info in grouped.items():

        if packet_id == AUTO_PACKET_ID:
            continue

        process_packet_group(packet_id, group_info, output_path)

def process_packet_group(packet_id, group_info, output_path: Path):

    group_df = group_info["df"]
    missing_packets = group_info["missing"]

    data_type = packet_id[:3]
    decode_unit = get_decode_unit_from_key(data_type)

    decodable_df = build_decodable_df(
        group_df,
        missing_packets,
        decode_unit
    )

    write_decodable_df(decodable_df, packet_id, output_path)

def build_decodable_df(
    df: pd.DataFrame,
    missing: list[int],
    decode_unit: int,
) -> pd.DataFrame:
    """
    df: ["Datetime", "Packet no.", "Data"]
    missing: 欠損packet番号のリスト
    """

    df = df.sort_values("Packet no.").reset_index(drop=True)
    missing_set = set(missing)

    buffer = b""
    time_buffer = []

    results = []

    for _, row in df.iterrows():
        pkt_no = row["Packet no."]
        data   = row["Data"]
        ts     = row["Datetime"]

        # 欠損が来たらストリームを断絶
        if pkt_no in missing_set:
            buffer = b""
            time_buffer = []
            continue

        buffer += data
        time_buffer.append(ts)

        # decode単位で切り出し
        while len(buffer) >= decode_unit:
            chunk = buffer[:decode_unit]

            results.append({
                "Datetime": 0,  # 代表時刻（先頭）
                "Data": chunk
            })

            # 消費
            buffer = buffer[decode_unit:]

            # packet単位で削る（安全側に倒す）
            # decode_unitがpacket_sizeの倍数でない場合を考慮
            consumed_packets = len(time_buffer) - (len(buffer) // len(data))
            time_buffer = time_buffer[consumed_packets:]

    return pd.DataFrame(results)

# def main(df: pd.DataFrame , save_datetime: str):
#     out_dir = concat_data(df,save_datetime)
#     return out_dir

# if __name__ == "__main__":
#     save_datetime = 'jpg4_received_20260129_110648'

#     input_path = Path("data/intermediate_output") / save_datetime / "step3_decode_ready.pickle"

#     with open(input_path, "rb") as f:
#         df = pickle.load(f)

#     main(df, save_datetime)
