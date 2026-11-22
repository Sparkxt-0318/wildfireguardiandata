import sys, json, gzip, re, numpy as np, pandas as pd
R=sys.argv[1]; out={}
F=pd.read_parquet(R+'/fires_us.parquet'); X=pd.read_parquet(R+'/crosswalk_us.parquet'); P=pd.read_parquet(R+'/complex_parents_us.parquet')
out['fires_rows']=len(F); out['perm_unique']=int(F.perm_id.nunique()); out['fid_unique']=int(F.fid.nunique())
print('fires',len(F),'unique perm',F.perm_id.nunique(),'unique fid',F.fid.nunique())
print(F.isna().sum().to_dict())
print('year range',F.year.min(),F.year.max()); print(F.year.value_counts().sort_index().tail(5).to_dict())
out['fires_year_lt_2024']=int((F.year<2024).sum()); out['fires_year_2024']=int((F.year==2024).sum())
# format
pat=re.compile(r'^FW-(\d{8})-(\d{4})(\d{4})-(\d{2,})$')
m=F.perm_id.str.extract(r'^FW-(\d{8})-(\d{8}|XXXXXXXX)-(\d{2,})$')
print('format ok',m[0].notna().sum(),'bad',m[0].isna().sum()); out['format_ok']=int(m[0].notna().sum())
# date check
d=pd.to_datetime(F.day,unit='D',errors='coerce').dt.strftime('%Y%m%d').fillna('00000000')
out['date_mismatch']=int((d!=m[0]).sum()); print('date mismatch',out['date_mismatch'])
# year vs date
out['year_vs_date_mismatch']=int((m[0].str[:4].astype(int)!=F.year).sum()); print('year != id year',out['year_vs_date_mismatch'])
ok=np.isfinite(F.lat)&np.isfinite(F.lon)
r=np.floor((F.lat+90)*10).astype('Int64'); c=np.floor((F.lon+180)*10).astype('Int64')
cell=np.where(ok, r.astype(str).str.zfill(4)+c.astype(str).str.zfill(4), 'XXXXXXXX')
out['cell_mismatch']=int((cell!=m[1]).sum()); print('cell mismatch',out['cell_mismatch'], 'XXXX cells',int((m[1]=='XXXXXXXX').sum()))
# ordinal: rank by acres desc then key 'fod:<fid>' string asc
G=F.assign(dstr=m[0],cell=m[1],ordn=m[2].astype(int),key='fod:'+F.fid.astype(str))
G=G.sort_values(['dstr','cell','acres','key'],ascending=[True,True,False,True],na_position='last',kind='mergesort')
G['ord2']=G.groupby(['dstr','cell']).cumcount()+1
out['ordinal_mismatch']=int((G.ord2!=G.ordn).sum()); print('ordinal mismatch',out['ordinal_mismatch'],'max ordinal',G.ordn.max())
# crosswalk
print('xw rows',len(X)); print(X.source.value_counts().to_dict()); out['xw_by_source']=X.source.value_counts().to_dict()
fx=X[X.source=='fpa_fod']
out['xw_fod_rows']=len(fx); out['xw_fod_unique_src']=int(fx.source_id.nunique())
print('fod src unique',fx.source_id.nunique(),'perm in fires',fx.perm_id.isin(F.perm_id).all())
k=fx.groupby('perm_id').size(); out['perm_with_multi_fod']=int((k>1).sum()); out['merged_extra_records']=int((k-1).sum())
print('perm ids with >1 fod record',(k>1).sum(),'extra records',(k-1).sum(), 'cluster size dist',k.value_counts().to_dict())
print('fires not in xw', (~F.perm_id.isin(fx.perm_id)).sum())
# fires fid -> own record maps to same perm
own=fx.merge(F[['perm_id','fid']].assign(source_id=F.fid.astype(str)),on=['source_id'],how='inner',suffixes=('','_f'))
print('keeper fid maps to own perm', (own.perm_id==own.perm_id_f).all(), len(own))
# patches dup
dup=[];
with gzip.open(R+'/patches_us.jsonl.gz','rt') as f:
    f.readline()
    for line in f:
        if '"dup:fs_link"' in line:
            p=json.loads(line); dup.append((p['record_id'][4:],p['new'][4:],p['evidence']['cluster_size']))
D=pd.DataFrame(dup,columns=['rec','keeper','cs'])
pm=fx.set_index('source_id').perm_id
D['p_rec']=pm.reindex(D.rec).to_numpy(); D['p_keep']=pm.reindex(D.keeper).to_numpy()
out['dup_patch_consistent']=int((D.p_rec==D.p_keep).sum()); print('dup patches consistent with xw',(D.p_rec==D.p_keep).sum(),'of',len(D))
print('dup recs are not fires', (~D.rec.astype(int).isin(F.fid)).sum(), 'keepers are fires', D.keeper.astype(int).isin(F.fid).sum())
print('cluster size dist',D.cs.value_counts().to_dict())
# other sources
for s in ['mtbs','ics209plus']:
    xs=X[X.source==s]; g=xs.groupby('source_id').perm_id.nunique()
    print(s,'rows',len(xs),'unique src',xs.source_id.nunique(),'src ids with >=2 fires',(g>=2).sum(),'perm ids',xs.perm_id.nunique(),'dup rows',xs.duplicated().sum())
    out[s+'_src_multi']=int((g>=2).sum()); out[s+'_rows']=len(xs); out[s+'_unique_src']=int(xs.source_id.nunique())
# parents
print('parents',len(P),P.source.value_counts().to_dict(),'split',P.split.sum(),'unique parent',P.parent_id.nunique())
print(P[P.split].to_string())
chk=((P.km>25)|(P.days>45))==P.split; print('split rule consistent',chk.all())
out['parents']=len(P); out['parents_by_source']=P.source.value_counts().to_dict(); out['split']=int(P.split.sum())
# parent n_children vs crosswalk
for s in ['mtbs','ics209plus']:
    xs=X[X.source==s]; g=xs.groupby('source_id').perm_id.nunique()
    pp=P[P.source==s].set_index('src_id')
    print(s,'parents',len(pp),'xw multi',(g>=2).sum(),'n_children match', (g.reindex(pp.index)==pp.n_children).sum())
# coverage
big=F[F.acres>=1000]; out['fires_ge1000']=len(big)
mt=set(X[X.source=='mtbs'].perm_id); out['fires_ge1000_mtbs']=int(big.perm_id.isin(mt).sum())
print('fires >=1000 acres',len(big),'linked mtbs',out['fires_ge1000_mtbs'])
# by records (keepers+merged): fod records >=1000 acres not available (acres only for keepers)
b2=big[(big.year>=2016)&(big.year<=2023)]; out['ge1000_2016_2023_no_mtbs']=int((~b2.perm_id.isin(mt)).sum()); print('2016-2023 >=1000 no mtbs', out['ge1000_2016_2023_no_mtbs'])
json.dump(out,open(sys.argv[2],'w'),indent=1,default=int)
