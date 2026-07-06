# Tailored Resume Generator

**An AI orchestration pipeline that turns a job posting into a polished, one-page resume — automatically.**

You give it a job description. It reads your career history, decides which of
your achievements best match that specific job, writes them up, lays them out
as a professional PDF and Word document, and checks that everything fits on one
page — trimming intelligently if it doesn't. The result is a draft ready for you
to review and send.

---

## 1. How to use it

The whole thing is one command. Save a job posting into a text file, then run:

```sh
./resume-gen jd.txt
```

That's it. A few minutes later you'll find a finished resume here:

```
output/<company>-<role>-<date>/
    ├── resume.pdf     ← the resume, ready to review
    ├── resume.docx    ← an editable Word copy (for recruiters / job boards)
    ├── instance.yaml  ← exactly what the AI chose, in plain text
    ├── omitted.md     ← what it left OUT, and why (so you can add things back)
    └── job_description.txt  ← a copy of the posting, for your records
```

> **The output is always a draft for a human to review** — nothing is ever sent
> anywhere automatically.

### Options (the short version)

| What you want to do | Command |
|---------------------|---------|
| Generate a resume from a job posting | `./resume-gen jd.txt` |
| Use the most powerful AI for a high-stakes application | see below |
| Just re-build the PDF from an existing draft (no AI) | `./resume-gen render --instance output/<folder>/instance.yaml` |
| Check a draft is valid without building anything | `./resume-gen validate --instance output/<folder>/instance.yaml` |

**Dialing the AI up for an important application.** By default the tool uses a
fast, cost-effective model. For your dream job, switch to the most capable one:

```sh
RESUME_GEN_CLAUDE_FLAGS="--model claude-opus-4-8 --effort high \
  --permission-mode acceptEdits --allowedTools Bash Read Edit Write" ./resume-gen jd.txt
```

**One-time setup.** The AI step uses the `claude` command-line tool (it signs in
with your existing Claude account — no separate API key needed). The build step
runs inside Docker, so you don't have to install anything technical yourself —
just build the toolbox once:

```sh
docker build -t resume-gen .
```

---

## 2. What this project actually does

This is a portfolio piece demonstrating **AI orchestration** — designing a
pipeline where an AI agent does the judgment-heavy creative work, while
deterministic (non-AI) software does the exact, repeatable work, and the two
hand off to each other cleanly.

I'm not a software developer by trade. I built this through **spec-driven /
"vibe" coding with AI assistance**: I wrote the product spec (`PRD.md`) and
technical spec (`TECH_SPEC.md`) in plain English, then directed an AI coding
assistant to implement them. The specs are in this repo — they're as much a part
of the work as the code, and they show how I break a fuzzy goal into a system an
AI can build reliably.

**The core design idea: split the brain from the machine.**

- **The AI does what only an AI can do well** — reading a job posting, judging
  which of my past achievements are relevant, choosing the right framing for
  each one, and writing a fitting summary. This is fuzzy, context-dependent
  work.
- **Plain software does what must be exact and repeatable** — laying out the
  page, enforcing that nothing was invented or exaggerated, counting pages, and
  producing the files. **No AI runs inside this step**, so the output is fast,
  cheap, reproducible, and shareable with anyone.

Crucially, the AI is kept on a tight leash. It can *select and reorder* facts
but is mechanically blocked from *rewriting* them — every number, job title,
date, and company name is checked character-for-character against my master
record before anything renders. If the AI drifts, the pipeline rejects its work
and tells it exactly what to fix. This is the interesting part of AI
orchestration: **not just calling an AI, but building guardrails that let you
trust the result.**

### The "self-correcting loop" — orchestration in action

The most illustrative piece is how the two halves talk to each other:

```
   Job posting
       │
       ▼
 ┌──────────────────────┐   The AI reads my whole career history,
 │  AI agent (Claude)    │   picks the achievements that fit THIS job,
 │  — makes the choices  │   writes a summary, and produces a draft.
 └──────────┬───────────┘
            │  hands the draft to ↓
            ▼
 ┌──────────────────────┐   1. Fact-checks every locked detail verbatim
 │  Renderer (no AI)     │   2. Builds the PDF + Word file
 │  — enforces the rules │   3. Counts the pages
 └──────────┬───────────┘
            │  reports back ↑ (pass / fail / too long)
            ▼
   One page?  ── No ──▶  The AI drops its own lowest-priority
       │ Yes             achievement and tries again (up to 5 times)
       ▼
   Finished draft
```

