import gzip, json, sys, collections
R=sys.argv[1]
rule=collections.Counter(); field_rule=collections.Counter(); rec_by_rule=collections.defaultdict(set)
cells=collections.Counter(); prefix=collections.Counter(); old_by_rule=collections.defaultdict(collections.Counter)
rows=[]
with gzip.open(R+'/patches_us.jsonl.gz','rt') as f:
    hdr=json.loads(f.readline())
    for line in f:
        p=json.loads(line)
        r=p['rule']; rule[r]+=1; field_rule[(r,p['field'])]+=1
        rec_by_rule[r].add(p['record_id']); cells[(p['record_id'],p['field'])]+=1
        prefix[p['record_id'].split(':')[0]]+=1
        if r!='val:hidden_chars': old_by_rule[r][str(p['old'])[:30]]+=1
        if not r.startswith('val:'): rows.append(p)
print('header',hdr)
print('n patches',sum(rule.values()))
print('by rule',dict(rule))
print('record prefixes',dict(prefix))
for k,v in sorted(field_rule.items()): print('  ',k,v)
for r,s in rec_by_rule.items(): print('records touched',r,len(s))
val=rec_by_rule['val:placeholder']|rec_by_rule['val:mojibake']
print('records val-level (placeholder|mojibake)',len(val))
allv=set().union(*[s for r,s in rec_by_rule.items()])
print('records any patch', len(allv))
nonval=set().union(*[s for r,s in rec_by_rule.items() if not r.startswith('val:')]) if any(not r.startswith('val:') for r in rec_by_rule) else set()
print('records non-val rules',len(nonval), 'union val-level+nonval', len(val|nonval))
print('records hidden only',len(rec_by_rule['val:hidden_chars']))
print('dup cells (record,field) with >1 patch', sum(1 for c in cells.values() if c>1))
for r,c in old_by_rule.items(): print(r, c.most_common(15))
print('nonval examples'); [print(json.dumps(x)[:400]) for x in rows[:4]]
json.dump({'n':sum(rule.values()),'by_rule':dict(rule),'records_by_rule':{r:len(s) for r,s in rec_by_rule.items()},'val_level_records':len(val),'val_plus_nonval_records':len(val|nonval),'dup_cells':sum(1 for c in cells.values() if c>1)},open(sys.argv[2],'w'),indent=1)
