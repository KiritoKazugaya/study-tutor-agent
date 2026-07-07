# 2–3 minute demo video script

Record your screen (Windows: **Win + Alt + R** with Xbox Game Bar, or use Loom).
Keep it tight — judges watch a lot of these.

**0:00–0:20 — The pitch (talk over your face-cam or a title slide)**
> "Students have tons of notes but no tutor who knows their material and their weak
> spots. Study Tutor is a multi-agent assistant that reads your own documents,
> quizzes you four ways, grades you, and remembers what you keep getting wrong."

**0:20–0:40 — Architecture (show the README diagram)**
> "A Coordinator agent routes to three specialists — Summarizer, QuizMaster, and an
> Evaluator that acts as an LLM-as-a-Judge — plus tools for documents and a code
> runner, and a persistent memory of weak topics. That's four course concepts:
> multi-agent, tools, memory, and evaluation."

**0:40–1:10 — Live: summarize**
- Run `python main.py`, pick option 2 (show Biology subject + doc), then option 3.
- Let the Summarizer produce notes. Say: "It read my uploaded notes and produced
  exam-ready summary + common mistakes."

**1:10–2:00 — Live: quiz + grading + memory**
- Option 4 → `mcq`. Answer one or two **wrong on purpose**.
- Then option 5 (progress) — show the weak topic got recorded.
- Run option 4 again — point out "Personalising around your weak topics…".
> "The loop closes: it remembers my weakness and targets it next time."

**2:00–2:30 — The coding round (the wow moment)**
- Option 4 → `coding`. Paste a short solution, type END.
- Show it running the code and the Evaluator scoring it.

**2:30–2:45 — Close**
> "Everything runs on the free Gemini tier. Next: a web UI and a permanent hosted
> endpoint on Vertex AI Agent Engine. Thanks for watching."

Tips: increase terminal font size before recording; have the sample Biology subject
ready; pre-write one correct + one wrong answer so you don't stall on camera.
