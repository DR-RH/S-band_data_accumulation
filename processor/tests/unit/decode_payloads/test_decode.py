import pandas as pd

from pipeline.decode_payloads.decode import _collect_step4_files, read_decodable_data, run


def test_run_writes_decoded_files_to_explicit_output_dir(tmp_path):
    input_dir = tmp_path / "intermediate"
    output_dir = tmp_path / "decoded"
    input_dir.mkdir()
    step4_file = input_dir / "step4_concat_data_ID_000_unassigned_2026-01-01.csv"
    pd.DataFrame({"Data": ["0a", "ff"]}).to_csv(step4_file, index=False)

    written_paths = run(input_dir, output_dir)

    expected_path = output_dir / f"decoded_{step4_file.name}"
    assert written_paths == [expected_path]
    decoded_df = pd.read_csv(expected_path)
    assert decoded_df["hex"].tolist() == ["0aff"]


def test_run_moves_lost_units_report_to_decoded_output_dir(tmp_path):
    input_dir = tmp_path / "intermediate"
    output_dir = tmp_path / "decoded"
    input_dir.mkdir()
    step4_file = input_dir / "step4_concat_data_ID_000_unassigned_2026-01-01.csv"
    report_file = input_dir / "step4_concat_data_ID_000_unassigned_2026-01-01_missing.csv"
    pd.DataFrame({"Data": ["0a"]}).to_csv(step4_file, index=False)
    pd.DataFrame({"lost_unit_index": [1], "reason": ["missing_prefix_before_sync"]}).to_csv(report_file, index=False)

    run(input_dir, output_dir)

    expected_report = output_dir / f"decoded_{report_file.name}"
    assert expected_report.exists()
    assert not report_file.exists()
    report = pd.read_csv(expected_report)
    assert report.to_dict("records") == [
        {"lost_unit_index": 1, "reason": "missing_prefix_before_sync"}
    ]


def test_collect_step4_files_returns_sorted_step4_csvs_only(tmp_path):
    first = tmp_path / "step4_concat_data_ID_001_a.csv"
    second = tmp_path / "step4_concat_data_ID_110_b.csv"
    ignored = tmp_path / "step3_decode_ready.csv"
    missing = tmp_path / "step4_concat_data_ID_001_a_missing.csv"
    second.write_text("", encoding="utf-8")
    ignored.write_text("", encoding="utf-8")
    missing.write_text("", encoding="utf-8")
    first.write_text("", encoding="utf-8")

    assert _collect_step4_files(tmp_path) == [first, second]


def test_read_decodable_data_concatenates_hex_column(tmp_path):
    csv_path = tmp_path / "step4_concat_data_ID_000_unassigned.csv"
    pd.DataFrame({"Data": ["ca", "fe"]}).to_csv(csv_path, index=False)

    assert read_decodable_data(csv_path) == b"\xca\xfe"


def test_read_decodable_data_returns_empty_bytes_for_empty_file(tmp_path):
    csv_path = tmp_path / "step4_concat_data_ID_100_empty.csv"
    csv_path.write_text("", encoding="utf-8")

    assert read_decodable_data(csv_path) == b""


def test_run_skips_empty_decodable_file(tmp_path):
    input_dir = tmp_path / "intermediate"
    output_dir = tmp_path / "decoded"
    input_dir.mkdir()
    step4_file = input_dir / "step4_concat_data_ID_100_empty.csv"
    step4_file.write_text('""\n', encoding="utf-8")

    assert run(input_dir, output_dir) == []
