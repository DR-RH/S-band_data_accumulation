from pipeline.utils.convert_time import datetime_to_hex


def inject_timestamp_into_faf320(
    segment: str,
    timestamp
) -> str:
    """
    Inject hexadecimal timestamp into FAF320 tag.
    """

    ts_hex = datetime_to_hex(timestamp).hex()
    return segment.replace("FAF320", f"FAF320{ts_hex}")