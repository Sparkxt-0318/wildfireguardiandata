import sys, numpy as np, pandas as pd
R=sys.argv[1]
F=pd.read_parquet(R+'/fires_us.parquet'); X=pd.read_parquet(R+'/crosswalk_us.parquet')
print(F[F.perm_id.str[3:7].astype(int)!=F.year].to_string())
fx=X[X.source=='fpa_fod']
A=F.set_index('perm_id').acres
fx=fx.assign(acres=A.reindex(fx.perm_id).to_numpy())
mt=set(X[X.source=='mtbs'].perm_id)
b=fx[fx.acres>=1000]
print('FOD records whose fire >=1000 acres',len(b),'of which fire linked mtbs',b.perm_id.isin(mt).sum())
# merged records -> perm year?
print('fires with acres exactly >=1000 by > 1000', (F.acres>1000).sum())
# day-of-year vs year for merged clusters: day min may cross year
print('state values',F.state.nunique(), sorted(F.state.unique())[:60])
print('acres<=0',(F.acres<=0).sum(),'lat range',F.lat.min(),F.lat.max(),'lon range',F.lon.min(),F.lon.max())
print('lon>0',(F.lon>0).sum())
