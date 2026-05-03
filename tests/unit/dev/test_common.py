import pickle
from pathlib import Path

import pandas as pd

from dev._common import artifact_name, infer_gse, intermediate_dir, read_bytes, read_dataframe, resolve_gse


def test_infer_gse_uses_kyutech_for_rx_com_names():
    assert infer_gse("all_tlm_in_RX_COM_COM7_20260312_153552.txt") == "Kyutech"
    assert infer_gse("MAIN_EXE_LOG_RX_GSE_TCP.txt") == "ISAS"


def test_resolve_gse_uses_auto_or_explicit_value():
    assert resolve_gse("auto", "RX_COM_sample") == "Kyutech"
    assert resolve_gse("ISAS", "RX_COM_sample") == "ISAS"


def test_artifact_name_prefers_explicit_name_or_path_stem():
    assert artifact_name(Path("/tmp/sample.txt")) == "sample"
    assert artifact_name(Path("/tmp/sample.txt"), "custom") == "custom"


def test_intermediate_dir_points_to_project_data_folder():
    path = intermediate_dir("sample")

    assert path.name == "sample"
    assert path.parent.name == "intermediate_output"


def test_read_bytes_reads_file_contents(tmp_path):
    path = tmp_path / "data.bin"
    path.write_bytes(b"abc")

    assert read_bytes(path) == b"abc"


def test_read_dataframe_supports_csv_and_pickle(tmp_path):
    df = pd.DataFrame({"a": [1, 2]})
    csv_path = tmp_path / "data.csv"
    pickle_path = tmp_path / "data.pickle"
    df.to_csv(csv_path, index=False)
    with pickle_path.open("wb") as f:
        pickle.dump(df, f)

    assert read_dataframe(csv_path).equals(df)
    assert read_dataframe(pickle_path).equals(df)
