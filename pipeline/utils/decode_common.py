from pathlib import Path
from decoder import decoder_main_HK, decoder_main_log, decoder_adcs_HK  
import pandas as pd
from dataclasses import dataclass

@dataclass
class DecoderConfig:
    file_id: str
    decoder: callable
    output_name: str
    decode_unit: int
    bin_offset_by_sync_code: callable
    sync_code: bytes
    sync_code_offset: int

    def decode(self, bin_file: Path):
        return self.decoder(bin_file)

def adcs_offset(data: bytes) -> bytes:
    SYNC_ADCS = b"\xCA\xFE"

    pos = data.find(SYNC_ADCS)

    if pos < 0:
        return b""

    offset = 36
    start = max(0, pos - offset)

    return data[start:]

def main_offset(data: bytes) -> bytes:
    SYNC_ADCS = b"\xB0\x0B"

    pos = data.find(SYNC_ADCS)

    if pos < 0:
        return b""

    offset = 191-2
    start = max(0, pos - offset)

    return data[start:]

def no_offset(data):
    return data 

def decode_undefined(data):
    return ["NO","data"]

def decode_hex_concat(data: bytes):
    return [{"hex": data.hex()}]

DECODER_REGISTRY = {
    "000": DecoderConfig(
        file_id="000",
        decoder=decode_hex_concat,
        output_name="unassigned_hex.csv",
        decode_unit=8,
        bin_offset_by_sync_code=no_offset,
        sync_code=b"",
        sync_code_offset=0,
    ),
    "001": DecoderConfig(
        file_id="001",
        decoder=decoder_main_log.decode,
        output_name="obc_decoded.csv",
        decode_unit=7,
        bin_offset_by_sync_code = no_offset,
        sync_code = b"",
        sync_code_offset = 0,
    ),
    "010": DecoderConfig(
        file_id="010",
        decoder=decode_undefined,
        output_name="undefined.csv",
        decode_unit=8,
        bin_offset_by_sync_code=no_offset,
        sync_code = b"",
        sync_code_offset = 0,
    ),
    "011": DecoderConfig(
        file_id="011",
        decoder=decoder_adcs_HK.decode,
        output_name="adcs_High_HK_decoded.csv",
        decode_unit=1473,
        bin_offset_by_sync_code = adcs_offset,
        sync_code = b"\xCA\xFE",
        sync_code_offset = 36,

    ),
    
    "100": DecoderConfig(
        file_id="100",
        decoder=decoder_adcs_HK.decode,
        output_name="adcs_Normal_HK_decoded.csv",
        decode_unit=1473,
        bin_offset_by_sync_code = adcs_offset,
        sync_code = b"\xCA\xFE",
        sync_code_offset = 36,
    ),

    "101": DecoderConfig(
        # unsetting
        file_id="101",
        decoder=decode_undefined,
        output_name="undefined.csv",
        decode_unit=8,
        bin_offset_by_sync_code=no_offset,
        sync_code = b"",
        sync_code_offset = 0,
    ),
    "110": DecoderConfig(
        file_id="110",
        decoder=decoder_main_HK.decode,
        # decoder=decoder_main_HK.decode,
        output_name="main_HK_decoded.csv",
        decode_unit=191,
        bin_offset_by_sync_code = main_offset,
        sync_code = b"\xB0\x0B",
        sync_code_offset = 191-2,
    ),
    "111": DecoderConfig(
        # unsetting
        file_id="111",
        decoder=decode_undefined,
        output_name="undefined.csv",
        decode_unit=8,
        bin_offset_by_sync_code=no_offset,
        sync_code = b"",
        sync_code_offset = 0,
    ),
}


# def get_decode_config(bin_file: Path) -> DecoderConfig | None:
#     file_id = _extract_file_id(bin_file)
#     return DECODER_REGISTRY.get(file_id)

def get_config_from_file(bin_file: Path) -> DecoderConfig | None:
    file_id = _extract_file_id(bin_file)
    return DECODER_REGISTRY.get(file_id)

def get_config_from_key(key: str) -> DecoderConfig | None:
    file_id = key[:3]
    return DECODER_REGISTRY.get(file_id)

def decode_file(data: bytes, decoder) -> Path | None:

    decoded_data = decoder(data)

    return decoded_data

# def decode_file(folder: Path, bin_path: Path) -> Path | None:
#     file_id = _extract_file_id(bin_path)    
#     config = DECODER_REGISTRY.get(file_id)

#     if config is None:
#         return None
    
#     with open(bin_path, 'rb') as f:
#         data = f.read()
#     data = data.rstrip(b"\xFF")
#     data = config.bin_offset_by_sync_code(data)

#     decoded = config.decoder(data)
#     out_folder = _replace_folder_name(folder)
#     csv_path = out_folder / config.output_name

#     _save_csv(csv_path, decoded)

#     return csv_path


