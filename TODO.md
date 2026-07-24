# TODO — Tailored Resume Generator

Working checklist against `PRD.md`. Organized so each item can be handed to a
fresh session/agent with just this file + `PRD.md` + `master.yaml` as context.
Check off (`[x]`) as completed; leave notes inline if an item gets partially
done or a decision changes.

## Phase 0 — Content (done)

- [x] `master.yaml` authored (profiles, experience bullets, variants, skills).
- [x] `review_flags` resolved and removed from `master.yaml`.
- [x] `PRD.md` written (pipeline, schema, validation rules, CLI, milestones).

## Phase 1 — Tech Spec (done)

- [x] **Write `TECH_SPEC.md`** — the implementation-level companion to
  `PRD.md`. PRD says *what* and *why*; this says *exactly how*, so an agent
  can implement without re-deriving decisions. Covers:
  - [x] Exact CLI argument/flag definitions and exit codes (0 = success/1-page,
    non-zero codes for: overflow, validation failure, render error — distinct
    codes so Claude's loop can branch without parsing stdout). See §1.
  - [x] **Structured output contract** — `resume-gen render`/`validate` always
    emit JSON to stdout: `{command, valid, errors: [...], page_count,
    output_files}`. See §2.
  - [x] `instance.schema.json` spec — required fields, types, id-reference
    rules, cross-field checks left to `validate.py` vs. pure JSON Schema.
    See §3.
  - [x] Jake's-resume LaTeX layout decisions: fonts (Latin Modern), margins
    (0.5in/0.6in), section order, skills-block rendering, `multinational_note`
    placement, date formatting. See §4.
  - [x] DOCX styling decisions: explicitly visually-consistent, not
    pixel-identical to the PDF — Calibri, native Word bullets, no live
    page-count check. See §5.
  - [x] Claude CLI invocation spec: Claude Code agent session (not raw API),
    no model pin, file paths passed by reference not concatenated, loop
    mechanics and 5-attempt cap. See §6.
  - [x] Dockerfile base image (`python:3.12-slim`), Tectonic static-binary
    install, non-root user, `/work` volume convention, `resume-gen` wrapper.
    See §7.

Also resolved while writing the spec (previously listed under "Gaps"):
- [x] Dependency manifest (`requirements.txt` versions) — §8.
- [x] Repo hygiene — `.gitignore` covering `output/` (gitignored, not
  committed) and Python/TeX build cruft — §9.
- [x] Versioning discipline — `schema_version` match enforced at validation
  time — §10.

## Phase 2 — Prompt (done)

- [x] **Write `prompts/tailor_resume.md`** per PRD §5: role/goal, hard rules
  (mirrored from `master.yaml`'s `authoring_rules`), profile-blending
  guidance, bullet-selection/theme-matching guidance, the instance-schema
  spec, overflow-loop instructions.
- [x] Dry-run the prompt manually (paste a real JD + master.yaml into a Claude
  session, no script yet) to sanity-check the selections it makes before any
  code depends on it. Ran against a BD/Partnerships JD: profile detection,
  per-bullet fallback to `general` when no `bd` variant exists (`win_b2b`),
  and theme-based exclusion of irrelevant bullets (`win_engagement`,
  `lg_positioning`, `ot_agile`) all worked as intended — no prompt-wording
  gaps found.

## Phase 3 — Development

- [x] `schema/instance.schema.json` (JSON Schema, from Tech Spec).
- [x] `scripts/validate.py` — locked-field verbatim check, bullet-verbatim
  check against `master.yaml`, JSON Schema structural check. Unit tests using
  `master.yaml`'s real ids/strings (including at least one deliberately
  broken instance to confirm it fails). 12 tests, all passing
  (`tests/test_validate.py`). Also added the actual `schema_version: 1.0`
  key to `master.yaml` — it previously only existed as a header comment,
  which would have made the versioning check in TECH_SPEC §10 silently
  compare against `None`.
- [x] `templates/resume.tex.j2` — Jake's-style Jinja2 LaTeX template. Uses the
  standard `\VAR{}` / `\BLOCK{}` delimiter remap (not `{{ }}`/`{% %}`) since
  those collide with LaTeX's own `{}`/`%` syntax.
- [x] `scripts/render_pdf.py` — Jinja2 render → Tectonic compile → page-count
  extraction (parses `\xdef\lastpage@lastpage{N}` from the `.aux` file).
  Escapes LaTeX special characters (`& % $ # _ { } ~ ^`) and the Unicode
  middle dot (renders as mojibake under plain T1/lmodern otherwise) on every
  string in the instance before templating.
- [x] `templates/resume_docx_style.py` + `scripts/render_docx.py`. Reuses the
  same full-time-before-part-time experience ordering as the PDF path.
- [x] `scripts/generate_resume.py` — CLI entrypoint wiring `render`/`validate`
  subcommands, structured JSON output, exit codes. Manually verified all 5
  exit codes (0 success, 1 validation failure, 2 render error, 3 overflow,
  4 usage error).
- [x] `Dockerfile` + `resume-gen` wrapper script + `requirements.txt`. Pins
  Tectonic 0.16.9 with a sha256 checksum (no official checksums file is
  published upstream, so the hash was computed from the downloaded asset
  directly — re-verify by hand if bumping the version).
- [x] **Smoke test**: user added the agent's user to the `docker` group;
  ran `docker build -t resume-gen .` (succeeded, including the Tectonic
  checksum verification) then `./resume-gen validate` and
  `./resume-gen render` against a hand-built bd-profile instance — both
  exited 0, `page_count: 1`, and produced a correct `resume.pdf`/`resume.docx`
  in `output/`. The Dockerized "no local install needed" path is confirmed
  working.
- [x] End-to-end dry run (partial, no Docker/Claude loop): built a full
  bd-profile `instance.yaml` from all 4 real `master.yaml` roles by hand,
  ran it through `render` locally (venv + a manually-downloaded Tectonic
  binary, not the Docker image). Confirmed: valid instance renders
  page_count 1 with exit 0; a deliberately broken instance fails validation
  with exit 1 and the right locked-field diff; a full-content instance
  overflows to page_count 2 with exit 3; a scripted overflow loop
  (drop lowest-priority bullet from `priority_order`, retry) correctly hits
  the 5-attempt cap and reports "cannot fit one page without further human
  trimming" when a naive drop heuristic isn't smart enough — this is
  expected, since real Claude will trim more surgically than that; it
  confirms the fallback path is reachable and correct, not a bug. Still
  outstanding: a real dry run with actual job descriptions and Claude
  driving `prompts/tailor_resume.md` end-to-end (this is Milestone 6 in
  `PRD.md`, not blocked on anything above).

## Phase 4 — One-shot launcher (Milestone 6, done)

- [x] **`resume-gen <jd-file>` end-to-end** — the wrapper now branches: a
  `render`/`validate` arg goes to the Docker renderer as before, while a
  job-description file launches a headless Claude Code session (`claude -p`,
  per TECH_SPEC §6) that reads `prompts/tailor_resume.md` + `master.yaml` + the
  JD, writes `output/<slug>/instance.yaml`, and drives the render/overflow loop
  itself. Control direction preserved: the launcher only *starts* Claude; the
  renderer never calls back into Claude.
- [x] **Milestone 6 live run** — verified on the Octapharma "Therapeutic Area
  Lead, Critical Care" JD: headless session picked profile `dm`, dropped the
  `server` role then trimmed the impact line + `win_ai`/`lg_xfn_kpi` over 4
  attempts, landed a valid one-page PDF/DOCX. Exit 0.
- [x] **Claude auth/model config** (was an open gap): auth = the user's existing
  Claude Code login (no API key); model = the session default, overridable via
  `RESUME_GEN_CLAUDE_FLAGS`. Default perms `--permission-mode acceptEdits
  --allowedTools Bash Read Edit Write` let the headless run write the instance
  and shell `resume-gen render` without prompts.

## Gaps found while compiling this list (not yet in PRD/Tech Spec — decide before or during Phase 1)

- [x] **Repo hygiene**: `.gitignore` exists and covers `output/` AND
  `master.yaml` itself — verified (2026-07-19) that neither has ever been
  committed, so no PII lives in git history. The application trail is
  local-only by design.
- [x] **Dependency manifest**: `requirements.txt` written (Phase 3 / TECH_SPEC
  §8).
- [x] **README.md**: written — quick start (Docker + no-Docker), normal
  workflow, CLI/exit-code reference, repo layout.
- [x] **Claude CLI auth/model config**: resolved in Phase 4 — user's existing
  Claude Code login, flags pinned in `resume-gen`, overridable via
  `RESUME_GEN_CLAUDE_FLAGS`.
- [ ] **Test job descriptions**: no sample JDs checked in yet for repeatable
  manual/automated dry runs — folded into Phase 5 (eval harness) below.
- [ ] **Versioning discipline**: `master.yaml` has `schema_version: 1.0` but
  the instance schema and the prompt file have no version markers — if
  `master.yaml`'s shape changes later, nothing currently forces the prompt or
  validator to be checked for compatibility. Worth a lightweight convention
  (e.g. instance.yaml echoes `schema_version` and the script asserts it
  matches what it was built against).

---

# Improvement roadmap (planned 2026-07-19)

Four phases, ordered by leverage. Each is independently shippable; 5 → 6 → 7 →
8 is the recommended order (5 and 6 share fixtures; 8 touches everything so it
goes last). Prerequisite quick wins first.

## Phase 4.5 — Quick wins (before any new phase)

- [x] **Fix the `-se` stemmer bug** in `scripts/coverage.py:_stem`: the
  sibilant check tests the *stripped stem* (`t[:-2].endswith(("s",…))`), so
  singular nouns ending in `-se` mangle their plurals — `cases → cas` but
  `case → case`; same for database/release/expense/license/purchase. Fix:
  test the token's own suffix instead — strip `es` only for
  `sses/xes/zes/ches/shes` (keeps `processes → process`, `boxes → box`,
  `matches → match`; `cases` then falls to the `-s` rule → `case`). Add these
  pairs to `test_stemmer_unifies_singular_and_plural`.
- [x] **Commit the pending working-tree changes** (coverage scorer overhaul,
  Opus 4.8 default, prompt guidance) once the stemmer fix lands, and
  **rebuild the Docker image** — `coverage.py` runs baked in the image, so
  renders keep scoring with the old code until then.
- [x] **CI**: `.github/workflows/ci.yml` — `pytest -q` on push, plus
  `docker build`. (The repo turned out to already have a GitHub remote.)
  Tests that need the private `master.yaml` skip on a fresh checkout.

## Phase 5 — Eval harness: make selection quality measurable

Motivation: the default just moved Sonnet/medium → Opus/high (≈2× cost) on the
*belief* that bullet selection improves. Nothing measures that today, and
scorer changes (like the Phase-4.5 fixes) can shift every score silently.

- [x] **Fixture JDs**: the 4 distinct real postings from
  `output/*/job_description.txt` copied into `tests/fixtures/jds/` (public
  postings — no PII concern).
- [x] **Keyphrase snapshot tests**: golden `.tsv` per fixture JD under
  `tests/fixtures/keyphrases/` (display + stems per line); regen via
  `python3 -m tests.regen_snapshots`, then review the git diff.
- [x] **`scripts/eval_run.py` + `resume-gen eval <jd> [--a …] [--b …]`**:
  run the tailor stage twice on the same JD (two model/effort settings) into
  scratch output dirs; collect per-run coverage score, render attempts,
  page-fit result, and cost (reuse `scripts/session_cost.py`); emit a
  side-by-side `eval.md` table. Answers "is Opus worth 2×?" with data.
- [x] **Optional LLM-judge** (`--judge`): headless session applies
  `prompts/eval_judge.md` to the two instances presented blind, in random
  order (candidate_1/candidate_2), and writes `judge.md`. Advisory only.
- [ ] **First live eval run**: `./resume-gen eval <jd> --judge` on a real
  posting to answer "is Opus/high worth 2×?" — not run yet (costs real
  money; user's call when).

## Phase 6 — Content-gap digest: what to add to master.yaml next

Motivation: the strategy is to raise coverage by enriching `master.yaml` with
real experience, never by gaming the scorer — but each run's `content_gap`
list currently dies in its folder.

- [x] **`scripts/gap_digest.py`** (pure stdlib + PyYAML, runs on host — no
  Docker): walks `output/*/` folders that have `job_description.txt` +
  `instance.yaml`; **recomputes** coverage against the *current* `master.yaml`
  (never parses stale `coverage.md`); aggregates `content_gap` keyphrases
  across runs by their stems. One bad folder is skipped with a stderr note,
  not fatal.
- [x] **Output `output/gap_digest.md`**: a "Recurring (≥N postings)" table —
  term, posting count, **total mention count** (real JD hits, the secondary
  rank key so an oft-repeated ask outranks a passing one), and the slugs that
  asked — then a "Seen once" list so nothing is lost. Leads with the no-faking
  guard ("a **to-write** list, not a to-fake list … only if it's truly part of
  your experience").
- [x] **Wire in**: `resume-gen gaps` subcommand (host, like `eval`) + README
  options row and explainer. Tests in `tests/test_gap_digest.py` over two
  synthetic runs under `tests/fixtures/gap_runs/` (self-contained mini bank —
  no dependency on the private `master.yaml`): recurring term ranks first with
  both slugs + mention tally, one-offs stay per-posting, covered bank terms
  never surface as standalone gaps, and the no-faking wording is present.
  6 tests; full suite 54 passing.

## Phase 7 — Application tracker: SKIPPED (2026-07-20)

A tracker app already exists as a separate local service on port 8000; the
web UI already pushes finished résumés to it (`/to-tracker` →
`http://127.0.0.1:8000/api/import`). Nothing to build here. The one idea
worth carrying over someday: an outcome-vs-coverage-score view, which
belongs in the tracker since it owns the status data.

## Phase 8 — Publishable repo: portfolio-ready without PII

Motivation: README is written as a portfolio piece but the repo can't be
shared while it assumes a private `master.yaml` beside it. Verified: neither
`master.yaml` nor `output/` was ever committed, so **no git-history rewrite is
needed** — this phase is relocation + example content only.

- [ ] **Master path indirection**: `RESUME_GEN_MASTER` env var (default
  `./master.yaml` for full back-compat) threaded through `resume-gen`, the
  tailor prompt text, and `scripts/generate_resume.py`. Real bank moves to
  e.g. `~/.config/resume-gen/master.yaml`.
- [ ] **`master.example.yaml`**: fictional persona, realistic shape (3 roles,
  2 profiles, variants, themes, skills). Must pass `validate` and render to
  one page — CI/pytest asserts this so the example never rots.
- [ ] **Sample output**: one rendered `docs/sample/` (resume.pdf +
  coverage.md from the example persona + a fixture JD) checked in so a
  visitor sees the result without running anything.
- [ ] **README polish**: swap personal references for the example persona,
  add a demo GIF/asciinema of `./resume-gen jd.txt`, keep the privacy note
  ("your real master.yaml lives outside the repo").
