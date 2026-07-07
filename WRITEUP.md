# Study Tutor — Kaggle Capstone Writeup

**Track:** Agents for Good (Education)
**Team:** <your name / team, up to 4>
**Code:** https://github.com/KiritoKazugaya/study-tutor-agent
**Live app:** https://study-tutor-g8h1.onrender.com
**Video:** <paste your 2–3 min demo link>

---

## The Pitch — Problem, Solution, Value

**Problem.** Students drown in their own notes but have no cheap, patient tutor
who knows *their* material and *their* weak spots. Generic quiz apps don't read
your syllabus, and human tutoring doesn't scale.

**Solution.** Study Tutor is a multi-agent assistant that ingests a student's own
documents and becomes a personalised tutor. It **summarises** the material, quizzes
the student four ways (MCQ, short answer, interview, coding), **grades** each answer
with specific feedback, **answers questions** from the notes in a chat, builds
**flashcards**, and — crucially — **remembers what the student keeps getting wrong**
and steers future quizzes toward those topics. It ships as a polished web app (with
a terminal CLI over the same backend).

**Value.** It closes the feedback loop that self-study lacks: material in →
targeted practice → judged feedback → memory of weaknesses → harder practice on
exactly those weaknesses. It works on any subject the student uploads and needs no
setup beyond an API key.

## The Implementation — Architecture & Code

A **Coordinator** agent routes each request to one of five specialists:

- **Summarizer** — turns uploaded `.txt/.md/.pdf` docs into exam-ready notes (streamed).
- **QuizMaster** — generates MCQ / short / interview / coding questions grounded in
  the material, biased toward the student's recorded weak topics.
- **Evaluator** — an **LLM-as-a-Judge** that scores each answer 0–10 with feedback.
- **Tutor** — answers free-text questions **strictly from the student's documents**
  (grounded, RAG-style), streamed token-by-token.
- **Flashcard** — turns the material into a flip-card study deck.

Supporting **tools** handle subject management, document ingestion, and a sandboxed
subprocess **code runner**. A persistent `student_memory.json` store carries weak
topics and scores **across sessions**. A per-subject **cache** pre-builds summaries
and question pools on upload, so later actions load instantly; disabling the model's
thinking mode cut latency ~20×.

### Course concepts demonstrated (6)
1. **Multi-agent systems** — Coordinator + 5 specialist agents with distinct personas.
2. **Agent tools / function-calling** — document loading, folder management, code execution.
3. **Sessions & memory** — persistent, personalising memory of weak topics/scores.
4. **Agent quality / evaluation** — Evaluator = LLM-as-a-Judge driving the learning loop.
5. **Context engineering / caching** — pre-warmed per-subject summary + question pools.
6. **Grounded Q&A + streaming** — the Tutor answers from the docs, streamed live.

### Safety / responsible design
- Student code runs in a subprocess with a hard timeout (no unbounded execution).
- The Tutor is instructed to answer only from the uploaded material and to say so
  when something isn't covered, reducing hallucination.
- User data (docs, memory) stays local except the LLM calls needed to reason.

## What I'd do next
A permanent hosted endpoint via **Vertex AI Agent Engine**, one-click **Google Forms**
export of generated quizzes, and multi-user accounts with cloud-synced progress.