The AI drives this loop itself: it calls the renderer, reads the verdict, and
reacts — fixing a rejected fact, or trimming the least-important bullet point
when the resume runs long. It even ranks its own choices *ahead of time* so the
trimming order is deliberate, not random. The renderer never calls the AI back;
control flows in one direction, which keeps the system predictable.

---

## 3. How it's built (architecture)

Two clearly separated halves, connected by a simple contract.

### The AI half — judgment

| Piece | What it is |
|-------|------------|
| `master.yaml` | My entire career history in one file: every achievement, written in several "angles" (business development, project management, digital marketing) so the AI can pick the framing that best matches a given job. Locked facts (numbers, titles, dates) live here as the single source of truth. |
| `prompts/tailor_resume.md` | The instruction manual I wrote for the AI — how to read a job posting, how to choose and rank achievements, what it's forbidden from doing. Plain English, editable without touching code. |
| `resume-gen` (top of the script) | Launches the AI agent for a job and lets it run unattended. |

### The deterministic half — exactness (no AI)

| Piece | What it does |
|-------|--------------|
| `scripts/validate.py` | The guardrail. Checks the AI's draft against `master.yaml` — every locked fact must match exactly, or the pipeline refuses to build. |
| `scripts/render_pdf.py` | Turns the draft into a professionally typeset PDF (using a LaTeX template) and counts the pages. |
| `scripts/render_docx.py` | Produces the editable Word version for recruiters and job-board uploads. |
| `schema/` | Formal definitions of what a valid draft and a valid layout look like. |
| `Dockerfile` | Packages the whole build step into a self-contained "toolbox" so it runs identically on any machine, with nothing to install. |

### The contract between them

The two halves communicate through **exit codes and a single line of
structured data** — a deliberately simple, unambiguous handshake:

- `0` = success, and it fits on one page
- `1` = the AI got a fact wrong (rejected — here's which one)
- `3` = valid, but the resume is too long (the AI needs to trim)

Because the verdict is machine-readable, the AI can react to it on its own
without a human in the loop.

### The specs

- **`PRD.md`** — the product spec: what this tool is for and why, in plain
  language.
- **`TECH_SPEC.md`** — the technical spec: every implementation decision, written
  before the code so an AI assistant could build to it without guessing.

These two documents are the backbone of how I work with AI: **think it through
in writing first, then direct the build.**

---

## 4. For the technically curious

- **Stack:** Python 3.12 (PyYAML, Jinja2, python-docx, jsonschema), a LaTeX
  template compiled by [Tectonic](https://tectonic-typesetting.github.io/),
  all wrapped in Docker. The AI step is a headless [Claude
  Code](https://claude.com/claude-code) agent session.
- **Running without Docker** (needs Python 3.12+ and a Tectonic binary on
  `PATH`):
  ```sh
  pip install -r requirements.txt
  python3 scripts/generate_resume.py render --instance instance.yaml --master master.yaml --out output/
  ```
- **Tests:**
  ```sh
  pip install -r requirements.txt pytest
  python3 -m pytest tests/ -q
  ```
- **Full CLI reference, exit-code contract, and the JSON output shape** are in
  `TECH_SPEC.md` §1–2.

### Repository layout

```
master.yaml                    # career content bank — the single source of truth
prompts/tailor_resume.md       # the instruction manual for the AI
schema/                        # formal definitions of a valid draft & layout
scripts/
  generate_resume.py           # command-line entry point (render / validate)
  validate.py                  # the fact-checking guardrail
  render_pdf.py                # draft → typeset PDF + page count
  render_docx.py               # draft → editable Word document
templates/                     # the LaTeX + Word styling
tests/                         # automated checks against real content
Dockerfile, resume-gen         # packaging & the one-command launcher
output/                        # generated resumes (kept off git — contains personal info)
PRD.md, TECH_SPEC.md           # the plain-English specs I wrote first
```

> **A privacy note:** `output/` is deliberately kept out of git because generated
> resumes contain personal contact details. Note that `master.yaml` itself holds
> a phone number and email in plain text — keep any copy of this repo private.
