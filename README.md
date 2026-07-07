# 📚 Study Tutor — a multi-agent study assistant

Built for the **5-Day AI Agents: Intensive Vibe Coding Capstone** · Track: **Agents for Good** (education).

Study Tutor turns your own notes into an interactive tutor. Drop your documents
into a subject folder and a team of agents will **summarize** them, **quiz** you
(MCQ / short answer / interview / coding), **grade** you with an LLM-as-a-Judge,
answer your **questions** from the material, build **flashcards**, and
**remember your weak topics** so the next quiz targets what you keep getting wrong.

## Features
- 🧠 **Streaming summaries** — exam-ready notes that type out live.
- 📝 **Adaptive quizzes** — MCQ / short / interview / coding, with immutable
  answers, specific grading, and weak-topic personalisation.
- 💬 **Ask the Tutor** — a chat that answers from *your* uploaded notes (streamed).
- 🃏 **Flashcards** — a flip-card deck generated from your material.
- 📈 **Progress tracking** — animated score chart + weak-topic memory, with a
  confetti celebration on high scores.
- ⚡ **Instant loading** — thinking disabled + pre-warmed cache of summaries and
  question pools on upload.
- 🗂️ **Subjects** — create, upload docs to, and delete subjects (full CRUD).
- Two front-ends over one backend: a **Flask web app** and a **terminal CLI**.

## Course concepts demonstrated (≥3 required — this shows 6)
1. **Multi-agent system** — a `Coordinator` routes to `Summarizer`, `QuizMaster`,
   `Evaluator`, `Tutor`, and `Flashcard` specialist agents (`study_tutor/agents.py`).
2. **Agent tools / function-calling** — subject-folder management, document
   ingestion (.txt/.md/.pdf), and a sandboxed code runner (`study_tutor/tools.py`).
3. **Sessions & memory** — persistent `student_memory.json` tracks weak topics and
   scores across runs and personalises future quizzes (`study_tutor/core.py`).
4. **Agent quality / evaluation** — the `Evaluator` is an **LLM-as-a-Judge** that
   scores answers and drives the memory updates.
5. **Context engineering / caching** — summaries and question pools are pre-built
   on upload and served from a per-subject cache (`study_tutor/cache.py`).
6. **Grounded Q&A (RAG-style) + streaming** — the `Tutor` answers strictly from the
   student's documents, streamed token-by-token for a responsive UX.

## Architecture
```
              You  (web app / terminal)
                     │
              ┌──────▼───────┐
              │ Coordinator  │  routes the request
              └──────┬───────┘
   ┌───────────┬─────┼───────────┬───────────┐
┌──▼────┐ ┌────▼────┐ ┌──▼─────┐ ┌─▼────┐ ┌──▼──────┐
│Summar-│ │QuizMaster│ │Evaluator│ │Tutor │ │Flashcard│
│izer   │ │          │ │(Judge) │ │(Q&A) │ │         │
└──┬────┘ └────┬────┘ └──┬─────┘ └─┬────┘ └──┬──────┘
   └──── tools: docs / folders / code runner ────┘
                     │
      cache (pre-warmed) · student_memory.json (weak topics + scores)
```

## Setup (2 minutes)
```bash
pip install -r requirements.txt
cp .env.example .env        # then paste your key into .env
# Get a FREE permanent key: https://aistudio.google.com/apikey
```
On Windows PowerShell use `copy .env.example .env`.

### Run the web app (recommended)
```bash
python webapp/app.py
```
Then open **http://127.0.0.1:5000** — a single-page UI with subjects, document
upload, summaries, quizzes, live grading, and a progress view.

### Or run the terminal version
```bash
python main.py
```
Both front-ends share the exact same multi-agent backend in `study_tutor/`.

## Try it
1. `python main.py`
2. Option **2** → you already have a sample `Biology` subject.
3. Option **3** → summarize Biology.
4. Option **4** → take an `mcq` (or `coding`) quiz. Answer a few wrong on purpose.
5. Option **5** → see your weak topics recorded. Re-run a quiz — it now targets them.

## Roadmap (beyond the capstone)
- Web UI (React + animations) calling the agents over an API.
- Persistent hosted agent via **Vertex AI Agent Engine** (permanent endpoint).
- Google Forms export of generated quizzes via Google Apps Script.

## Tech
Python · Google Gemini (`google-genai`) · multi-agent design · LLM-as-a-Judge.
