from pathlib import Path
from decoder import main_log_decoder, adcs_main_decoder
import pandas as pd
from dataclasses import dataclass

@dataclass
class DecoderConfig:
    filetype: str
    decoder: callable
    output_name: str
    decode_unit: int

    def decode(self, bin_file: Path):
        return self.decoder(bin_file)

DECODER_REGISTRY = {
    "001": DecoderConfig(
        filetype="001",
        decoder=main_log_decoder.decode,
        output_name="obc_decoded.csv",
        decode_unit=7,
    ),
    "011": DecoderConfig(
        filetype="011",
        decoder=adcs_main_decoder.decode,
        output_name="adcs_HK_decoded.csv",
        decode_unit=1473,
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

def decode_file(folder: Path, bin_file: Path) -> Path | None:
    config = get_config_from_file(bin_file)

    if config is None:
        return None
    decoded = config.decoder(bin_file)
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
    return bin_file.stem.split("step4_concat_data_ID_")[-1][:3]


def _replace_folder_name(folder: Path) -> Path:
    parts = list(folder.parts)

    if len(parts) < 2:
        raise ValueError("folder depth too shallow")

    parts[1] = "final_product"
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