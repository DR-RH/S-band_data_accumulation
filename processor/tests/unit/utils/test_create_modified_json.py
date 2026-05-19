from pipeline.utils.create_modified_json import add_numeric


def test_add_numeric_offsets_bit_range_bounds():
    assert add_numeric("8:15", 80) == "88:95"
