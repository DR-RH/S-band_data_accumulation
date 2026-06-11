import pickle
from pathlib import Path

import pandas as pd

from dev._common import (
    DEFAULT_DB_PATH,
    DEFAULT_DB_SERVER_URL,
    PROCESSED_INPUT_DIR,
    UNPROCESSED_INPUT_DIR,
    artifact_name,
    decoded_output_dir,
    infer_gse,
    intermediate_dir,
    is_unprocessed_input,
    processed_input_path,
    read_bytes,
    read_dataframe,
    resolve_gse,
)


def test_infer_gse_uses_kyutech_for_rx_com_names():
    assert infer_gse("all_tlm_in_RX_COM_COM7_20260312_153552.txt") == "Kyutech"
    assert infer_gse("MAIN_EXE_LOG_RX_GSE_TCP.txt") == "ISAS"


def test_resolve_gse_uses_auto_or_explicit_value():
    assert resolve_gse("auto", "RX_COM_sample") == "Kyutech"
    assert resolve_gse("ISAS", "RX_COM_sample") == "ISAS"


def test_artifact_name_prefers_explicit_name_or_path_stem():
    assert artifact_name(Path("/tmp/sample.txt")) == "sample"
    assert artifact_name(Path("/tmp/sample.txt"), "custom") == "custom"


def test_intermediate_dir_points_to_project_output_folder():
    path = intermediate_dir("sample")

    assert path.name == "sample"
    assert path.parent.name == "intermediate"
    assert path.parent.parent.name == "output"


def test_output_and_input_paths_use_organized_layout():
    assert UNPROCESSED_INPUT_DIR.parts[-2:] == ("input", "unprocessed")
    assert PROCESSED_INPUT_DIR.parts[-2:] == ("input", "processed")
    assert intermediate_dir("sample").parts[-3:] == ("output", "intermediate", "sample")
    assert decoded_output_dir("sample").parts[-3:] == ("output", "decoded", "sample")
    assert DEFAULT_DB_PATH.parts[-3:] == ("output", "accumulated", "payloads.sqlite")
    assert DEFAULT_DB_SERVER_URL.startswith("http")


def test_processed_input_path_points_to_processed_folder():
    path = UNPROCESSED_INPUT_DIR / "sample.txt"

    assert processed_input_path(path) == PROCESSED_INPUT_DIR / "sample.txt"
    assert is_unprocessed_input(path)
    assert not is_unprocessed_input(PROCESSED_INPUT_DIR / "sample.txt")


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


def test_read_dataframe_preserves_packet_id_and_restores_byte_literals(tmp_path):
    csv_path = tmp_path / "step3.csv"
    pd.DataFrame(
        {
            "Packet ID": ["0101011001000101"],
            "Data": [repr(b"SUTELEMETRY 0 abc")],
            "CRC": [repr(b"\xce\xad")],
        }
    ).to_csv(csv_path, index=False)

    result = read_dataframe(csv_path)

    assert result.iloc[0]["Packet ID"] == "0101011001000101"
    assert result.iloc[0]["Data"] == b"SUTELEMETRY 0 abc"
    assert result.iloc[0]["CRC"] == b"\xce\xad"
