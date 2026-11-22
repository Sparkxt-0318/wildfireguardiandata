import gzip, json, sys, pandas as pd
R=sys.argv[1]
F=pd.read_parquet(R+'/fires_us.parquet'); X=pd.read_parquet(R+'/crosswalk_us.parquet')
print('state ok lowercase',(F.state=='ok').sum(),'OK',(F.state=='OK').sum())
pos=F[F.lon>0]; print('lon>0 by state',pos.state.value_counts().head(10).to_dict())
print('lat<18 or >72 non-territory', ((F.lat<18)&~F.state.isin(['PR','VI','GU','HI'])).sum())
dup=[]
with gzip.open(R+'/patches_us.jsonl.gz','rt') as f:
    f.readline()
    for line in f:
        if '"dup:fs_link"' in line:
            p=json.loads(line); dup.append((p['record_id'],p['new'],p['evidence']['cluster_size']))
D=pd.DataFrame(dup,columns=['rec','keep','cs'])
g=D.groupby('keep').agg(n=('rec','size'),cs=('cs','max'))
print('patches per keeper vs evidence cluster_size'); print(pd.crosstab(g.n+1,g.cs))
