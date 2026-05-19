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


def test_process_decodable_df_stores_main_hk_rows_when_db_path_is_given(tmp_path, monkeypatch):
    input_df = pd.DataFrame([{"Packet no.": 1}])
    bundle = {"df": pd.DataFrame([{"Packet no.": 1}]), "missing": []}
    decodable_df = pd.DataFrame([{"Data": "aa"}])
    stored = []

    monkeypatch.setattr(process, "detect_missing_packet", lambda df: {"110000": bundle})
    monkeypatch.setattr(process, "build_decodable_from_group", lambda packet_id, packet_bundle: decodable_df)
    monkeypatch.setattr(process, "write_decodable_df", lambda df, packet_id, out_dir: None)
    monkeypatch.setattr(process, "store_main_hk_payloads", lambda db_path, packet_id, df, gse: stored.append((db_path, packet_id, df, gse)))

    process.process_decodable_df(input_df, tmp_path, tmp_path / "main_hk.sqlite", gse="Kyutech")

    assert stored == [(tmp_path / "main_hk.sqlite", "110000", decodable_df, "Kyutech")]


def test_process_decodable_df_does_not_store_non_main_hk_rows(tmp_path, monkeypatch):
    input_df = pd.DataFrame([{"Packet no.": 1}])
    bundle = {"df": pd.DataFrame([{"Packet no.": 1}]), "missing": []}
    stored = []

    monkeypatch.setattr(process, "detect_missing_packet", lambda df: {"001000": bundle})
    monkeypatch.setattr(process, "build_decodable_from_group", lambda packet_id, packet_bundle: pd.DataFrame([{"Data": "aa"}]))
    monkeypatch.setattr(process, "write_decodable_df", lambda df, packet_id, out_dir: None)
    monkeypatch.setattr(process, "store_main_hk_payloads", lambda db_path, packet_id, df, gse: stored.append((db_path, packet_id, df, gse)))

    process.process_decodable_df(input_df, tmp_path, tmp_path / "main_hk.sqlite")

    assert stored == []


def test_process_decodable_df_stores_adcs_rows_when_db_path_is_given(tmp_path, monkeypatch):
    input_df = pd.DataFrame([{"Packet no.": 1}])
    bundle = {"df": pd.DataFrame([{"Packet no.": 1}]), "missing": []}
    decodable_df = pd.DataFrame([{"Data": "aa"}])
    stored = []

    monkeypatch.setattr(process, "detect_missing_packet", lambda df: {"011000": bundle, "100000": bundle})
    monkeypatch.setattr(process, "build_decodable_from_group", lambda packet_id, packet_bundle: decodable_df)
    monkeypatch.setattr(process, "write_decodable_df", lambda df, packet_id, out_dir: None)
    monkeypatch.setattr(process, "store_adcs_hk_payloads", lambda db_path, packet_id, df, gse: stored.append((db_path, packet_id, df, gse)))
    monkeypatch.setattr(process, "store_main_hk_payloads", lambda db_path, packet_id, df, gse: None)

    process.process_decodable_df(input_df, tmp_path, tmp_path / "hk.sqlite", gse="ISAS")

    assert stored == [
        (tmp_path / "hk.sqlite", "011000", decodable_df, "ISAS"),
        (tmp_path / "hk.sqlite", "100000", decodable_df, "ISAS"),
    ]


def test_process_decodable_df_uploads_rows_when_db_server_url_is_given(tmp_path, monkeypatch):
    input_df = pd.DataFrame([{"Packet no.": 1}])
    bundle = {"df": pd.DataFrame([{"Packet no.": 1}]), "missing": []}
    decodable_df = pd.DataFrame([{"Data": "aa"}])
    uploaded = []

    monkeypatch.setattr(process, "detect_missing_packet", lambda df: {"110000": bundle, "011000": bundle})
    monkeypatch.setattr(process, "build_decodable_from_group", lambda packet_id, packet_bundle: decodable_df)
    monkeypatch.setattr(process, "write_decodable_df", lambda df, packet_id, out_dir: None)
    monkeypatch.setattr(process, "upload_main_hk_payloads", lambda server_url, packet_id, df, gse: uploaded.append((server_url, packet_id, df, gse)))
    monkeypatch.setattr(process, "upload_adcs_hk_payloads", lambda server_url, packet_id, df, gse: uploaded.append((server_url, packet_id, df, gse)))

    process.process_decodable_df(input_df, tmp_path, db_server_url="http://127.0.0.1:8000", gse="Kyutech")

    assert uploaded == [
        ("http://127.0.0.1:8000", "110000", decodable_df, "Kyutech"),
        ("http://127.0.0.1:8000", "011000", decodable_df, "Kyutech"),
    ]


def test_process_decodable_df_queues_upload_when_server_connection_fails(tmp_path, monkeypatch):
    input_df = pd.DataFrame([{"Packet no.": 1}])
    bundle = {"df": pd.DataFrame([{"Packet no.": 1}]), "missing": []}
    decodable_df = pd.DataFrame([{"Data": "aa"}])
    queued = []

    monkeypatch.setattr(process, "detect_missing_packet", lambda df: {"011000": bundle})
    monkeypatch.setattr(process, "build_decodable_from_group", lambda packet_id, packet_bundle: decodable_df)
    monkeypatch.setattr(process, "write_decodable_df", lambda df, packet_id, out_dir: None)

    def fail_upload(server_url, packet_id, df, gse):
        raise process.UploadConnectionError("server down")

    monkeypatch.setattr(process, "upload_adcs_hk_payloads", fail_upload)
    monkeypatch.setattr(process, "enqueue_upload", lambda queue_dir, endpoint, payload, reason: queued.append((queue_dir, endpoint, payload, reason)))

    process.process_decodable_df(
        input_df,
        tmp_path,
        db_server_url="http://127.0.0.1:8000",
        pending_upload_dir=tmp_path / "pending",
        gse="ISAS",
    )

    assert queued == [
        (
            tmp_path / "pending",
            "/payloads/adcs-hk",
            {"packet_id": "011000", "gse": "ISAS", "rows": [{"Data": "aa"}]},
            "server down",
        )
    ]


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
