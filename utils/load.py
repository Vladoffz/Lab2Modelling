
import pandas as pd


def load_csv_file(data: dict, path: str, file_name: str):

    df = pd.DataFrame.from_dict(data)
    df.T.to_csv(path + file_name + ".csv")
