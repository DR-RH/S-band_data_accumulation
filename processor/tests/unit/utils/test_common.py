from pipeline.utils.common import get_save_directory_name


def test_get_save_directory_name_removes_txt_suffix_from_basename():
    assert get_save_directory_name("/tmp/all_tlm.txt") == "all_tlm"


def test_get_save_directory_name_leaves_non_txt_basename_unchanged():
    assert get_save_directory_name("/tmp/all_tlm.csv") == "all_tlm.csv"
