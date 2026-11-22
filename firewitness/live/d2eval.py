"""D2 evaluation: one signed record per 5-min cycle (or signed gap record) for the 288 cycles
2026-11-21T00:21:18Z .. 2026-11-22T00:16:18Z on origin/live-log; frozen detector; no record edited after commit."""
import json, subprocess, sys
from datetime import datetime, timedelta, timezone
R = "origin/live-log"
def git(*a): return subprocess.check_output(["git", *a], text=True)
names = set(git("ls-tree", "-r", "--name-only", R, "live/").split())
t0 = datetime(2026, 11, 21, 0, 21, 18, tzinfo=timezone.utc)
cycles = [t0 + timedelta(minutes=5 * i) for i in range(288)]
FROZEN = "69081030f02d078cb61b119c2559cbf592252a78ec38a30f55d787012253cf8a"
rows, miss, unsigned, gaprec, notfrozen, errs, edited, lat, ncand, ncycles_cand = [], [], [], [], [], [], [], [], 0, 0
commits_per_file = {}
for line in git("log", R, "--name-only", "--format=@%H", "--", "live/log").splitlines():
    if line.startswith("@") or not line.strip(): continue
    commits_per_file[line] = commits_per_file.get(line, 0) + 1
for c in cycles:
    stem = c.strftime("%Y%m%dT%H%MZ")
    p = f"live/log/{c:%Y/%m/%d}/{stem}"
    js, sig = p + ".json", p + ".sigstore.json"
    if js not in names:
        alt = [n for n in names if n.startswith(p) and n.endswith(".json") and "sigstore" not in n]
        if not alt: miss.append(stem); continue
        js = alt[0]
    if sig not in names: unsigned.append(stem)
    r = json.loads(git("show", f"{R}:{js}"))
    if r.get("gap") or r.get("kind") == "gap": gaprec.append(stem)
    if not (r.get("detector", {}).get("frozen") and r["detector"].get("sha256") == FROZEN): notfrozen.append(stem)
    if "error" in r: errs.append((stem, r["error"][:80]))
    if commits_per_file.get(js, 0) != 1 or commits_per_file.get(sig, 0) not in (0, 1): edited.append((stem, commits_per_file.get(js)))
    pub = datetime.fromisoformat(r["published_at"].replace("Z", "+00:00"))
    scan = datetime.fromisoformat(r["cycle_scan_start"].replace("Z", "+00:00"))
    lat.append((pub - scan).total_seconds() / 60)
    nc = len(r.get("candidates", [])); ncand += nc; ncycles_cand += nc > 0
# cryptographic check of every Sigstore bundle against the relay workflow identity
import os, tempfile
vd = tempfile.mkdtemp()
files = []
for c in cycles:
    stem = c.strftime("%Y%m%dT%H%MZ"); p = f"live/log/{c:%Y/%m/%d}/{stem}"
    if p + ".json" in names and p + ".sigstore.json" in names:
        open(f"{vd}/{stem}.json", "w").write(git("show", f"{R}:{p}.json"))
        open(f"{vd}/{stem}.json.sigstore.json", "w").write(git("show", f"{R}:{p}.sigstore.json"))
        files.append(f"{stem}.json")
ver = subprocess.run([sys.executable, "-m", "sigstore", "verify", "identity", "--cert-identity",
                      "https://github.com/Sparkxt-0318/wildfireguardiandata/.github/workflows/live-relay.yml@refs/heads/main",
                      "--cert-oidc-issuer", "https://token.actions.githubusercontent.com", *files],
                     cwd=vd, capture_output=True, text=True)
n_ok = sum(1 for l in (ver.stdout + ver.stderr).splitlines() if l.startswith("OK:"))
bad_sig = [l for l in (ver.stdout + ver.stderr).splitlines() if l.strip() and not l.startswith("OK:")][:10]
lat.sort()
out = {"cycles_expected": 288, "records_present": 288 - len(miss), "missing": miss, "unsigned": unsigned,
       "gap_records": gaprec, "not_frozen": notfrozen, "records_with_error": errs, "edited_after_commit": edited,
       "latency_min_scan_to_publish": {"median": lat[len(lat)//2], "p95": lat[int(0.95*len(lat))-1], "max": lat[-1]} if lat else None,
       "sigstore_verified": [n_ok, len(files)], "sigstore_problems": bad_sig, "candidates_total": ncand, "cycles_with_candidates": ncycles_cand,
       "D2": "PASS" if not (miss or unsigned or notfrozen or edited) and n_ok == len(files) == 288 else "FAIL"}
print(json.dumps(out, indent=1, default=str))
if len(sys.argv) > 1: open(sys.argv[1], "w").write(json.dumps(out, indent=1, default=str) + "\n")
