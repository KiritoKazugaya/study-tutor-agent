"""Flask web server for Study Tutor.

Thin HTTP layer over the SAME multi-agent backend used by the CLI
(study_tutor/*). Run from anywhere:

    python webapp/app.py

then open http://127.0.0.1:5000
"""
from __future__ import annotations

import os
import pathlib
import secrets
import sys
import threading

# Windows consoles default to cp1252 and choke on non-ASCII — force UTF-8.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Make the project importable and anchor all data (subjects/, memory) to the
# project root no matter where the server is launched from.
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from flask import Flask, Response, jsonify, request, send_from_directory, stream_with_context

from study_tutor.core import (
    load_memory, save_memory, record_weakness, top_weak_topics,
)
from study_tutor.tools import (
    create_subject, list_subjects, list_docs, SUBJECTS_DIR,
)
from study_tutor.agents import (
    SummarizerAgent, QuizMasterAgent, EvaluatorAgent, TutorAgent, FlashcardAgent,
)
from study_tutor import cache as cachelib

app = Flask(__name__, static_folder=None)
HERE = pathlib.Path(__file__).resolve().parent

summarizer = SummarizerAgent()
quizmaster = QuizMasterAgent()
evaluator = EvaluatorAgent()
tutor = TutorAgent()
flashcarder = FlashcardAgent()

ALLOWED = {".txt", ".md", ".pdf"}

# --------------------------------------------------------------------------- #
# Background pre-warming: build summary + question pools right after upload,   #
# so later clicks are served instantly from cache.                            #
# --------------------------------------------------------------------------- #
QUIZ_KINDS = ("mcq", "short", "interview", "coding")
# Only warm the two most common quiz types up front, to conserve API quota.
# Interview/coding generate on demand (still fast) and get cached after first use.
PREWARM_KINDS = ("mcq", "short")
POOL_TARGET = 6          # questions to keep ready per kind
_prewarming: set[str] = set()
_prewarm_lock = threading.Lock()


def _prewarm(subject: str) -> None:
    with _prewarm_lock:
        if subject in _prewarming:
            return
        _prewarming.add(subject)
    try:
        c = cachelib.load(subject)          # blank if docs changed
        if not c.get("summary"):
            try:
                c["summary"] = summarizer.run(subject)
                cachelib.save(subject, c)
            except Exception:
                pass
        for kind in PREWARM_KINDS:
            have = len(c["pool"].get(kind, []))
            if have < POOL_TARGET:
                try:
                    fresh = quizmaster.run(
                        subject, kind, n=POOL_TARGET - have,
                        variety_nonce=secrets.token_hex(3),
                    )
                    c["pool"].setdefault(kind, []).extend(fresh)
                    cachelib.save(subject, c)
                except Exception:
                    pass
    finally:
        with _prewarm_lock:
            _prewarming.discard(subject)


def _start_prewarm(subject: str) -> None:
    threading.Thread(target=_prewarm, args=(subject,), daemon=True).start()


@app.get("/")
def index():
    return send_from_directory(HERE, "index.html")


@app.get("/api/subjects")
def api_subjects():
    return jsonify([
        {"name": s, "docs": list_docs(s)} for s in list_subjects()
    ])


