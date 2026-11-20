"""Key loader. Keys live in a keys.env file outside the repo; values are never printed or logged."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_KEYS_PATHS = (
    "wildfire 3 (1)/keys/keys.env",
    "../wildfire 3 (1)/keys/keys.env",
    "/home/user/wildfire 3 (1)/keys/keys.env",
)


class MissingKey(RuntimeError):
    """Raised by require_key. The message names the key, never a value."""


def find_keys_file(path: str | os.PathLike | None = None) -> Path | None:
    cands = []
    if path:
        cands.append(Path(path))
    if os.environ.get("FIREWITNESS_KEYS"):
        cands.append(Path(os.environ["FIREWITNESS_KEYS"]))
    cands += [Path(p).expanduser() for p in DEFAULT_KEYS_PATHS]
    for c in cands:
        if c.is_file():
            return c
    return None


def parse_env(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k:
            out[k] = v
    return out


def load_keys(path: str | os.PathLike | None = None) -> dict[str, str]:
    """Read keys.env; process environment variables of the same name override."""
    f = find_keys_file(path)
    keys = parse_env(f.read_text()) if f else {}
    for k in list(keys):
        if os.environ.get(k):
            keys[k] = os.environ[k]
    return keys


def get_key(name: str, path: str | os.PathLike | None = None) -> str | None:
    if os.environ.get(name):
        return os.environ[name]
    return load_keys(path).get(name)


def require_key(name: str, needs_file: str | os.PathLike | None = None,
                track: str = "records", path: str | os.PathLike | None = None) -> str:
    """Return the key, or record its NAME in NEEDS.md (if a path is given) and raise MissingKey."""
    v = get_key(name, path)
    if v:
        return v
    if needs_file:
        _note_need(Path(needs_file), name, track)
    raise MissingKey(f"key {name} is not set (looked in keys.env and the environment)")


def _note_need(needs: Path, name: str, track: str) -> None:
    line = f"| {track} | key {name} | {datetime.now(timezone.utc):%Y-%m-%dT%H:%MZ} | open |\n"
    existing = needs.read_text() if needs.exists() else "# NEEDS\n\n| track | need | first noted (UTC) | status |\n|---|---|---|---|\n"
    if f"key {name} " in existing and f"| {track} |" in existing:
        return
    needs.write_text(existing.rstrip("\n") + "\n" + line)


def redact(text: str, keys: dict[str, str] | None = None) -> str:
    """Replace any known key value in text with <REDACTED:NAME>. Use before logging anything."""
    keys = keys if keys is not None else load_keys()
    for k, v in keys.items():
        if v and len(v) >= 8:
            text = text.replace(v, f"<REDACTED:{k}>")
    return text
