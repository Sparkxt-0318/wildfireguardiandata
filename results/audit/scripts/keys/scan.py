import re, subprocess, sys, collections
repo = sys.argv[1]
P = {
 "huggingface": rb"\bhf_[A-Za-z0-9]{30,}",
 "github": rb"\b(?:ghp|gho|ghs|ghu|ghr)_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}",
 "jwt": rb"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
 "aws_akid": rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b",
 "google_api": rb"\bAIza[0-9A-Za-z_-]{35}\b",
 "slack": rb"\bxox[abprs]-[A-Za-z0-9-]{10,}",
 "private_key": rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY",
 "anthropic/openai": rb"\bsk-(?:ant-)?[A-Za-z0-9_-]{20,}",
 "earthdata_token_assign": rb"(?i)earthdata[_ -]?token\s*[=:]\s*['\"]?[A-Za-z0-9._-]{20,}",
 "generic_secret_assign": rb"(?i)\b[A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD)\s*[=:]\s*['\"]?[A-Za-z0-9+/=_%.-]{16,}",
 "firms_32hex_assign": rb"(?i)(?:firms|map)_?(?:map_)?key\s*[=:]\s*['\"]?[0-9a-f]{32}",
 "data_go_kr_like": rb"[A-Za-z0-9%]{60,}(?:%3D|==)",
 "bearer": rb"(?i)authorization:\s*bearer\s+[A-Za-z0-9._-]{20,}",
 "url_cred": rb"https?://[^/\s:@]+:[^/\s:@]{6,}@",
}
R = {k: re.compile(v) for k, v in P.items()}
objs = subprocess.run(["git","-C",repo,"rev-list","--all","--objects"],capture_output=True).stdout.decode().splitlines()
paths = {}
for l in objs:
    parts = l.split(" ",1)
    if len(parts)==2: paths.setdefault(parts[0], parts[1])
# keep blobs
check = subprocess.run(["git","-C",repo,"cat-file","--batch-check"],input="\n".join(paths).encode(),capture_output=True).stdout.decode().splitlines()
blobs=[l.split()[0] for l in check if l.split()[1]=="blob"]
print("blobs", len(blobs), file=sys.stderr)
hits = collections.defaultdict(set)
p = subprocess.Popen(["git","-C",repo,"cat-file","--batch"],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
for b in blobs:
    p.stdin.write((b+"\n").encode()); p.stdin.flush()
    hdr = p.stdout.readline().split()
    n = int(hdr[2]); data = p.stdout.read(n); p.stdout.read(1)
    for k, rx in R.items():
        for m in rx.finditer(data):
            s = m.group(0)
            # redact: show first 6 chars + length
            hits[(k, paths[b])].add(s[:12].decode('latin-1')+"…(len %d)"%len(s))
for (k, path), v in sorted(hits.items()):
    vs = sorted(v)
    print(f"{k}\t{path}\t{len(vs)}\t{'; '.join(vs[:4])}")
