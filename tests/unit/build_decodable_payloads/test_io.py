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
