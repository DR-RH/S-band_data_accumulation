from typing import Dict
import pandas as pd


def concat_payloads_by_key(
    df: pd.DataFrame,
    group_key: str,
    data_column: str,
) -> Dict[int, bytes]:
    """
    Group dataframe by group_key and concat bytes in data_column.
    """

    result = {}

    for key, group in df.groupby(group_key, sort=True):
        payloads = group[data_column]

        if not all(isinstance(x, (bytes, bytearray)) for x in payloads):
            raise TypeError("data_column must contain bytes")

        result[key] = b"".join(payloads.tolist())

    return result