def get_decode_unit(bin_file: Path) -> int | None:
    config = get_config_from_file(bin_file)
    return None if config is None else config.decode_unit

def get_decode_unit_from_key(key: str) -> int | None:
    config = get_config_from_key(key)
    return None if config is None else config.decode_unit

def _extract_file_id(bin_file: Path) -> str:
    # step4_concat_data_adcs_normal_2026-03-12_1540_decodable_hex
    return bin_file.stem.split("step4_concat_data_ID_")[-1][:3]


def _replace_folder_name(folder: Path) -> Path:
    parts = list(folder.parts)

    if len(parts) < 2:
        raise ValueError("folder depth too shallow")

    parts[1] = "decoded"
    return Path(*parts)


def _save_csv(csv_path: Path, data):
    df = pd.DataFrame(data)

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)

    print(f"saved {csv_path}")


def extract_decode_units_with_time(
    # data: bytes,
    df:pd.DataFrame,
    positions:list,
    decode_unit:int,
    packet_size: int = 116,
    ) -> bytes:

    def align_down(x: int) -> int:
        return (x // decode_unit) * decode_unit

    def align_up(x: int) -> int:
        return ((x + decode_unit - 1) // decode_unit) * decode_unit
    
    buffer = b""
    time_buffer = []
    results = []
    current_size = 0
    for _, row in df.iterrows():
        packet = row["Data"]
        ts = row["Datetime"]
        buffer += packet
        time_buffer.append(ts)
        current_size += len(packet)
    
        while current_size >= decode_unit:
            chunk = buffer[:decode_unit]
             # 代表時刻（先頭パケット）
            chunk_time = time_buffer[0]
            results.append({
                "datetime": chunk_time,
                "data": chunk
            })
            # 消費
            buffer = buffer[decode_unit:]
            current_size -= decode_unit

            # packet境界でtime_bufferも更新
            consumed = decode_unit // packet_size
            time_buffer = time_buffer[consumed:]


    return pd.DataFrame(results)

def decode_valid_chunks(
    df: pd.DataFrame,
    decode_unit: int,
    packet_size: int = 116
):
    buffer = b""
    time_buffer = []
    loss_buffer = []

    results = []

    for _, row in df.iterrows():
        buffer += row["Data"]
        time_buffer.append(row["Datetime"])
        loss_buffer.append(row["IsLoss"])

        while len(buffer) >= decode_unit:
            chunk = buffer[:decode_unit]

            # このchunkに含まれるpacket数
            pkt_count = decode_unit // packet_size

            if not any(loss_buffer[:pkt_count]):
                results.append({
                    "Datetime": time_buffer[0],
                    "Data": chunk
                })

            buffer = buffer[decode_unit:]
            time_buffer = time_buffer[pkt_count:]
            loss_buffer = loss_buffer[pkt_count:]

    return pd.DataFrame(results)

def fix_broken_bin(
    data: bytes,
    loss_positions: list[int],
    decode_unit: int,
    packet_size: int = 116,
) -> bytes:

    def align_down(x: int) -> int:
        return (x // decode_unit) * decode_unit

    def align_up(x: int) -> int:
        return ((x + decode_unit - 1) // decode_unit) * decode_unit

    chunks = []
    cursor = 0

    for pos in sorted(loss_positions):
        loss_start = pos * packet_size

        if loss_start >= len(data):
            break

        # デコード単位で切り捨て
        safe_end = align_down(loss_start)

        if cursor < safe_end:
            chunks.append(data[cursor:safe_end])

        # 壊れたパケットをスキップ（decode単位で切り上げ）
        loss_end = (pos + 1) * packet_size
        cursor = align_up(loss_end)

    if cursor < len(data):
        chunks.append(data[cursor:])

    return b"".join(chunks)
# def get_decode_unit(bin_file):
#     entry = select_decoder(bin_file)

#     if entry is None:
#         return None

#     decode_unit = entry["unit"]

#     return decode_unit




# def select_decoder(folder, bin_file):
#     file_id = bin_file.stem.split('_')[-1][:3]
    
#     match file_id:
#         case "001":
#             print('main_exe_log')
#             decoder = decode_main_exe
#         case "010":
#             print('auto_packet')
#             decoder = None
#         case "011":
#             print("ADCS high")
#             decoder = decode_adcs_high
#     return decoder 

# def decode_main_exe(folder: Path, bin_file: Path) -> Path:
#     lines = main_log_decoder.decode(bin_file)
#     new_folder_name = _replace_folder_name(folder)
#     csv_path = new_folder_name  / "obc_decoded.csv"
#     save_csv_file(csv_path, lines)
#     return csv_path


# def decode_adcs_high(folder: Path, bin_file: Path) -> Path:
#     decoded_list = adcs_main_decoder.decode(bin_file)
#     new_folder_name = _replace_folder_name(folder)
#     csv_path = new_folder_name  / "adcs_HK_decoded.csv"
#     save_csv_file(csv_path, decoded_list)

#     return csv_path
