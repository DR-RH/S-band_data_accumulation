from pipeline.utils.create_modified_json_byte import add_numeric


def test_add_numeric_offsets_byte_range_bounds():
    assert add_numeric("3:10", 18) == "21:28"
