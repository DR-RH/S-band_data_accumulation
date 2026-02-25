import pytest
from pathlib import Path

from pipeline.step5_decode.flow import run


def test_run_collects_step4_files(tmp_path: Path):
    # create dummy files
    (tmp_path / "step4_a.bin").touch()
    (tmp_path / "step4_b.bin").touch()
    (tmp_path / "other_file.bin").touch()

    result = run(str(tmp_path))

    # only step4_* should be returned
    assert len(result) == 2
    assert all(p.name.startswith("step4_") for p in result)

    # sorted order guarantee
    assert [p.name for p in result] == ["step4_a.bin", "step4_b.bin"]


def test_run_returns_empty_when_no_matching_files(tmp_path: Path):
    (tmp_path / "random.bin").touch()

    result = run(str(tmp_path))
    print(result)
    assert result == []


def test_run_raises_if_folder_not_exists():
    with pytest.raises(FileNotFoundError):
        run("non_existent_folder")