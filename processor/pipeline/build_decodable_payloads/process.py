
from pipeline.build_decodable_payloads.builder import build_decodable_df
from pipeline.build_decodable_payloads.missing import detect_missing_packet
from pipeline.build_decodable_payloads.constants import AUTO_PACKET_ID
from pipeline.build_decodable_payloads.db import store_adcs_hk_payloads, store_main_hk_payloads
from pipeline.build_decodable_payloads.io import get_reference_time, write_decodable_df
from pipeline.build_decodable_payloads.realtime import build_realtime_decodable_df
from pipeline.build_decodable_payloads.upload_queue import enqueue_upload
from pipeline.build_decodable_payloads.uploader import (
    UploadConnectionError,
    payload_from_df,
    upload_adcs_hk_payloads,
    upload_main_hk_payloads,
)
from pipeline.utils.decode_common import DECODER_REGISTRY
import pandas as pd
from pathlib import Path

MAIN_HK_DATA_TYPE = "110"
ADCS_HK_DATA_TYPES = {"011", "100"}


def process_decodable_df(
    input_df: pd.DataFrame,
    out_dir: Path,
    db_path: Path | None = None,
    db_server_url: str | None = None,
    pending_upload_dir: Path | None = None,
    gse: str = "unknown",
):
    if input_df.empty:
        return out_dir

    packet_order_key = "Packet no."

    ordered_df = input_df.sort_values(packet_order_key)
    sampled_df = ordered_df
    packet_groups = detect_missing_packet(sampled_df)

    for raw_packet_id, packet_bundle in packet_groups.items():

        packet_id = normalize_packet_id(raw_packet_id)

        decodable_df = build_decodable_from_group(packet_id, packet_bundle)
        write_decodable_df(
            decodable_df,
            packet_id,
            out_dir,
            reference_time=get_reference_time(packet_bundle["df"]),
        )
        if db_path is not None:
            data_type = extract_data_type(packet_id)
            if data_type == MAIN_HK_DATA_TYPE:
                store_main_hk_payloads(db_path, packet_id, decodable_df, gse)
            if data_type in ADCS_HK_DATA_TYPES:
                store_adcs_hk_payloads(db_path, packet_id, decodable_df, gse)
        if db_server_url is not None:
            data_type = extract_data_type(packet_id)
            if data_type == MAIN_HK_DATA_TYPE:
                upload_or_queue(
                    db_server_url,
                    "/payloads/main-hk",
                    packet_id,
                    decodable_df,
                    pending_upload_dir,
                    upload_main_hk_payloads,
                    gse,
                )
            if data_type in ADCS_HK_DATA_TYPES:
                upload_or_queue(
                    db_server_url,
                    "/payloads/adcs-hk",
                    packet_id,
                    decodable_df,
                    pending_upload_dir,
                    upload_adcs_hk_payloads,
                    gse,
                )

    return out_dir


def build_decodable_from_group(packet_id, packet_bundle) -> pd.DataFrame:
    packet_id = normalize_packet_id(packet_id)

    packet_df = packet_bundle["df"]
    missing_packets = packet_bundle["missing"]

    data_type = extract_data_type(packet_id)
    config = DECODER_REGISTRY.get(data_type)
    if config is None:
        raise ValueError(f"Unsupported packet data type: {data_type}")

    if packet_id == AUTO_PACKET_ID:
        return build_realtime_decodable_df(packet_df)

    # decode_unit = get_decode_unit_from_key(data_type)
    # data_offset_by_sync_code()

    decodable_df = build_decodable_df(
        packet_df,
        missing_packets,
        config
    )
    return decodable_df

def extract_data_type(packet_id: str) -> str:
    return normalize_packet_id(packet_id)[:3]


def normalize_packet_id(packet_id) -> str:
    value = str(packet_id).strip()
    if value and set(value) <= {"0", "1"} and 13 <= len(value) <= 16:
        return value.zfill(16)
    return value


def upload_or_queue(server_url: str, endpoint: str, packet_id: str, df: pd.DataFrame, pending_upload_dir: Path | None, upload_func, gse: str):
    try:
        upload_func(server_url, packet_id, df, gse)
    except UploadConnectionError as exc:
        if pending_upload_dir is None:
            raise
        enqueue_upload(
            pending_upload_dir,
            endpoint,
            payload_from_df(packet_id, df, gse),
            str(exc),
        )
