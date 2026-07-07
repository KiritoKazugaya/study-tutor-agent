"""Tools the agents can call (Course concept: Agent Tools / function-calling).

Each function is a self-contained capability: managing subject folders,
loading uploaded documents into context, and safely running student code.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

SUBJECTS_DIR = pathlib.Path("subjects")


def create_subject(name: str) -> pathlib.Path:
    """Create a subject 'folder' the student can drop documents into."""
    d = SUBJECTS_DIR / name.strip()
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_subjects() -> list[str]:
    if not SUBJECTS_DIR.exists():
        return []
    return sorted(p.name for p in SUBJECTS_DIR.iterdir() if p.is_dir())


def list_docs(subject: str) -> list[str]:
    d = SUBJECTS_DIR / subject
    if not d.exists():
        return []
    return sorted(p.name for p in d.glob("**/*") if p.is_file())


def load_subject_docs(subject: str, max_chars: int = 12000) -> str:
    """Read every .txt/.md/.pdf in a subject folder into one context blob."""
    d = SUBJECTS_DIR / subject
    if not d.exists():
        return ""
    chunks: list[str] = []
    for p in sorted(d.glob("**/*")):
        if not p.is_file():
            continue
        suffix = p.suffix.lower()
        if suffix in {".txt", ".md"}:
            chunks.append(f"### {p.name}\n" + p.read_text(encoding="utf-8", errors="ignore"))
        elif suffix == ".pdf":
            chunks.append(f"### {p.name}\n" + _read_pdf(p))
    return "\n\n".join(chunks)[:max_chars]


def _read_pdf(p: pathlib.Path) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(p))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as exc:  # pragma: no cover
        return f"[could not read PDF {p.name}: {exc}]"


def run_code(code: str, stdin: str = "", timeout: int = 10) -> str:
    """Execute student-submitted Python in a subprocess and capture output.

    Used by the terminal coding round so the Evaluator can judge real output.
    """
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(code)
        path = f.name
    try:
        result = subprocess.run(
            [sys.executable, path],
            input=stdin,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return (result.stdout + result.stderr).strip() or "[no output]"
    except subprocess.TimeoutExpired:
        return "[timeout: your code ran longer than %ss]" % timeout
    finally:
        pathlib.Path(path).unlink(missing_ok=True)
