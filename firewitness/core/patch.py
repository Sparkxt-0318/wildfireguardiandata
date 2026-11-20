"""The patch format. Every change a cleaning tool makes is a Patch; nothing is overwritten.

A Patch = (record id, field, old value, new value, rule, evidence, confidence).
A PatchSet is an ordered, hash-chained list of patches with the hash of the input it was made from.
Applying never mutates its input; reverting restores the input exactly.
"""
from __future__ import annotations

import copy
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from .hashing import canonical_json, sha256_bytes, sha256_file

PATCH_FIELDS = ("record_id", "field", "old", "new", "rule", "evidence", "confidence")
_MISSING = {"__missing__": True}  # old value used when a field did not exist (insert); revert deletes it


@dataclass(frozen=True)
class Patch:
    record_id: str
    field: str
    old: Any
    new: Any
    rule: str
    evidence: Any = None  # dict / list / str: what independent evidence supports it
    confidence: float = 1.0

    def validate(self) -> None:
        if not str(self.record_id):
            raise ValueError("patch without record_id")
        if not self.field:
            raise ValueError("patch without field")
        if not self.rule:
            raise ValueError("patch without rule")
        if not (0.0 <= float(self.confidence) <= 1.0):
            raise ValueError("confidence outside [0,1]")
        if self.old == self.new:
            raise ValueError("no-op patch (old == new)")

    def to_dict(self) -> dict:
        d = asdict(self)
        d["record_id"] = str(d["record_id"])
        return d

    @staticmethod
    def from_dict(d: Mapping) -> "Patch":
        return Patch(**{k: d[k] for k in PATCH_FIELDS if k in d})

    def key(self) -> str:
        return sha256_bytes(canonical_json(self.to_dict()).encode())


class PatchSet:
    """Ordered patches with provenance: input hash, tool name, version."""

    def __init__(self, patches: Iterable[Patch] = (), input_sha256: str | None = None,
                 tool: str = "", meta: dict | None = None):
        self.patches: list[Patch] = list(patches)
        self.input_sha256 = input_sha256
        self.tool = tool
        self.meta = dict(meta or {})

    def add(self, patch: Patch) -> Patch:
        patch.validate()
        self.patches.append(patch)
        return patch

    def extend(self, patches: Iterable[Patch]) -> None:
        for p in patches:
            self.add(p)

    def __len__(self) -> int:
        return len(self.patches)

    def __iter__(self):
        return iter(self.patches)

    def chain_hash(self) -> str:
        h = ""
        for p in self.patches:
            h = sha256_bytes((h + p.key()).encode())
        return h

    # ---- storage (JSON lines; first line is a header) ----
    def write(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        head = {"_header": True, "tool": self.tool, "input_sha256": self.input_sha256,
                "n": len(self.patches), "chain": self.chain_hash(), "meta": self.meta}
        with open(path, "w", encoding="utf-8") as f:
            f.write(canonical_json(head) + "\n")
            for p in self.patches:
                f.write(canonical_json(p.to_dict()) + "\n")

    @staticmethod
    def read(path: str | Path) -> "PatchSet":
        lines = Path(path).read_text(encoding="utf-8").splitlines()
        head = json.loads(lines[0])
        if not head.get("_header"):
            raise ValueError("not a patch file (no header)")
        ps = PatchSet((Patch.from_dict(json.loads(x)) for x in lines[1:] if x.strip()),
                      head.get("input_sha256"), head.get("tool", ""), head.get("meta"))
        if ps.chain_hash() != head.get("chain"):
            raise ValueError("patch file chain hash mismatch (file edited or corrupted)")
        return ps


class PatchConflict(RuntimeError):
    pass


def apply_patches(records: Mapping[str, Mapping[str, Any]] | list, patches: Iterable[Patch],
                  id_field: str | None = None, strict: bool = True) -> dict:
    """Apply patches to records; returns a NEW dict {record_id: record}. Input is not mutated.

    records: {id: {field: value}} or a list of dicts together with id_field.
    strict: the record's current value must equal patch.old, else PatchConflict (a patch made from
    a different input cannot be applied silently).
    """
    out = _index(records, id_field)
    for p in patches:
        rec = out.get(str(p.record_id))
        if rec is None:
            if strict:
                raise PatchConflict(f"record {p.record_id} not found")
            continue
        cur = rec.get(p.field, _MISSING)
        want = p.old
        if strict and not (cur == want or (cur is _MISSING and want == _MISSING)):
            raise PatchConflict(f"{p.record_id}.{p.field}: expected {want!r}, found {cur!r}")
        if p.new == _MISSING:
            rec.pop(p.field, None)
        else:
            rec[p.field] = p.new
    return out


def revert_patches(records: Mapping | list, patches: Iterable[Patch], id_field: str | None = None,
                   strict: bool = True) -> dict:
    """Exact inverse of apply_patches: undo in reverse order."""
    inv = [Patch(p.record_id, p.field, p.new, p.old, p.rule, p.evidence, p.confidence)
           for p in reversed(list(patches))]
    return apply_patches(records, inv, id_field, strict)


def _index(records, id_field):
    if isinstance(records, Mapping):
        return {str(k): copy.deepcopy(dict(v)) for k, v in records.items()}
    if id_field is None:
        raise ValueError("id_field is required for a list of records")
    return {str(r[id_field]): copy.deepcopy(dict(r)) for r in records}


def missing() -> dict:
    """Sentinel for patches that insert a new field (old) or remove one (new)."""
    return dict(_MISSING)


# ---- file-level revert: byte for byte ----
def snapshot_input(path: str | Path, ledger: str | Path) -> dict:
    """Record the hash of an input file (never modified by tools). Returns the ledger entry."""
    entry = {"path": str(path), "sha256": sha256_file(path), "bytes": Path(path).stat().st_size}
    Path(ledger).parent.mkdir(parents=True, exist_ok=True)
    with open(ledger, "a", encoding="utf-8") as f:
        f.write(canonical_json(entry) + "\n")
    return entry


def verify_input_unchanged(path: str | Path, expected_sha256: str) -> bool:
    return sha256_file(path) == expected_sha256


def revert_file(cleaned_rows_path: str | Path, patches_path: str | Path, out_path: str | Path,
                reader, writer) -> str:
    """Revert a cleaned table to the input using the patch file; returns sha256 of the result.

    reader(path) -> (records dict, token) and writer(records, token, path) must be inverse of each other
    for the table format (the records module supplies them); the result is compared by the caller
    with PatchSet.input_sha256 to prove a byte-for-byte restoration.
    """
    ps = PatchSet.read(patches_path)
    recs, token = reader(cleaned_rows_path)
    writer(revert_patches(recs, ps.patches), token, out_path)
    return sha256_file(out_path)
