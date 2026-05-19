import pandas as pd

from pipeline.parse_packets import main as parse_main


def test_parse_into_df_returns_dataframe(monkeypatch):
    expected = pd.DataFrame([{"Packet no.": 1}])

    monkeypatch.setattr(parse_main, "build_dataframe", lambda binary, gse: expected)

    result = parse_main.parse_into_df(b"packets", "ISAS")

    assert result is expected


def test_parse_into_df_writes_output_when_out_dir_is_given(tmp_path, monkeypatch):
    expected = pd.DataFrame([{"Packet no.": 1}])
    written = {}

    monkeypatch.setattr(parse_main, "build_dataframe", lambda binary, gse: expected)

    def fake_write_step3_output(df, out_dir):
        written["df"] = df
        written["out_dir"] = out_dir

    monkeypatch.setattr(parse_main, "write_step3_output", fake_write_step3_output)

    result = parse_main.parse_into_df(b"packets", "ISAS", tmp_path)

    assert result is expected
    assert written == {"df": expected, "out_dir": tmp_path}
