"""Loop of the live service: process every CONUS cycle, write, sign and commit one record per cycle."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from .live import LiveService, iso, record_path, slot_times, write_record

LATENCY_S = 200          # files reach S3 about 3 min after scan start
MAX_WAIT_S = 600         # after this, a cycle is recorded with what is there (gap record if frames are missing)


def sh(cmd, cwd=None, check=True):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed: {r.stderr[-500:]}")
    return r


def sign(path: Path) -> bool:
    b = path.with_suffix(".sigstore.json")
    r = sh([sys.executable, "-m", "sigstore", "sign", "--bundle", str(b), str(path)], check=False)
    return r.returncode == 0 and b.is_file()


def commit(repo: Path, paths, msg):
    sh(["git", "add", "--"] + [str(p) for p in paths], cwd=repo)
    if sh(["git", "diff", "--cached", "--quiet"], cwd=repo, check=False).returncode == 0:
        return
    sh(["git", "commit", "-q", "-m", msg], cwd=repo)
    for i in range(5):
        if sh(["git", "push", "-q", "origin", "HEAD:live-log"], cwd=repo, check=False).returncode == 0:
            return
        sh(["git", "pull", "-q", "--rebase", "origin", "live-log"], cwd=repo, check=False)
        time.sleep(5 * (i + 1))
    raise RuntimeError("push to live-log failed")


def run(log_repo: Path, until: float, publish: bool, cache: Path, region="us", max_catchup_h=6.0, sign_records=True):
    log_dir = log_repo / "live" / "log"
    state_f = log_repo / "live" / "state" / f"state_{region}.npz"
    svc = LiveService(region, log_dir=log_dir, cache_dir=cache)
    resumed = svc.load_state(state_f)
    now = time.time()
    start = (svc.last_slot + 300) if (resumed and svc.last_slot and now - svc.last_slot < max_catchup_h * 3600) \
        else slot_times(now - LATENCY_S - 300, now)[-1]
    print(f"live: resumed={resumed} first slot {iso(start)} until {iso(until)}", flush=True)
    t = start
    n = 0
    while t < until:
        due = t + LATENCY_S
        if time.time() < due:
            time.sleep(due - time.time())
        if record_path(log_dir, t).exists():       # already written by a predecessor
            t += 300
            continue
        wait = max(0, int(t + MAX_WAIT_S - time.time()))
        try:
            rec = svc.cycle(t, wait_s=wait)
        except Exception as e:  # noqa: BLE001 — a failed cycle is recorded, never skipped
            rec = {"schema": "firewitness.live.record/1", "cycle_scan_start": iso(t), "processed_at": iso(time.time()),
                   "error": f"{type(e).__name__}: {str(e)[:300]}", "candidates": [], "gap": True}
        rec["published_at"] = iso(time.time())
        rec["run"] = {"trigger": __import__("os").environ.get("LIVE_TRIGGER", "local"),
                      "run_id": __import__("os").environ.get("GITHUB_RUN_ID")}
        p = write_record(log_dir, rec, t)
        paths = [p]
        if publish and sign_records:
            if sign(p):
                paths.append(p.with_suffix(".sigstore.json"))
            else:
                u = p.with_suffix(".UNSIGNED")
                u.write_text("Sigstore signing failed for this record.\n")
                paths.append(u)
        svc.save_state(state_f)
        n += 1
        if publish:
            if n % 6 == 0:
                paths.append(state_f)
            commit(log_repo, paths, f"live record {p.name} ({len(rec.get('candidates', []))} candidates)")
        if publish and n % 12 == 1:
            try:
                from .reconcile import reconcile
                rr = reconcile(log_repo)
                if rr.get("file"):
                    commit(log_repo, [Path(rr["file"])], "live reconciliation (records 24-72 h old)")
            except Exception as e:  # noqa: BLE001
                print("reconcile failed:", type(e).__name__, str(e)[:200], flush=True)
        print(f"{iso(t)} candidates={len(rec.get('candidates', []))} proc={rec.get('processing_s')}s "
              f"{'ERROR ' + rec['error'] if 'error' in rec else ''}", flush=True)
        t += 300
    svc.save_state(state_f)
    if publish:
        commit(log_repo, [state_f], "live state handoff")
    return n
