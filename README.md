# Tailored Resume Generator

**A headless Claude (Anthropic) agent, wrapped in deterministic guardrails,
that turns a job posting into a polished, one-page resume — automatically.**

You give it a job description. It reads your career history, decides which of
your achievements best match that specific job, writes them up, lays them out
as a professional PDF and Word document, and checks that everything fits on one
page — trimming intelligently if it doesn't. The result is a draft ready for you
to review and send.

This is not a chatbot wrapper. There is no chat window anywhere in the loop:
Claude runs headless as an autonomous agent inside the pipeline — the same
agent technology that powers AI coding tools — reading files, running the
renderer, and reacting to its verdicts on its own.

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

### Cover letters (optional)

Some postings want a cover letter; most don't. So it's **opt-in** — a plain
`./resume-gen jd.txt` run stays fast and makes only the resume. When you want a
letter, you have two ways:

```sh
./resume-gen jd.txt --cover                    # resume + cover letter, one run
./resume-gen cover-letter output/<folder>      # add a letter to a resume you already made
```

The second form is handy when you generate resumes in bulk and only later decide
which few postings deserve a letter — it reuses that folder's `instance.yaml` and
job description, so it never re-does the resume. Either way you get a matching
`cover_letter.pdf` / `cover_letter.docx` beside the resume: same letterhead, one
page, grounded only in what the resume already claims, and written to mirror the
target company's culture.

### Options (the short version)

| What you want to do | Command |
|---------------------|---------|
| Generate a resume from a job posting | `./resume-gen jd.txt` |
| Generate a resume **and** a cover letter | `./resume-gen jd.txt --cover` |
| Add a cover letter to a resume you already made | `./resume-gen cover-letter output/<folder>` |
| Use the most powerful AI for a high-stakes application | see below |
| Just re-build the PDF from an existing draft (no AI) | `./resume-gen render --instance output/<folder>/instance.yaml` |
| Check a draft is valid without building anything | `./resume-gen validate --instance output/<folder>/instance.yaml` |
| Compare two AI settings head-to-head on one posting | `./resume-gen eval jd.txt` (see below) |
| See which skills to add to your bank next | `./resume-gen gaps` (see below) |

**Dialing the AI down for a routine application.** By default the tool uses the
most capable model (Opus 4.8, high effort) — bullet selection is the one
judgment call nothing downstream can repair. To roughly halve the cost on a
routine posting, drop to the lighter setting:

```sh
RESUME_GEN_CLAUDE_FLAGS="--model claude-sonnet-5 --effort medium \
  --permission-mode acceptEdits --allowedTools Bash Read Edit Write" ./resume-gen jd.txt
```

**Is the expensive model actually better?** Measure instead of guessing:
`./resume-gen eval jd.txt` runs the tailor stage twice on the same posting (by
default Sonnet/medium vs Opus/high — both cost real money), then writes a
side-by-side `output/eval-<jd>-<date>/eval.md` comparing coverage, page fit, and
cost. Add `--judge` for a blind AI preference read (`judge.md`) that scores the
two drafts without knowing which model made which.

**What should I add to my experience bank next?** Every run records the JD terms
your `master.yaml` has nothing on. `./resume-gen gaps` walks every past run,
re-scores each against your *current* bank, and writes
`output/gap_digest.md` — the terms ranked by how many postings wanted them (with
the mention count and which postings asked). It's a **to-write** list, not a
to-fake list: add a recurring term only if it's genuinely part of your
experience — the score is a keyword screen, never a reason to invent content.

**One-time setup.** The AI step uses the `claude` command-line tool (it signs in
with your existing Claude account — no separate API key needed). The build step
runs inside Docker, so you don't have to install anything technical yourself —
just build the toolbox once:

```sh
docker build -t resume-gen .
```

The image bakes in the build code (the LaTeX template, renderer, and validator),
so **re-run `docker build -t resume-gen .` after changing anything under
`templates/` or `scripts/`** — otherwise the container keeps running the old copy.

**Where the money goes.** Each AI run now drops a `cost.json` in its
`output/<slug>/` folder — estimated token spend and cost for that run (read from
the headless session), plus its final JD-coverage score. Set `RESUME_GEN_NO_COST=1`
to skip it.

**If your Claude subscription lapses.** The two halves of the pipeline depend on
different things:

- **Building/re-rendering an existing draft never needs AI or a subscription.**
  `render`, `validate`, and the cover-letter `cover` renderer run entirely inside
  Docker (Tectonic) — they never call Claude. Any resume you've already generated
  stays fully usable: re-render it, hand-edit its `instance.yaml` and re-render,
  or render a cover letter from an existing `cover_letter.yaml`, all offline.
- **Generating a *new* AI-tailored resume needs the `claude` CLI to be signed
  in.** With no active subscription, either renew, or point the CLI at a
  pay-per-use API key instead of the account login:

  ```sh
  export ANTHROPIC_API_KEY=sk-ant-...   # the CLI uses this instead of your account
  ./resume-gen jd.txt
  ```

  API billing is roughly **$1 per resume** (a bit more with `--cover`), so for
  occasional job-search use it's often cheaper than a subscription.

---

## 2. What this project actually does

This is a portfolio piece demonstrating **AI orchestration** — designing a
pipeline where a headless Claude agent does the judgment-heavy creative work, while
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
master.example.yaml            # fictional persona — what a fresh clone renders
master.yaml                    # YOUR real content bank (git-ignored; not in this repo)
docs/sample/                   # a rendered sample (PDF + coverage) from the example
prompts/
  tailor_resume.md             # the instruction manual for the AI (resume)
  tailor_cover_letter.md       # ditto for the optional cover letter
schema/                        # formal definitions of a valid draft & layout
scripts/
  generate_resume.py           # command-line entry point (render / validate / cover)
  validate.py                  # the fact-checking guardrail
  render_pdf.py                # draft → typeset PDF + page count
  render_docx.py               # draft → editable Word document
  render_cover_letter.py       # cover letter → matching PDF + Word
templates/                     # the LaTeX + Word styling (resume & cover letter)
tests/                         # automated checks against real content
Dockerfile, resume-gen         # packaging & the one-command launcher
output/                        # generated resumes (kept off git — contains personal info)
PRD.md, TECH_SPEC.md           # the plain-English specs I wrote first
```

> **Your data stays out of the repo.** The real content bank — `master.yaml`,
> with your name, phone, email, and full history — is **git-ignored and never
> committed**. It lives beside the repo by default, or anywhere you point
> `RESUME_GEN_MASTER` (e.g. `~/.config/resume-gen/master.yaml`). What ships in
> this public repo is `master.example.yaml`, a fully fictional persona, so the
> project is safe to browse, clone, and share. `output/` is git-ignored too
> (generated resumes carry contact details).
>
> **Try it without any setup:** everything runs against the example out of the
> box —
>
> ```bash
> ./resume-gen validate --instance docs/sample/instance.yaml --master master.example.yaml
> ./resume-gen render   --instance docs/sample/instance.yaml --master master.example.yaml --out docs/sample
> ```
>
> A pre-rendered result is checked in at [`docs/sample/resume.pdf`](docs/sample/resume.pdf).
