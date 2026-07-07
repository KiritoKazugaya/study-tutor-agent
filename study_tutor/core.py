"""Core services shared by every agent: the LLM client and persistent memory.

These are deliberately tiny wrappers so the *agent* logic stays readable.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import time

try:  # load .env if present (optional dependency)
    from dotenv import load_dotenv
    load_dotenv()
except Exception:  # pragma: no cover - dotenv is optional
    pass

from google import genai
from google.genai import types

MODEL = os.environ.get("STUDY_TUTOR_MODEL", "gemini-2.5-flash")

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise SystemExit(
                "No API key found. Get a free one at "
                "https://aistudio.google.com/apikey and set GEMINI_API_KEY "
                "(or copy .env.example to .env and paste it there)."
            )
        _client = genai.Client(api_key=key)
    return _client


# Gemini 2.5 Flash "thinks" by default, adding ~15-20s per call. Summaries and
# quizzes don't need it — disabling makes every request ~3-5x faster.
try:
    _NO_THINKING = types.ThinkingConfig(thinking_budget=0)
except Exception:  # older SDK / model without thinking support
    _NO_THINKING = None


def generate(prompt: str, system: str | None = None, temperature: float = 0.7) -> str:
    """Single entry point for every LLM call in the app.

    Retries once on a transient (per-minute) rate limit, and raises a clear,
    actionable message when the quota is genuinely exhausted.
    """
    cfg = types.GenerateContentConfig(
        temperature=temperature,
        system_instruction=system,
        thinking_config=_NO_THINKING,
    )
    for attempt in range(2):
        try:
            resp = _get_client().models.generate_content(
                model=MODEL, contents=prompt, config=cfg
            )
            return (resp.text or "").strip()
        except Exception as exc:
            msg = str(exc)
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                retry = re.search(r"retry in ([\d.]+)s", msg)
                delay = float(retry.group(1)) if retry else 6.0
                # Only wait for short (per-minute) windows; give up on long ones.
                if attempt == 0 and delay <= 10:
                    time.sleep(delay + 0.5)
                    continue
                raise RuntimeError(
                    f"Gemini quota reached for model '{MODEL}'. Your free-tier limit "
                    "is used up for now. Fix: enable billing on your Google Cloud "
                    "project (costs pennies) or create a new API key in a new project, "
                    "then restart the server."
                ) from exc
            raise
    raise RuntimeError("Gemini request failed after retry.")


# --------------------------------------------------------------------------- #
# Persistent memory (Course concept: Sessions & Memory)                        #
# --------------------------------------------------------------------------- #
MEM_PATH = pathlib.Path("student_memory.json")


def load_memory() -> dict:
    if MEM_PATH.exists():
        try:
            return json.loads(MEM_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"student": "learner", "weak_topics": {}, "scores": []}


def save_memory(mem: dict) -> None:
    MEM_PATH.write_text(json.dumps(mem, indent=2), encoding="utf-8")


def record_weakness(mem: dict, topic: str) -> None:
    if not topic:
        return
    mem["weak_topics"][topic] = mem["weak_topics"].get(topic, 0) + 1


def top_weak_topics(mem: dict, k: int = 3) -> list[str]:
    items = sorted(mem["weak_topics"].items(), key=lambda kv: kv[1], reverse=True)
    return [t for t, _ in items[:k]]
