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

from flask import Flask, jsonify, request, send_from_directory

from study_tutor.core import (
    load_memory, save_memory, record_weakness, top_weak_topics,
)
from study_tutor.tools import (
    create_subject, list_subjects, list_docs, SUBJECTS_DIR,
)
from study_tutor.agents import (
    SummarizerAgent, QuizMasterAgent, EvaluatorAgent,
)

app = Flask(__name__, static_folder=None)
HERE = pathlib.Path(__file__).resolve().parent

summarizer = SummarizerAgent()
quizmaster = QuizMasterAgent()
evaluator = EvaluatorAgent()

ALLOWED = {".txt", ".md", ".pdf"}


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
    return jsonify({"ok": True, "saved": dest.name})


@app.post("/api/summarize")
def api_summarize():
    subject = (request.json or {}).get("subject", "").strip()
    try:
        return jsonify({"summary": summarizer.run(subject)})
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
    try:
        questions = quizmaster.run(
            subject, kind, n=n, focus=focus, style=style,
            variety_nonce=secrets.token_hex(3),
        )
        return jsonify({"questions": questions, "focus": focus})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


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
