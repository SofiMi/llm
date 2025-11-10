import pandas as pd

df = pd.read_parquet("hf://datasets/edgar9810/dating_parsed/data/train-00000-of-00001.parquet")
df.to_csv('dating_parsed.csv')
print(df.head())
