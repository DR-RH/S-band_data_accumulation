import re
import struct

FORMAT_INFO = {
    "x": {"name": "pad byte", "python_type": "no value", "unpack": False},
    "c": {"name": "char", "python_type": "bytes(len=1)", "unpack": True},
    "b": {"name": "signed char", "python_type": "int", "unpack": True},
    "B": {"name": "unsigned char", "python_type": "int", "unpack": True},
    "?": {"name": "_Bool", "python_type": "bool", "unpack": True},
    "h": {"name": "short", "python_type": "int", "unpack": True},
    "H": {"name": "unsigned short", "python_type": "int", "unpack": True},
    "i": {"name": "int", "python_type": "int", "unpack": True},
    "I": {"name": "unsigned int", "python_type": "int", "unpack": True},
    "l": {"name": "long", "python_type": "int", "unpack": True},
    "L": {"name": "unsigned long", "python_type": "int", "unpack": True},
    "q": {"name": "long long", "python_type": "int", "unpack": True},
    "Q": {"name": "unsigned long long", "python_type": "int", "unpack": True},
    "f": {"name": "float", "python_type": "float", "unpack": True},
    "d": {"name": "double", "python_type": "float", "unpack": True},
    "s": {"name": "char[]", "python_type": "bytes", "unpack": True},
    "p": {"name": "pascal string", "python_type": "bytes", "unpack": True},
}

PREFIX_INFO = {
    "@": "native",
    "=": "native std-size",
    "<": "little-endian",
    ">": "big-endian",
    "!": "network(big-endian)",
}

def explain_struct_format(fmt: str):
    total_bytes_all = 0
    if fmt and fmt[0] in PREFIX_INFO:
        prefix = fmt[0]
        body = fmt[1:]
    else:
        prefix = "@"
        body = fmt

    tokens = re.findall(r"(\d*)([A-Za-z?x])", body)

    print(f"format       : {fmt}")
    print(f"byte order   : {PREFIX_INFO[prefix]}")
    print(f"total bytes  : {struct.calcsize(fmt)}")
    print("-" * 90)
    print(f"{'token':<8} {'count':>5} {'size_each':>10} {'total':>8} {'unpack':>8}  meaning")
    print("-" * 90)

    for count_str, code in tokens:
        count = int(count_str) if count_str else 1
        size_each = struct.calcsize(prefix + code)
        total = size_each * count
        info = FORMAT_INFO.get(code, {"name": "unknown", "python_type": "unknown", "unpack": True})
        unpack_flag = "yes" if info["unpack"] else "no"
        print(f"{count_str + code:<8} {count:>5} {size_each:>10} {total:>8} {unpack_flag:>8}  {info['name']} -> {info['python_type']}")
        total_bytes_all += total
    print(total_bytes_all)
explain_struct_format(">7B8H2B1B26H2B2H1B3H4B4B3H6B1I")
