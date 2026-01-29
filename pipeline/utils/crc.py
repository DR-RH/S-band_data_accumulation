# utils/crc.py
import crcmod

# モジュール読み込み時に一度だけ生成
_CRC_FUNC = crcmod.mkCrcFun(0x11021, initCrc=0, xorOut=0xFFFF, rev=True)

def calculate_crc16(data: bytes) -> bytes:
    """CRC16-CCITT (False) ? パラメータに基づく計算"""
    return _CRC_FUNC(data).to_bytes(2, 'big')

def verify_packet_crc(packet: bytes, calc_start: int, calc_len: int) -> bool:
    """
    パケット内の指定範囲のCRCを検証する
    
    Args:
        packet: パケットデータ全体
        calc_start: CRC計算対象の開始位置
        calc_len: CRC計算対象の長さ
    """
    # 範囲外アクセスを防ぐチェック推奨
    if len(packet) < calc_start + calc_len + 2:
        return False
        
    target_data = packet[calc_start : calc_start + calc_len]
    expected_crc = packet[calc_start + calc_len : calc_start + calc_len + 2]
    
    return calculate_crc16(target_data) == expected_crc
