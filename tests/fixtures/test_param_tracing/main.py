import pandas as pd

def process_df(df):
    df.info()
    df.dropna()
    return df

all_df = pd.read_csv("data.csv")
result = process_df(all_df)
result.head()
