"""The multi-agent system (Course concept: Multi-agent systems).

A Coordinator routes each student request to one of three specialist agents:

    Coordinator ─┬─▶ Summarizer   (turns uploaded docs into exam-ready notes)
                 ├─▶ QuizMaster   (generates MCQ / short / interview / coding items)
                 └─▶ Evaluator    (LLM-as-a-Judge grading + updates memory)

Each agent has a single responsibility and its own system persona.
"""
from __future__ import annotations

import json
import re

from .core import generate, generate_stream
from .tools import load_subject_docs


def _parse_json(text: str):
    """Best-effort JSON extraction from an LLM response."""
    match = re.search(r"\[.*\]|\{.*\}", text, re.S)
    raw = match.group(0) if match else text
    return json.loads(raw)


class SummarizerAgent:
    name = "Summarizer"
    persona = "You are an expert tutor who writes concise, accurate, exam-ready study notes."

    _EMPTY = ("No documents found for that subject yet. "
              "Add .txt/.md/.pdf files to its folder first.")

    def _prompt(self, subject: str, docs: str) -> str:
        return (
            f"Summarize these study materials for '{subject}' into clear notes:\n"
            "- Key concepts as bullet points\n"
            "- A short 'must remember' list\n"
            "- 3 common mistakes students make on this topic\n\n"
            f"{docs}"
        )

    def run(self, subject: str) -> str:
        docs = load_subject_docs(subject)
        if not docs:
            return self._EMPTY
        return generate(self._prompt(subject, docs), system=self.persona, temperature=0.4)

    def run_stream(self, subject: str):
        docs = load_subject_docs(subject)
        if not docs:
            yield self._EMPTY
            return
        yield from generate_stream(self._prompt(subject, docs),
                                   system=self.persona, temperature=0.4)


class QuizMasterAgent:
    name = "QuizMaster"
    persona = "You are a rigorous, creative exam setter. Output ONLY valid JSON, no prose."

    _specs = {
        "mcq": '{"q": "question", "options": ["A) ..","B) ..","C) ..","D) .."], "answer": "A", "explanation": "why the correct option is right and what makes the distractors wrong", "topic": "sub-topic"}',
        "short": '{"q": "question", "ideal": "a full model answer listing every key point expected", "topic": "sub-topic"}',
        "interview": '{"q": "an open interview-style question", "ideal": "point-by-point, what a strong answer must cover", "topic": "sub-topic"}',
        "coding": '{"q": "a small, clearly specified coding problem", "signature": "def solve(...):", "ideal": "expected approach, key steps, and edge cases to handle", "topic": "sub-topic"}',
    }

    _style_hint = {
        "auto": "Read the material and choose the question angles it best supports.",
        "core": "Focus on core concepts, definitions, and conceptual understanding.",
        "code": "Focus on practical / applied / code-based problem solving where the topic allows.",
        "mixed": "Mix conceptual, applied, and analytical questions for broad coverage.",
    }

    def run(self, subject: str, kind: str, n: int = 5, focus: list[str] | None = None,
            style: str = "auto", variety_nonce: str = "") -> list[dict]:
        docs = load_subject_docs(subject, max_chars=8000)
        focus_line = ""
        if focus:
            focus_line = f"Prioritise these weak topics for this student: {', '.join(focus)}.\n"
        style_line = self._style_hint.get(style, self._style_hint["auto"])
        prompt = (
            f"You are setting a {kind} quiz on '{subject}'.\n"
            f"First understand the material below and identify the different angles it supports "
            f"(definitions, application, analysis, reasoning, code, edge cases).\n"
            f"{style_line}\n"
            f"{focus_line}"
            f"Then create {n} DISTINCT questions that each explore a DIFFERENT perspective — do not "
            f"repeat the same idea or standard textbook phrasing, and vary the difficulty.\n"
            f"Return a JSON list of exactly {n} items, each shaped like: {self._specs[kind]}\n"
            f"(freshness token, ignore in output: {variety_nonce})\n\n"
            f"MATERIAL:\n{docs}"
        )
        # High temperature => genuinely different questions on every run.
        raw = generate(prompt, system=self.persona, temperature=1.0)
        try:
            data = _parse_json(raw)
        except Exception:
            # self-repair pass
            fixed = generate("Convert this into a valid JSON list only:\n" + raw, temperature=0)
            data = _parse_json(fixed)
        return data if isinstance(data, list) else [data]


