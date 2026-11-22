import gzip, json, sys, collections, math
R=sys.argv[1]; s=collections.defaultdict(set)
with gzip.open(R+'/patches_us.jsonl.gz','rt') as f:
    f.readline()
    for line in f:
        p=json.loads(line); s[p['rule']].add(p['record_id'])
H,P,M,D=s['val:hidden_chars'],s['val:placeholder'],s['val:mojibake'],s['dup:fs_link']
print('H&M',len(H&M),'H|M',len(H|M),'P&D',len(P&D),'P|D',len(P|D),'P&M',len(P&M),'M&D',len(M&D),'P|D|M',len(P|D|M))
N=2661383
def w(k,n,z=1.96):
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d; return '%.4f%% to %.4f%%'%(100*(c-h),100*(c+h))
for k in [len(H),len(H|M),len(P|D|M),len(P|M)]: print(k,'%.4f%%'%(100*k/N),w(k,N))
