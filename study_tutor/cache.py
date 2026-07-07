"""Per-subject cache so summaries and quizzes are ready *before* you click.

The moment notes are uploaded, a background worker pre-builds the summary and a
pool of questions and stores them here. Later requests are served instantly.
This is the "context engineering / pre-computation" idea from the course.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import threading

from .tools import SUBJECTS_DIR

CACHE_DIR = pathlib.Path(".cache")
_lock = threading.Lock()


def subject_signature(subject: str) -> str:
    """A fingerprint of a subject's documents (name+size+mtime).

    Changes whenever a file is added/edited, which invalidates stale cache.
    """
    d = SUBJECTS_DIR / subject
    if not d.exists():
        return ""
    parts = []
    for p in sorted(d.glob("**/*")):
        if p.is_file():
            st = p.stat()
            parts.append(f"{p.name}:{st.st_size}:{int(st.st_mtime)}")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _path(subject: str) -> pathlib.Path:
    CACHE_DIR.mkdir(exist_ok=True)
    safe = hashlib.sha256(subject.encode()).hexdigest()[:16]
    return CACHE_DIR / f"{safe}.json"


def blank(subject: str) -> dict:
    return {"sig": subject_signature(subject), "summary": None, "pool": {}}


def load(subject: str) -> dict:
    """Load cache; return a blank (reset) cache if missing, corrupt, or stale."""
    p = _path(subject)
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if data.get("sig") == subject_signature(subject):
                data.setdefault("summary", None)
                data.setdefault("pool", {})
                return data
        except Exception:
            pass
    return blank(subject)


def save(subject: str, data: dict) -> None:
    """Atomically persist the cache (temp file + replace) under a lock."""
    with _lock:
        p = _path(subject)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        os.replace(tmp, p)
