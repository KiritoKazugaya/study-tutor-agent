# 📚 Study Tutor — a multi-agent study assistant

Built for the **5-Day AI Agents: Intensive Vibe Coding Capstone** · Track: **Agents for Good** (education).

Study Tutor turns your own notes into an interactive tutor. Drop your documents
into a subject folder and the agents will **summarize** them, **quiz** you
(MCQ / short answer / interview / a live **coding round in the terminal**),
**grade** you with an LLM-as-a-Judge, and **remember your weak topics** so the
next quiz targets exactly what you keep getting wrong.

## Course concepts demonstrated (≥3 required)
1. **Multi-agent system** — a `Coordinator` routes requests to `Summarizer`,
   `QuizMaster`, and `Evaluator` specialist agents (`study_tutor/agents.py`).
2. **Agent tools / function-calling** — subject-folder management, document
   ingestion (.txt/.md/.pdf), and a sandboxed code runner (`study_tutor/tools.py`).
3. **Sessions & memory** — persistent `student_memory.json` tracks weak topics and
   scores across runs and personalises future quizzes (`study_tutor/core.py`).
4. **Agent quality / evaluation (bonus)** — the `Evaluator` is an
   **LLM-as-a-Judge** that scores answers and drives the memory updates.

## Architecture
```
        You (terminal / natural language)
                     │
              ┌──────▼───────┐
              │ Coordinator  │  routes the request
              └──────┬───────┘
        ┌────────────┼─────────────┐
   ┌────▼────┐  ┌────▼─────┐  ┌────▼──────┐
   │Summarizer│  │QuizMaster│  │ Evaluator │  (LLM-as-a-Judge)
   └────┬────┘  └────┬─────┘  └────┬──────┘
        └───── tools: docs / folders / code runner ─────┘
                     │
             student_memory.json  (weak topics + scores)
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