@app.post("/api/subject")
def api_create_subject():
    name = (request.json or {}).get("name", "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    create_subject(name)
    return jsonify({"ok": True})


@app.post("/api/upload")
def api_upload():
    subject = request.form.get("subject", "").strip()
    file = request.files.get("file")
    if not subject or not file:
        return jsonify({"error": "subject and file required"}), 400
    ext = pathlib.Path(file.filename).suffix.lower()
    if ext not in ALLOWED:
        return jsonify({"error": f"only {', '.join(sorted(ALLOWED))} allowed"}), 400
    dest = create_subject(subject) / pathlib.Path(file.filename).name
    file.save(str(dest))
    _start_prewarm(subject)   # build summary + quiz pools in the background
    return jsonify({"ok": True, "saved": dest.name, "prewarming": True})


@app.post("/api/prewarm")
def api_prewarm():
    """Manually kick off pre-warming for a subject (e.g. the sample one)."""
    subject = (request.json or {}).get("subject", "").strip()
    if subject:
        _start_prewarm(subject)
    return jsonify({"ok": True})


@app.get("/api/ready")
def api_ready():
    """Report what's already cached so the UI can show a 'ready' badge."""
    subject = request.args.get("subject", "").strip()
    c = cachelib.load(subject)
    return jsonify({
        "summary": bool(c.get("summary")),
        "pool": {k: len(c.get("pool", {}).get(k, [])) for k in QUIZ_KINDS},
        "building": subject in _prewarming,
    })


@app.post("/api/summarize")
def api_summarize():
    subject = (request.json or {}).get("subject", "").strip()
    c = cachelib.load(subject)
    if c.get("summary"):
        return jsonify({"summary": c["summary"], "cached": True})
    try:
        summary = summarizer.run(subject)
        c["summary"] = summary
        cachelib.save(subject, c)
        return jsonify({"summary": summary})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.post("/api/quiz")
def api_quiz():
    data = request.json or {}
    subject = data.get("subject", "").strip()
    kind = data.get("kind", "mcq").strip()
    try:
        n = int(data.get("n", 5))
    except (TypeError, ValueError):
        n = 5
    n = max(1, min(n, 10))
    style = data.get("style", "auto")
    mem = load_memory()
    focus = top_weak_topics(mem)

    # Fast path: serve instantly from the pre-built pool (default 'auto' style).
    # Personalisation still happens — we bias the cached questions toward the
    # student's weak topics using their topic tags, with NO extra LLM call.
    if style == "auto":
        c = cachelib.load(subject)
        pool = c.get("pool", {}).get(kind, [])
        if len(pool) >= n:
            if focus:
                focus_words = {w for f in focus for w in f.lower().split() if len(w) > 3}

                def _hits_weak(q):
                    topic = str(q.get("topic", "")).lower()
                    return any(w in topic for w in focus_words)

                pool = sorted(pool, key=lambda q: not _hits_weak(q))  # weak topics first
            served, remaining = pool[:n], pool[n:]
            c.setdefault("pool", {})[kind] = remaining
            cachelib.save(subject, c)
            if len(remaining) < n:            # running low → refill in background
                _start_prewarm(subject)
            return jsonify({"questions": served, "focus": focus, "cached": True})

    # Slow path: generate fresh (personalised or pool not ready yet).
    try:
        questions = quizmaster.run(
            subject, kind, n=n, focus=focus, style=style,
            variety_nonce=secrets.token_hex(3),
        )
        return jsonify({"questions": questions, "focus": focus})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.post("/api/summarize_stream")
def api_summarize_stream():
    """Stream the summary token-by-token; cache the full text when done."""
    subject = (request.json or {}).get("subject", "").strip()
    cached = cachelib.load(subject).get("summary")

    @stream_with_context
    def gen():
        if cached:
            yield cached
            return
        buf = []
        for chunk in summarizer.run_stream(subject):
            buf.append(chunk)
            yield chunk
        full = "".join(buf).strip()
        if full and not full.startswith("No documents"):
            c = cachelib.load(subject)
            c["summary"] = full
            cachelib.save(subject, c)

    return Response(gen(), mimetype="text/plain; charset=utf-8")


@app.post("/api/ask")
def api_ask():
    """Answer a free-text question about a subject, streamed live."""
    data = request.json or {}
    subject = data.get("subject", "").strip()
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "question required"}), 400

    @stream_with_context
    def gen():
        yield from tutor.answer_stream(subject, question)

    return Response(gen(), mimetype="text/plain; charset=utf-8")


@app.post("/api/flashcards")
def api_flashcards():
    """Generate flashcards; cache a pool so repeats are instant."""
    subject = (request.json or {}).get("subject", "").strip()
    n = 8
    c = cachelib.load(subject)
    pool = c.get("pool", {}).get("flashcards", [])
    if len(pool) >= n:
        served, c["pool"]["flashcards"] = pool[:n], pool[n:]
        cachelib.save(subject, c)
        return jsonify({"cards": served, "cached": True})
    try:
        cards = flashcarder.run(subject, n=n, variety_nonce=secrets.token_hex(3))
        return jsonify({"cards": cards})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.post("/api/subject/delete")
def api_subject_delete():
    subject = (request.json or {}).get("subject", "").strip()
    d = SUBJECTS_DIR / subject
    if d.exists():
        import shutil
        shutil.rmtree(d, ignore_errors=True)
    try:
        cachelib._path(subject).unlink(missing_ok=True)
    except Exception:
        pass
    return jsonify({"ok": True})


@app.post("/api/grade")
def api_grade():
    data = request.json or {}
    kind = data.get("kind", "short")
    question = data.get("question", "")
    ideal = data.get("ideal", "")
    answer_key = str(data.get("answer_key", "")).strip().upper()[:1]
    student = data.get("answer", "")
    topic = data.get("topic", "")

    mem = load_memory()
    if kind == "mcq":
        correct = str(student).strip().upper()[:1] == answer_key
        verdict = {
            "score": 10 if correct else 0,
            "correct": correct,
            "feedback": "Correct!" if correct else f"Correct answer was {answer_key}.",
        }
    else:
        try:
            verdict = evaluator.grade(question, ideal, student)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    if not verdict.get("correct"):
        record_weakness(mem, topic)
    save_memory(mem)
    return jsonify(verdict)


@app.post("/api/session_score")
def api_session_score():
    data = request.json or {}
    mem = load_memory()
    mem["scores"].append({
        "subject": data.get("subject", ""),
        "kind": data.get("kind", ""),
        "score": data.get("score", 0),
    })
    save_memory(mem)
    return jsonify({"ok": True})


@app.get("/api/progress")
def api_progress():
    mem = load_memory()
    return jsonify({
        "scores": mem.get("scores", [])[-10:],
        "weak_topics": top_weak_topics(mem, k=6),
    })


if __name__ == "__main__":
    print("Study Tutor web app → http://127.0.0.1:5000  (Ctrl+C to stop)")
    app.run(host="127.0.0.1", port=5000, debug=False)
