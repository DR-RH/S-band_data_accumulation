from math import ceil

def regroup_bitfmt_to_structfmt(bitfmt: str) -> str:
    result = []
    bit_count = 0

    def flush_bits():
        nonlocal bit_count, result
        if bit_count > 0:
            nbytes = ceil(bit_count / 8)
            result.append("B" * nbytes)
            bit_count = 0

    for ch in bitfmt:
        if ch in "123":
            bit_count += int(ch)
        elif ch in "BHI":
            flush_bits()
            result.append(ch)
        else:
            raise ValueError(f"unsupported token: {ch}")

    flush_bits()
    return compress_struct_fmt("".join(result))


def compress_struct_fmt(fmt: str) -> str:
    if not fmt:
        return fmt

    out = []
    prev = fmt[0]
    count = 1

    for ch in fmt[1:]:
        if ch == prev:
            count += 1
        else:
            out.append(f"{count}{prev}" if count > 1 else prev)
            prev = ch
            count = 1

    out.append(f"{count}{prev}" if count > 1 else prev)
    return "".join(out)

bitfmt = "111BB2111I111BBBBBBBBHHHHHHHHH11113HHH11113HHHH11111HHHBBBHHHBBB11311111HH"
fmt = regroup_bitfmt_to_structfmt(bitfmt)
print(fmt)