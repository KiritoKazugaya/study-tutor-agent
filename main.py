"""Study Tutor — terminal app.

A multi-agent study assistant that summarizes your notes, quizzes you
(MCQ / short answer / interview / live coding round), grades you with an
LLM-as-a-Judge, and remembers your weak topics across sessions.

Run:  python main.py
"""
from __future__ import annotations

import sys

# Windows terminals default to cp1252 and choke on emoji — force UTF-8.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

from study_tutor.core import (
    load_memory, save_memory, record_weakness, top_weak_topics,
)
from study_tutor.tools import (
    create_subject, list_subjects, list_docs, run_code,
)
from study_tutor.agents import (
    CoordinatorAgent, SummarizerAgent, QuizMasterAgent, EvaluatorAgent,
)

summarizer = SummarizerAgent()
quizmaster = QuizMasterAgent()
evaluator = EvaluatorAgent()
coordinator = CoordinatorAgent()


def banner():
    print("\n" + "=" * 58)
    print("  📚  STUDY TUTOR  —  multi-agent study assistant")
    print("=" * 58)


def pick_subject() -> str | None:
    subjects = list_subjects()
    if not subjects:
        print("No subjects yet. Create one first (menu option 1).")
        return None
    print("\nYour subjects:")
    for i, s in enumerate(subjects, 1):
        print(f"  {i}. {s}  ({len(list_docs(s))} docs)")
    choice = input("Pick a subject number: ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(subjects):
        return subjects[int(choice) - 1]
    print("Invalid choice.")
    return None


def do_summarize(subject: str):
    print(f"\n🧠 Summarizer working on '{subject}'...\n")
    print(summarizer.run(subject))


def _grade_and_remember(mem, subject, kind, question, ideal, answer, topic):
    verdict = evaluator.grade(question, ideal, answer)
    mark = "✅" if verdict.get("correct") else "❌"
    print(f"  {mark} Score {verdict.get('score')}/10 — {verdict.get('feedback')}")
    if not verdict.get("correct"):
        record_weakness(mem, topic)
    return verdict.get("score", 0)


def do_quiz(subject: str, kind: str):
    mem = load_memory()
    focus = top_weak_topics(mem)
    if focus:
        print(f"\n(Personalising around your weak topics: {', '.join(focus)})")
    print(f"\n📝 QuizMaster is generating a {kind.upper()} quiz on '{subject}'...\n")
    questions = quizmaster.run(subject, kind, n=4, focus=focus)

    scores = []
    for i, q in enumerate(questions, 1):
        topic = q.get("topic", subject)
        print(f"\nQ{i}. {q.get('q')}")

        if kind == "mcq":
            for opt in q.get("options", []):
                print(f"     {opt}")
            answer = input("Your answer (A/B/C/D): ").strip().upper()
            correct_letter = str(q.get("answer", "")).strip().upper()[:1]
            ok = answer[:1] == correct_letter
            mark = "✅" if ok else f"❌ (correct: {correct_letter})"
            print(f"  {mark}")
            if not ok:
                record_weakness(mem, topic)
            scores.append(10 if ok else 0)

        elif kind == "coding":
            print(f"     Signature: {q.get('signature', '')}")
            print("     Paste your Python solution. Type 'END' on its own line to submit:")
            lines = []
            while True:
                line = input()
                if line.strip() == "END":
                    break
                lines.append(line)
            code = "\n".join(lines)
            print("  ▶ Running your code...")
            output = run_code(code)
            print("  Output:", output[:500])
            submission = f"CODE:\n{code}\n\nOUTPUT:\n{output}"
            scores.append(_grade_and_remember(mem, subject, kind, q.get("q"),
                                               q.get("ideal", ""), submission, topic))

        else:  # short / interview
            answer = input("Your answer: ").strip()
            scores.append(_grade_and_remember(mem, subject, kind, q.get("q"),
                                              q.get("ideal", ""), answer, topic))

    avg = round(sum(scores) / len(scores), 1) if scores else 0
    print(f"\n🎯 Session score: {avg}/10")
    mem["scores"].append({"subject": subject, "kind": kind, "score": avg})
    save_memory(mem)
    print("(Saved to your memory — weak topics will be prioritised next time.)")


def show_progress():
    mem = load_memory()
    print("\n📈 YOUR PROGRESS")
    if mem["scores"]:
        for s in mem["scores"][-8:]:
            print(f"  • {s['subject']} [{s['kind']}] → {s['score']}/10")
    else:
        print("  No quizzes taken yet.")
    weak = top_weak_topics(mem, k=5)
    if weak:
        print("\n  Focus next on:", ", ".join(weak))


def ask_tutor():
    text = input("\nTell the tutor what you want (natural language): ").strip()
    route = coordinator.route(text)
    print(f"  → Coordinator routed to: {route['action']} ({route.get('reason', '')})")
    action = route["action"]
    if action == "show_progress":
        show_progress()
        return
    subject = pick_subject()
    if not subject:
        return
    if action == "summarize":
        do_summarize(subject)
    else:
        do_quiz(subject, action.replace("quiz_", ""))


MENU = """
  1. Create a subject folder
  2. List subjects & documents
  3. Summarize a subject
  4. Take a quiz (MCQ / short / interview / coding)
  5. Show my progress
  6. Ask the tutor (natural language)
  0. Exit
"""


def main():
    banner()
    print("Tip: create a subject, drop .txt/.md/.pdf files into its folder, then quiz yourself.")
    while True:
        print(MENU)
        choice = input("Choose: ").strip()
        if choice == "0":
            print("Keep learning! 👋")
            break
        elif choice == "1":
            name = input("New subject name: ").strip()
            if name:
                path = create_subject(name)
                print(f"Created: {path}  (drop your documents in here)")
        elif choice == "2":
            for s in list_subjects():
                print(f"  📁 {s}: {', '.join(list_docs(s)) or '(empty)'}")
        elif choice == "3":
            s = pick_subject()
            if s:
                do_summarize(s)
        elif choice == "4":
            s = pick_subject()
            if not s:
                continue
            kind = input("Type — mcq / short / interview / coding: ").strip().lower()
            if kind not in {"mcq", "short", "interview", "coding"}:
                print("Unknown type.")
                continue
            do_quiz(s, kind)
        elif choice == "5":
            show_progress()
        elif choice == "6":
            ask_tutor()
        else:
            print("Unknown option.")


if __name__ == "__main__":
    main()
