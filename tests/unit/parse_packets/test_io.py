import pickle

import pandas as pd

from pipeline.parse_packets.io import write_step3_output


def test_write_step3_output_writes_csv_and_pickle(tmp_path):
    df = pd.DataFrame([{"Packet no.": 1, "Data": b"abc"}])

    write_step3_output(df, tmp_path)

    csv_path = tmp_path / "step3_decode_ready.csv"
    pickle_path = tmp_path / "step3_decode_ready.pickle"
    assert csv_path.exists()
    assert pickle_path.exists()

    with pickle_path.open("rb") as f:
        loaded = pickle.load(f)
    pd.testing.assert_frame_equal(loaded, df)
