import pandas as pd

from pipeline.build_decodable_payloads import io


def test_write_decodable_df_writes_inside_explicit_output_dir(tmp_path, monkeypatch):
    df = pd.DataFrame([{"Data": "aa"}])
    monkeypatch.setattr(io, "get_filename_time", lambda id_time: "2026-03-12_1540")

    io.write_decodable_df(df, "1101011001000101", tmp_path)

    out_path = tmp_path / "step4_concat_data_ID_110_main_HK_log_2026-03-12_1540.csv"
    assert out_path.exists()
    assert "aa" in out_path.read_text()


def test_write_decodable_df_does_not_print_stdout(tmp_path, monkeypatch, capsys):
    df = pd.DataFrame([{"Data": "aa"}])
    monkeypatch.setattr(io, "get_filename_time", lambda id_time: "2026-03-12_1540")

    io.write_decodable_df(df, "1101011001000101", tmp_path)

    captured = capsys.readouterr()
    assert captured.out == ""


def test_write_df_writes_legacy_named_csv(tmp_path, monkeypatch):
    df = pd.DataFrame([{"Data": "aa"}])
    monkeypatch.setattr(io, "get_filename_time", lambda id_time: "2026-03-12_1540")

    io.write_df(df, "1101011001000101", tmp_path)

    out_path = tmp_path / "step4_concat_data_ID_110_1101011001000101_2026-03-12_1540.csv"
    assert out_path.exists()
    assert "aa" in out_path.read_text()


def test_write_concat_binaries_writes_raw_missing_and_decodable_files(tmp_path, monkeypatch):
    monkeypatch.setattr(io, "get_filename_time", lambda id_time: "2026-03-12_1540")
    monkeypatch.setattr(io, "get_decode_unit_from_key", lambda key: 4)
    monkeypatch.setattr(io, "fix_broken_bin", lambda binary, missing, decode_unit: binary[:4])

    result = io.write_concat_binaries(
        {"1101011001000101": {"payload": b"abcdef", "missing": [2, 3]}},
        tmp_path,
    )

    prefix = "step4_concat_data_ID_110_main_HK_log_2026-03-12_1540"
    assert (tmp_path / f"{prefix}_raw_filled.bin").read_bytes() == b"abcdef"
    assert (tmp_path / f"{prefix}_missing.csv").read_text() == "2,3"
    assert (tmp_path / f"{prefix}_decodable.bin").read_bytes() == b"abcd"
    assert result == b"abcd"


def test_extract_decodable_packet_is_currently_noop_placeholder():
    assert io.extract_decodable_packet(b"abc", missing=[]) is None
