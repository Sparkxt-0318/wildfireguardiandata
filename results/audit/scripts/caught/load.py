import pyarrow.parquet as pq, pandas as pd
D='<work>/rel_v01/x/caught-v0.1/caught-v0.1/'
def labels(cols=None):
    fs=[]
    for y in (2018,2019,2020):
        p=pq.ParquetFile(D+f'caught_labels_v0.1_{y}.parquet')
        c=cols or [n for n in p.schema_arrow.names if n!='geometry']
        t=p.read(columns=c).to_pandas(); t['_file_year']=y; fs.append(t)
    return pd.concat(fs, ignore_index=True)
