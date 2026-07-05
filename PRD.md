# PRD — Tailored Resume Generator

## 1. Problem & Goal

Chantamas maintains a single master content bank (`master.yaml`) containing every
fact, bullet, and phrasing variant from her career, tagged by profile
(`bd` / `pm` / `dm` / `general`) and by theme keyword. Today, tailoring a resume
to a specific job description is a manual copy-paste-and-edit exercise.

**Goal:** a command-line tool that takes a job description as input, uses the
Claude CLI to select and lightly rephrase content from `master.yaml` according
to its own `authoring_rules`, and produces a one-page PDF and DOCX resume —
without ever calling an LLM inside the rendering step itself. Content selection
is Claude's job; layout, validation, and file production are a deterministic
Python script's job. This split keeps rendering reproducible, fast, cheap, and
shareable with anyone (not just Claude Code users).

## 2. Non-Goals

- No auto-submission of resumes to job boards.
- No cover-letter generation (future phase, not in this PRD).
- No web UI — CLI only.

## 3. Pipeline Overview

```
job_description.txt
        │
        ▼
┌───────────────────────┐
│ Claude CLI (agent)     │  reads job_description.txt + master.yaml
│ - picks a profile      │  (or blends), selects bullets per role by
│   theme match, resolves│  each bullet's chosen `variants[profile]`,
│   rephrasable prose    │  orders skills/summary, writes:
│   (summary only)       │
└───────────┬───────────┘
            ▼
   output/<company>-<role>-<date>/instance.yaml   (resume-instance schema, §4)
            │
            ▼
┌───────────────────────────┐
│ generate_resume.py (script)│  1. Validates instance.yaml against master.yaml
│  deterministic, no LLM     │     (locked fields verbatim, bullets exist in
│  calls                     │     master.yaml's variants — see §7)
│                             │  2. Renders LaTeX (Jinja2 template) → Tectonic
│                             │     → resume.pdf
│                             │  3. Renders resume.docx from the same
│                             │     instance.yaml (python-docx)
│                             │  4. Reports PDF page count back to caller
└───────────┬───────────────┘
            ▼
   page_count == 1?  ──No──▶ Claude drops the lowest-priority bullet(s)
        │Yes                 from instance.yaml, re-invokes the script
        ▼                    (loop, capped at N retries)
   output/<company>-<role>-<date>/
       ├── job_description.txt   (copy, for the audit trail)
       ├── instance.yaml
       ├── resume.pdf
       └── resume.docx
```

Claude Code (or any Claude CLI session) drives the loop by calling the script
repeatedly; the script itself never calls out to an LLM.

## 4. Resume-Instance Schema (Claude's output / script's input)

YAML, same shape as `master.yaml` but fully resolved — no `variants`, no
`themes`, one string per bullet, plus explicit ordering.

```yaml
schema_version: 1.0
profile: bd                      # or a note if blended across profiles
job_description_ref: job_description.txt
meta: { ...copied verbatim from master.yaml... }
summary: "..."                    # rephrased prose, profile-appropriate
experience:
  - id: winnergy                  # must match an id in master.yaml
    company: ...                  # copied verbatim (locked field)
    location: ...
    title: ...
    start: ...
    end: ...
    bullets:                      # ordered list of resolved strings, subset only
      - id: win_b2c
        text: "Opened the company's first B2C channel from scratch, ..."
      - id: win_retention
        text: "Sustained a 90% repeat-order rate ..."
education: [ ...copied verbatim, ordering may change... ]
certifications: [ ... ]
skills:
  - label: "Business Development & Partnerships"
    items: [ ... ]                # subset/reorder of master.yaml items only
languages: [ ... ]                # copied verbatim
priority_order:                    # per-role bullet ids in ascending priority,
  winnergy: [win_ai, win_b2b, win_engagement, ...]   # lowest-priority first —
  lgchem: [...]                                       # this is what gets cut
  otsuka: [...]                                       # first on overflow
  boots: [...]
```

Why this shape: it's a direct filter/resolve of `master.yaml`, so the
verbatim-diff validation in §7 is a straightforward id + string lookup, and
it's human-skimmable before rendering (matches the "DRAFT for human review"
hard rule already in `master.yaml`).

`priority_order` is required so the overflow loop (§8) has a deterministic,
Claude-authored cut order instead of the script guessing what to drop.

## 5. Master Prompt (`prompts/tailor_resume.md`)

The instructions that drive Claude's content-selection step live in their own
plain-markdown file, versioned in git alongside `master.yaml` — not embedded
in a script string or a Claude Code skill definition. This keeps it something
Chantamas can read top-to-bottom and edit without touching code, and lets it
evolve independently of the render pipeline.

**Single file, clear sections**, in this order:

1. **Role & goal** — "You are tailoring a resume from a fixed content bank to
   a specific job description. You select and lightly rephrase; you never
   invent."
2. **Hard rules** — a restatement of `master.yaml`'s `authoring_rules`
   (locked fields, rephrasable fields, the four hard rules) so the rules are
   visible in the prompt itself, not just cross-referenced.
3. **Profile guidance** — how to read a JD and decide which of bd/pm/dm/general
   each bullet and the summary should draw from.
4. **Bullet-selection guidance** — matching JD language/keywords against each
   bullet's `themes` tags; how many bullets per role is reasonable; how to
   order them within a role.
5. **Output schema spec** — the exact `instance.yaml` shape (§4), including
   the required `priority_order` field.
6. **Overflow-loop instructions** — what to do when `resume-gen render`
   reports >1 page (§8): drop from `priority_order`, re-render, cap at 5
   attempts.

