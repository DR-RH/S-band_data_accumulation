from datetime import datetime, timezone

from pipeline.utils.convert_time import add_timestamp, datetime_to_hex, hex_to_datetime


def test_datetime_to_hex_and_hex_to_datetime_round_trip_utc():
    dt = datetime(2026, 3, 12, 15, 36, 8, 105390, tzinfo=timezone.utc)

    assert hex_to_datetime(datetime_to_hex(dt)) == dt


def test_hex_to_datetime_clamps_out_of_range_timestamp():
    dt = hex_to_datetime(b"\xff\xff\xff\xff\xff\xff\xff\xff")

    assert dt.year == 9999


def test_add_timestamp_filters_invalid_lines_and_injects_before_sync(capsys):
    lines = [
        "not a timestamp - FAF320\n",
        "2026-03-12T15:36:08.105390 - ABCD\n",
        "2026-03-12T15:36:08.105390 - FAF320AA\n",
    ]

    result = add_timestamp(lines)
    expected_ts = datetime_to_hex(
        datetime(2026, 3, 12, 15, 36, 8, 105390, tzinfo=timezone.utc)
    ).hex().upper()

    assert result[0] == lines[1]
    assert f"{expected_ts}FAF320AA" in result[1]
    assert len(result) == 2
    assert capsys.readouterr().out == ""
