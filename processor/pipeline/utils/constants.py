# constants.py
import re

# 基本的なタイムスタンプパターンの定義 (ISO 8601 like format)
TIMESTAMP_REGEX_STR = (
    r"\d{4}-\d{2}-\d{2}T"
    r"\d{2}:\d{2}:\d{2}"
    r"(?:\.\d+)?"
)

# コンパイル済みのパターン（検索・抽出用）
TIMESTAMP_PATTERN = re.compile(TIMESTAMP_REGEX_STR)

# ログ内の区切り文字を含めたパターン（置換・正規化用）
# 注: 元のnormalize.pyにある " - " もここで定義するか、使用側で結合します
TIMESTAMP_SEPARATOR = r"\s-\s"
SYNC_PATTERN = re.compile(b'\xFA\xF3\x20', re.DOTALL)


# パケット構造定義
SYNC_CODE_LEN = 3   # Sync(3) 
TIMESTAMP_LEN = 8  #  Timestamp(8) 
ORIGINAL_SIZE = 128 
CRC_LEN = 2

# GSEごとの追加バイト数定義
GSE_CONFIG = {
    "Kyutech": 0,
    "ISAS": 10
}
DEFAULT_GSE_NAME = "ISAS"

def get_packet_size(gse_name: str) -> int:
    ges_extra = GSE_CONFIG.get(gse_name, GSE_CONFIG[DEFAULT_GSE_NAME])
    # 全長 = Header + ges_Extra + Payload + CRC 
    return ORIGINAL_SIZE + TIMESTAMP_LEN + ges_extra  # 元コードの MIN_PACKET_LEN に相当
