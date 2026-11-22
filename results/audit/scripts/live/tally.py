import re, sys, collections
c = collections.Counter(); rows = collections.Counter()
for ln in open(sys.argv[1]):
    if not ln.startswith("| ") or ln.startswith("| line") : continue
    cols = [x.strip() for x in ln.strip().strip("|").split("|")]
    if len(cols) < 6: continue
    st = cols[4]
    if st.startswith("("): continue
    last = cols[5]
    m = re.search(r"Total counted CANNOT here: (\d+)", last) or re.search(r"(\d+) numbers?", last) or re.search(r"\((\d+)\)", last)
    k = int(m.group(1)) if m else 1
    if k > 1: print(k, st, cols[0], cols[1][:40])
    key = st.split(" (")[0].replace("**", "")
    c[key] += k; rows[key] += 1
print(dict(c), "rows", dict(rows), "total", sum(c.values()))
