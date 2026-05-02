import numpy as np

def _break_packets(df):
    # number_of_list = len(df)
    rand_vals = np.random.rand(len(df))
    df = df[rand_vals > 0.2]

    return df