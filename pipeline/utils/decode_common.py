from pathlib import Path
from decoder import decoder_main_HK, decoder_main_log, decoder_adcs_HK  
import pandas as pd
from dataclasses import dataclass

@dataclass
class DecoderConfig:
    filetype: str
    decoder: callable
    output_name: str
    decode_unit: int
    bin_offset_by_sync_code: callable

    def decode(self, bin_file: Path):
        return self.decoder(bin_file)

def adcs_offset_bin(data: bytes) -> bytes:
    SYNC_ADCS = b"\xCA\xFE"

    pos = data.find(SYNC_ADCS)

    if pos < 0:
        return b""

    offset = 36
    start = max(0, pos - offset)

    return data[start:]

def no_offset(data):
    return data 

def decode_undefined(data):
    return ["NO","data"]

DECODER_REGISTRY = {
    "000": DecoderConfig(
    # undefined
        filetype="000",
        decoder=decode_undefined,
        output_name="undefined.csv",
        decode_unit=8,
        bin_offset_by_sync_code=no_offset,
    ),
    "001": DecoderConfig(
        filetype="001",
        decoder=decoder_main_log.decode,
        output_name="obc_decoded.csv",
        decode_unit=7,
        bin_offset_by_sync_code = no_offset,
    ),
    "010": DecoderConfig(
        filetype="010",
        decoder=decode_undefined,
        output_name="undefined.csv",
        decode_unit=8,
        bin_offset_by_sync_code=no_offset,
    ),
    "011": DecoderConfig(
        filetype="011",
        decoder=decoder_adcs_HK.decode,
        output_name="adcs_High_HK_decoded.csv",
        decode_unit=1473,
        bin_offset_by_sync_code = adcs_offset_bin,

    ),
    
    "100": DecoderConfig(
        filetype="100",
        decoder=decoder_adcs_HK.decode,
        output_name="adcs_Normal_HK_decoded.csv",
        decode_unit=1473,
        bin_offset_by_sync_code = adcs_offset_bin,
    ),

    "101": DecoderConfig(
        # unsetting
        filetype="101",
        decoder=decode_undefined,
        output_name="undefined.csv",
        decode_unit=8,
        bin_offset_by_sync_code=no_offset,
    ),
    "110": DecoderConfig(
        filetype="110",
        decoder=decoder_main_HK.decode,
        # decoder=decoder_main_HK.decode,
        output_name="main_HK_decoded.csv",
        decode_unit=191,
        bin_offset_by_sync_code = no_offset,
    ),
    "111": DecoderConfig(
        # unsetting
        filetype="111",
        decoder=decode_undefined,
        output_name="undefined.csv",
        decode_unit=8,
        bin_offset_by_sync_code=no_offset,
    ),
}


# def get_decode_config(bin_file: Path) -> DecoderConfig | None:
#     filetype = _extract_filetype(bin_file)
#     return DECODER_REGISTRY.get(filetype)

def get_config_from_file(bin_file: Path) -> DecoderConfig | None:
    filetype = _extract_filetype(bin_file)
    return DECODER_REGISTRY.get(filetype)

def get_config_from_key(key: str) -> DecoderConfig | None:
    filetype = key[:3]
    return DECODER_REGISTRY.get(filetype)

def decode_file(folder: Path, bin_path: Path) -> Path | None:
    config = get_config_from_file(bin_path)

    if config is None:
        return None
    
    with open(bin_path, 'rb') as f:
        data = f.read()
    data = data.rstrip(b"\xFF")
    data = config.bin_offset_by_sync_code(data)

    decoded = config.decoder(data)
    out_folder = _replace_folder_name(folder)
    csv_path = out_folder / config.output_name

    _save_csv(csv_path, decoded)

    return csv_path


def get_decode_unit(bin_file: Path) -> int | None:
    config = get_config_from_file(bin_file)
    return None if config is None else config.decode_unit
def get_decode_unit_from_key(key: str) -> int | None:
    config = get_config_from_key(key)
    return None if config is None else config.decode_unit

def _extract_filetype(bin_file: Path) -> str:
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


def fix_broken_bin(
    data: bytes,
    positions:list,
    decode_byte_unit:int,
    block: int = 116,
    ) -> bytes:

    chunks = []
    cut_off_start = 0
    for position in sorted(positions):
        loss_start = block * position
        if loss_start >= len(data):
            break
        cut_off_end = (loss_start // decode_byte_unit) * decode_byte_unit
        chunks.append(data[cut_off_start:cut_off_end])
        cut_off_start = (((position + 1) * block - 1) // decode_byte_unit + 1) * decode_byte_unit 
    chunks.append(data[cut_off_start:])
    decodable_data = b"".join(chunks)
    return decodable_data


# def get_decode_unit(bin_file):
#     entry = select_decoder(bin_file)

#     if entry is None:
#         return None

#     decode_unit = entry["unit"]

#     return decode_unit




# def select_decoder(folder, bin_file):
#     filetype = bin_file.stem.split('_')[-1][:3]
    
#     match filetype:
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