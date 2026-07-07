# Study Tutor — Kaggle Capstone Writeup

**Track:** Agents for Good (Education)
**Team:** <your name / team, up to 4>
**Code:** <paste your public GitHub / Kaggle Notebook link>
**Video:** <paste your 2–3 min demo link>

---

## The Pitch — Problem, Solution, Value

**Problem.** Students drown in their own notes but have no cheap, patient tutor
who knows *their* material and *their* weak spots. Generic quiz apps don't read
your syllabus, and human tutoring doesn't scale.

**Solution.** Study Tutor is a multi-agent assistant that ingests a student's own
documents and becomes a personalised tutor: it summarises the material, quizzes
the student four different ways (MCQ, short answer, interview, and a live coding
round graded in the terminal), and — crucially — **remembers what the student
keeps getting wrong** and steers future quizzes toward those topics.

**Value.** It closes the feedback loop that self-study lacks: material in →
targeted practice → judged feedback → memory of weaknesses → harder practice on
exactly those weaknesses. It works on any subject the student uploads, runs on the
free Gemini tier, and needs no setup beyond an API key.

## The Implementation — Architecture & Code

A **Coordinator** agent routes each request to one of three specialists:

- **Summarizer** — turns uploaded `.txt/.md/.pdf` docs into exam-ready notes.
- **QuizMaster** — generates MCQ / short / interview / coding questions grounded
  in the uploaded material, biased toward the student's recorded weak topics.
- **Evaluator** — an **LLM-as-a-Judge** that scores each answer 0–10 with feedback
  and flags wrong topics.

Supporting **tools** handle subject-folder management, document ingestion, and a
sandboxed subprocess **code runner** for the coding round. A persistent
`student_memory.json` store carries weak topics and scores **across sessions** and
personalises every future quiz.

### Course concepts demonstrated (≥3)
1. **Multi-agent systems** — Coordinator + 3 specialist agents with distinct
   personas and responsibilities.
2. **Agent tools / function-calling** — document loading, folder management, code
   execution.
3. **Sessions & memory** — persistent, personalising memory of weak topics/scores.
4. **Agent quality / evaluation (bonus)** — Evaluator = LLM-as-a-Judge driving the
   learning loop.

### Safety / responsible design
- Student code runs in a subprocess with a hard timeout (no unbounded execution).
- All data (docs, memory) stays local to the user — nothing is uploaded anywhere
  except the LLM calls needed to reason.

## What I'd do next
Web UI with animations over an agent API, a permanent hosted endpoint via **Vertex
AI Agent Engine**, and one-click **Google Forms** export of generated quizzes.
