from types import SimpleNamespace

import pandas as pd
import pytest

from pipeline.build_decodable_payloads import process


def test_process_decodable_df_returns_out_dir_for_empty_input(tmp_path):
    result = process.process_decodable_df(pd.DataFrame(), tmp_path)

    assert result == tmp_path


def test_process_decodable_df_writes_non_auto_packet_groups(tmp_path, monkeypatch):
    input_df = pd.DataFrame([{"Packet no.": 1}])
    bundle = {"df": pd.DataFrame([{"Packet no.": 1}]), "missing": []}
    written = []

    monkeypatch.setattr(process, "detect_missing_packet", lambda df: {"001000": bundle})
    monkeypatch.setattr(process, "build_decodable_from_group", lambda packet_id, packet_bundle: pd.DataFrame([{"Data": "aa"}]))
    monkeypatch.setattr(process, "write_decodable_df", lambda df, packet_id, out_dir: written.append((packet_id, out_dir)))

    result = process.process_decodable_df(input_df, tmp_path)

    assert result == tmp_path
    assert written == [("001000", tmp_path)]


def test_build_decodable_from_group_accepts_unassigned_data_type(monkeypatch):
    packet_bundle = {"df": pd.DataFrame([{"Packet no.": 1, "Data": b"aa"}]), "missing": []}

    monkeypatch.setattr(process, "build_decodable_df", lambda df, missing, cfg: pd.DataFrame([{"cfg": cfg}]))

    result = process.build_decodable_from_group("0000000000000000", packet_bundle)

    assert result.iloc[0]["cfg"].file_id == "000"


def test_build_decodable_from_group_rejects_unsupported_data_type():
    packet_bundle = {"df": pd.DataFrame([{"Packet no.": 1, "Data": b"aa"}]), "missing": []}

    with pytest.raises(ValueError, match="Unsupported packet data type: abc"):
        process.build_decodable_from_group("abc0000000000000", packet_bundle)


def test_build_decodable_from_group_uses_decoder_config(monkeypatch):
    config = SimpleNamespace(decode_unit=1, sync_code=b"", sync_code_offset=0)
    packet_bundle = {"df": pd.DataFrame([{"Packet no.": 1, "Data": b"a", "Datetime": "ts"}]), "missing": []}

    monkeypatch.setitem(process.DECODER_REGISTRY, "001", config)
    monkeypatch.setattr(process, "build_decodable_df", lambda df, missing, cfg: pd.DataFrame([{"cfg": cfg}]))

    result = process.build_decodable_from_group("0010000000000000", packet_bundle)

    assert result.iloc[0]["cfg"] is config


def test_extract_data_type():
    assert process.extract_data_type("1101011001000101") == "110"
