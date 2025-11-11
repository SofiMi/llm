import pandas as pd
import polars as pl
import re
import os

datasets = ["hf://datasets/edgar9810/dating_parsed/data/train-00000-of-00001.parquet"]
for dataset in datasets:
	df = pl.read_parquet(dataset)
	match = re.search(r'datasets/([^/]+/[^/]+)', dataset)
	name = match.group(1).replace('/', '_')
	if os.path.exists(name):
		continue
	df.write_csv(name + '.csv')


