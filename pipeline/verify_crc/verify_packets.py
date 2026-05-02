import logging
import re
from typing import Iterator, List

import pipeline.utils.constants as CONST
from pipeline.utils.crc import verify_packet_crc

# コンパイル済み正規表現
SYNC_PATTERN = CONST.SYNC_PATTERN
logger = logging.getLogger(__name__)

def extract_packets(data: bytes,gse_name) -> Iterator[bytes]:
    """バイナリストリームからパケット候補をyieldするジェネレータ"""
    PACKET_TOTAL_LEN = CONST.get_packet_size(gse_name)
    for match in SYNC_PATTERN.finditer(data):
        start = match.start()
        end = start + PACKET_TOTAL_LEN
        
        if end <= len(data):
            yield data[start:end]

def process_data(data: bytes, gse_name: str) -> bytes:
    valid_packets: List[bytes] = []
    ges_extra_len = CONST.GSE_CONFIG.get(gse_name, CONST.GSE_CONFIG[CONST.DEFAULT_GSE_NAME])
    calc_start = CONST.SYNC_CODE_LEN + CONST.TIMESTAMP_LEN + ges_extra_len + 1 
    calc_len = 122

    for packet in extract_packets(data, gse_name):
        if verify_packet_crc(packet, calc_start, calc_len):
            valid_packets.append(packet)
            
            # デバッグ用: 特定パケットのログ出力など
            # packet_num = int.from_bytes(packet[24:26], 'big')
            # if packet_num == 7352: ...
            
    logger.info("Found %s valid packets.", len(valid_packets))
    return b"".join(valid_packets) # 最後に一括結合（高速）
