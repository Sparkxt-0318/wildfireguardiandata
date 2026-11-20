"""Input hashing: every run records the hash of every input so a result can be tied to exact bytes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: str | Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def hash_inputs(paths: Iterable[str | Path]) -> dict[str, dict[str, Any]]:
    """{path: {sha256, bytes}} for each existing file; directories are hashed over sorted members."""
    out: dict[str, dict[str, Any]] = {}
    for p in paths:
        p = Path(p)
        if p.is_dir():
            h = hashlib.sha256()
            n = 0
            for q in sorted(x for x in p.rglob("*") if x.is_file()):
                h.update(str(q.relative_to(p)).encode())
                h.update(sha256_file(q).encode())
                n += q.stat().st_size
            out[str(p)] = {"sha256": h.hexdigest(), "bytes": n}
        else:
            out[str(p)] = {"sha256": sha256_file(p), "bytes": p.stat().st_size}
    return out


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def hash_obj(obj: Any) -> str:
    return sha256_bytes(canonical_json(obj).encode("utf-8"))
