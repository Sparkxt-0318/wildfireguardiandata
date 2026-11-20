"""Apply and revert patches on a string table (pandas), and write it deterministically.

Tables are all-string frames (empty cell = ''). `core.missing()` as `old` means the cell was empty (or the column absent);
as `new` it means the cell becomes empty. Input tables are never modified; apply returns a new frame.
"""
from __future__ import annotations

import csv
import hashlib
import io
from pathlib import Path

import numpy as np
import pandas as pd

from ..core import Patch, PatchConflict


def _is_missing(v) -> bool:
    return isinstance(v, dict) and v.get("__missing__") is True or v is None


def _cell(v) -> str:
    return "" if _is_missing(v) else str(v)


def apply_frame(df: pd.DataFrame, patches, id_col: str, strict: bool = True) -> pd.DataFrame:
    out = df.copy()
    pos = pd.Series(np.arange(len(out)), index=out[id_col].astype(str).to_numpy())
    by_field: dict[str, list[Patch]] = {}
    for p in patches:
        by_field.setdefault(p.field, []).append(p)
    for field, ps in by_field.items():
        if field not in out.columns:
            out[field] = ""
        ids = pd.Index([str(p.record_id) for p in ps])
        try:
            idx = pos.reindex(ids)
        except Exception:
            raise
        if idx.isna().any():
            raise PatchConflict(f"unknown record ids in field {field}")
        idx = idx.to_numpy().astype(int)
        col = out[field].to_numpy(dtype=object).copy()
        if strict:
            cur = col[idx]
            want = np.array([_cell(p.old) for p in ps], dtype=object)
            bad = np.flatnonzero(cur != want)
            if len(bad):
                p = ps[bad[0]]
                raise PatchConflict(f"{p.record_id}.{field}: expected {_cell(p.old)!r}, found {cur[bad[0]]!r} ({len(bad)} conflicts)")
        col[idx] = [_cell(p.new) for p in ps]
        out[field] = col
    return out


def revert_frame(df: pd.DataFrame, patches, id_col: str, orig_columns, strict: bool = True) -> pd.DataFrame:
    inv = [Patch(p.record_id, p.field, p.new, p.old, p.rule, p.evidence, p.confidence) for p in reversed(list(patches))]
    out = apply_frame(df, inv, id_col, strict)
    return out[list(orig_columns)]


def to_csv_bytes(df: pd.DataFrame, encoding: str = "latin-1") -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    w.writerow(list(df.columns))
    w.writerows(df.astype(str).to_numpy().tolist())
    return buf.getvalue().encode(encoding)


def sha256_frame(df: pd.DataFrame, encoding: str = "latin-1") -> str:
    return hashlib.sha256(to_csv_bytes(df, encoding)).hexdigest()


def write_csv(df: pd.DataFrame, path, encoding: str = "latin-1") -> str:
    b = to_csv_bytes(df, encoding)
    Path(path).write_bytes(b)
    return hashlib.sha256(b).hexdigest()


def changed_cells(a: pd.DataFrame, b: pd.DataFrame, id_col: str) -> set:
    """Set of (record id, field) where two frames with the same ids differ (new columns count as changed where non-empty)."""
    assert (a[id_col].to_numpy() == b[id_col].to_numpy()).all()
    s = set()
    for c in b.columns:
        if c == id_col:
            continue
        if c not in a.columns:
            nz = np.flatnonzero(b[c].to_numpy(dtype=object) != "")
        else:
            nz = np.flatnonzero(a[c].to_numpy(dtype=object) != b[c].to_numpy(dtype=object))
        ids = b[id_col].to_numpy()
        s.update((str(ids[i]), c) for i in nz)
    return s