**Profile blending:** Claude is instructed to choose the best-fitting variant
independently for *each* bullet and the summary, rather than committing to one
profile label for the whole resume — this is what `master.yaml`'s per-bullet
`variants` structure is already built for. The chosen profile is still
recorded in `instance.yaml`'s `profile` field as a label of the dominant
angle (for the tagline/summary and file naming), even when individual bullets
draw from a different profile's variant.

## 6. CLI Interface

Single Python entry point, Dockerized so "anybody can use it" without a local
Tectonic/LaTeX/Python setup.

```
docker run --rm -v $(pwd):/work resume-gen \
  render --instance output/acme-pm-2026-07-05/instance.yaml \
         --master master.yaml \
         --out output/acme-pm-2026-07-05/

docker run --rm -v $(pwd):/work resume-gen \
  validate --instance output/acme-pm-2026-07-05/instance.yaml \
           --master master.yaml
```

- `render`: validates, then produces `resume.pdf` + `resume.docx`, prints the
  resulting page count (and a non-zero exit code if page count > 1, so Claude's
  loop can detect overflow from the exit code alone).
- `validate`: validation only (§7), no rendering — useful as a fast fail before
  spending render time.
- A thin wrapper script (`resume-gen`) shells into the Docker image so the
  invocation reads like a normal CLI tool, not a raw `docker run`.

Claude CLI's job in the loop is: write `job_description.txt` → prompt itself
with `master.yaml` → write `instance.yaml` → shell out to `resume-gen render`
→ read exit code / page count → if overflow, drop the next id from
`priority_order`, rewrite `instance.yaml`, retry (cap at, say, 5 iterations,
then surface a "content doesn't fit, needs manual trim" message).

## 7. Validation Rules (script-enforced, no LLM involved)

On every `render`/`validate` call, before touching LaTeX:

1. **Locked fields verbatim** — for every experience/education/certification
   entry, `company`, `location`, `title`, `start`, `end`, `degree`, `detail`,
   metrics-bearing substrings must string-match `master.yaml` exactly for that
   `id`. Mismatch → hard fail, script refuses to render.
2. **Bullets exist verbatim** — every bullet `text` in `instance.yaml` must
   equal some `variants[*]` value for that bullet `id` in `master.yaml`
   (any profile's variant is acceptable — Claude may mix profiles across
   bullets, e.g. bd wording for one role, pm wording for another — but the
   string itself must be unaltered). Mismatch → hard fail.
3. **Summary is exempt** from verbatim matching (it's the one `rephrasable`
   field per `authoring_rules`), but the script still checks it doesn't
   contain any of `master.yaml`'s locked numeric tokens in an altered form —
   out of scope for v1 beyond a manual review nudge.
4. **One-page check** happens after LaTeX compiles, via Tectonic's page count
   (or a `\pageref{LastPage}` marker in the template) — output as part of
   `render`'s result.

Failures print which id/field mismatched and the expected vs. actual string,
so Claude can self-correct on the next write of `instance.yaml`.

## 8. Overflow / One-Page Loop

- `instance.yaml` carries `priority_order` per role (lowest priority first).
- On `render` reporting >1 page, Claude removes the next-lowest-priority
  bullet id (across roles, using its own judgment on which role can most
  afford to lose one) from that role's `bullets` list, and re-runs `render`.
- Loop caps at 5 attempts; after that, script/Claude reports "cannot fit
  one page without further human trimming" rather than silently shrinking
  fonts/margins (`master.yaml`'s hard rule: "drop bullets, don't shrink
  facts" — extends here to "don't shrink fonts/margins either").

## 9. Directory Structure

```
resume_generator/
├── master.yaml
├── PRD.md
├── Dockerfile
├── prompts/
│   └── tailor_resume.md       # master prompt driving Claude's selection step (§5)
├── templates/
│   ├── resume.tex.j2          # Jake's-style Jinja2 LaTeX template
│   └── resume_docx_style.py   # python-docx styling constants
├── scripts/
│   ├── generate_resume.py     # CLI entrypoint (render / validate subcommands)
│   ├── validate.py            # §7 logic
│   ├── render_pdf.py          # Jinja2 → .tex → tectonic → .pdf
│   └── render_docx.py         # instance.yaml → .docx via python-docx
├── schema/
│   └── instance.schema.json   # JSON Schema for instance.yaml structural checks
└── output/
    └── <company>-<role>-<date>/
        ├── job_description.txt
        ├── instance.yaml
        ├── resume.pdf
        └── resume.docx
```

## 10. Tech Stack

- Python 3.12, dependencies: `pyyaml`, `jinja2`, `python-docx`, `jsonschema`.
- Tectonic (self-contained LaTeX engine) inside the Docker image — no host
  TeX distribution required.
- Single `Dockerfile` bundling Python + Tectonic; `resume-gen` shell wrapper
  for ergonomics.

## 11. Milestones

1. **Schema + validation** — `instance.schema.json`, `validate.py` (§7 rules 1-2),
   unit tests against `master.yaml`'s current content.
2. **PDF render path** — Jake's-style `.tex.j2` template, Tectonic integration,
   page-count reporting.
3. **DOCX render path** — `render_docx.py` from the same `instance.yaml`.
4. **Dockerize** — `Dockerfile`, `resume-gen` wrapper, smoke test on a clean
   machine (no local TeX/Python needed).
5. **Master prompt + Claude-side loop** — write `prompts/tailor_resume.md`
   (§5); a Claude CLI invocation that loads it, reads a JD, drafts
   `instance.yaml` with `priority_order`, invokes `resume-gen render`,
   handles overflow retries, surfaces validation failures for self-correction.
6. **Dry run** — end-to-end test with 2-3 real job descriptions across
   different profiles (bd/pm/dm), human review of resulting PDFs/DOCXs.