class EvaluatorAgent:
    """LLM-as-a-Judge (Course concept: Agent Quality / evaluation)."""

    name = "Evaluator"
    persona = "You are a fair but strict grader. Output ONLY JSON, no prose."

    def grade(self, question: str, ideal: str, student_answer: str) -> dict:
        prompt = (
            f"QUESTION: {question}\n"
            f"EXPECTED ANSWER / KEY POINTS: {ideal}\n"
            f"STUDENT ANSWER: {student_answer}\n\n"
            "Grade the student's answer against the expected key points. Be specific.\n"
            'Return JSON: {"score": <0-10 int>, "correct": <true if score>=6 else false>, '
            '"feedback": "2-3 sentences that name exactly which points were correct, which '
            'key points were missing or wrong, and one concrete tip to improve"}'
        )
        raw = generate(prompt, system=self.persona, temperature=0)
        try:
            result = _parse_json(raw)
        except Exception:
            return {"score": 0, "correct": False, "feedback": raw[:180]}
        result.setdefault("score", 0)
        result.setdefault("correct", False)
        result.setdefault("feedback", "")
        return result


class TutorAgent:
    """Answers free-text questions grounded in the student's own documents."""

    name = "Tutor"
    persona = ("You are a warm, precise tutor. Answer using the student's material below. "
               "If the answer isn't in the material, say so briefly, then give correct general guidance. "
               "Use short paragraphs and bullet points; keep it focused.")

    def _prompt(self, subject: str, question: str) -> str:
        docs = load_subject_docs(subject, max_chars=10000)
        context = f"MATERIAL for '{subject}':\n{docs}" if docs else "(no documents uploaded yet)"
        return f"Student's question: {question}\n\n{context}"

    def answer(self, subject: str, question: str) -> str:
        return generate(self._prompt(subject, question), system=self.persona, temperature=0.4)

    def answer_stream(self, subject: str, question: str):
        yield from generate_stream(self._prompt(subject, question),
                                   system=self.persona, temperature=0.4)


class FlashcardAgent:
    """Turns study material into concise front/back flashcards."""

    name = "Flashcards"
    persona = "You create concise, accurate study flashcards. Output ONLY valid JSON."

    def run(self, subject: str, n: int = 8, variety_nonce: str = "") -> list[dict]:
        docs = load_subject_docs(subject, max_chars=8000)
        prompt = (
            f"Create {n} study flashcards from the material on '{subject}'.\n"
            "Each card: a short prompt on the front, a concise answer on the back.\n"
            'Return a JSON list of items like: {"front": "term or question", '
            '"back": "concise definition or answer", "topic": "sub-topic"}\n'
            f"(freshness token: {variety_nonce})\n\nMATERIAL:\n{docs}"
        )
        raw = generate(prompt, system=self.persona, temperature=0.8)
        try:
            data = _parse_json(raw)
        except Exception:
            data = _parse_json(generate("Convert to a valid JSON list only:\n" + raw, temperature=0))
        return data if isinstance(data, list) else [data]


class CoordinatorAgent:
    """Routes a free-text student request to the right specialist."""

    name = "Coordinator"
    persona = "You route student requests to tutor sub-agents. Output ONLY JSON."

    ACTIONS = ["summarize", "quiz_mcq", "quiz_short", "quiz_interview", "quiz_coding", "show_progress"]

    def route(self, text: str) -> dict:
        prompt = (
            f'The student said: "{text}".\n'
            f"Pick exactly one action from {self.ACTIONS}.\n"
            'Return JSON: {"action": "...", "reason": "short reason"}'
        )
        raw = generate(prompt, system=self.persona, temperature=0)
        try:
            result = _parse_json(raw)
        except Exception:
            return {"action": "summarize", "reason": "fallback"}
        if result.get("action") not in self.ACTIONS:
            result["action"] = "summarize"
        return result
