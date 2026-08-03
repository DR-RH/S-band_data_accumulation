from decoder import decoder_main_log


def test_decode_returns_main_log_columns_in_header_order():
    result = decoder_main_log.decode(bytes.fromhex("00000000c0fa01"))

    assert result.to_dict("records") == [
        {
            "timestamp": "1970/01/01 00:00:00",
            "source": "C0",
            "command": "FA",
            "command_name": "command_trx_message",
            "return": "01",
        }
    ]


def test_decode_skips_all_ff_padding_chunks():
    result = decoder_main_log.decode(b"\xff" * 7)

    assert result.empty
    assert list(result.columns) == [
        "timestamp",
        "source",
        "command",
        "command_name",
        "return",
    ]


def test_decode_handles_large_unsigned_timestamp_without_os_error():
    result = decoder_main_log.decode(bytes.fromhex("00000080c0fa01"))

    assert result.iloc[0]["timestamp"] == "2038/01/19 03:14:08"
