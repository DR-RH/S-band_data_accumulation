from pathlib import Path
import pickle
import pandas as pd


def write_step3_output(df: pd.DataFrame, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    df.to_csv(out_dir / "step3_decode_ready.csv", index=False)
    with open(out_dir / "step3_decode_ready.pickle", "wb") as f:
        pickle.dump(df, f)
