import sys, re, math
z=1.959963984540054
def w(k,n):
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d; return c-h,c+h
L=open(sys.argv[1]).read().split('\n')
print('== table lines 45-65')
for i in range(44,65):
    c=[x.strip() for x in L[i].strip('|').split('|')]
    k=int(c[1].replace(',','')); n=int(c[2].replace(',',''))
    lo,hi=w(k,n); pr=f"{100*k/n:.4f}%"; iv=f"{100*lo:.4f}% to {100*hi:.4f}%"
    ok = (pr==c[3]) and (iv==c[4])
    print(i+1, c[0], k, n, 'pub',c[3],c[4],'| rec',pr,iv, 'OK' if ok else 'DIFF')
print('== text "k of n (x%; Wilson a% to b%)" and "k/n (Wilson a to b)"')
pat=re.compile(r'([\d,]+) of ([\d,]+)\)? \(([\d.]+)%; (?:Wilson )?([\d.]+)% to ([\d.]+)%')
pat2=re.compile(r'([\d,]+)/([\d,]+)[^()]{0,40}\((?:Wilson |[A-Z]{2}, )?([\d.]+) to ([\d.]+)\)')
pat3=re.compile(r'([\d,]+) of ([\d,]+)[^;()]{0,30}\(Wilson ([\d.]+)% to ([\d.]+)%\)')
for i,l in enumerate(L):
    for m in pat.finditer(l):
        k=int(m[1].replace(',','')); n=int(m[2].replace(',',''))
        lo,hi=w(k,n); dp=len(m[4].split('.')[1])
        rec=(round(100*k/n,len(m[3].split('.')[1])),round(100*lo,dp),round(100*hi,dp))
        pub=(float(m[3]),float(m[4]),float(m[5]))
        print(i+1,m.group(0)[:70],'| rec',rec,'OK' if rec==pub else 'DIFF')
    for m in pat2.finditer(l):
        k=int(m[1].replace(',','')); n=int(m[2].replace(',',''))
        lo,hi=w(k,n); dp=len(m[3].split('.')[1]); rec=(round(lo,dp),round(hi,dp)); pub=(float(m[3]),float(m[4]))
        print(i+1,m.group(0)[:70],'| rec',rec,'OK' if rec==pub else 'DIFF')
    for m in pat3.finditer(l):
        k=int(m[1].replace(',','')); n=int(m[2].replace(',',''))
        lo,hi=w(k,n); dp=len(m[3].split('.')[1]); rec=(round(100*lo,dp),round(100*hi,dp)); pub=(float(m[3]),float(m[4]))
        print(i+1,m.group(0)[:70],'| rec',rec,'OK' if rec==pub else 'DIFF')
