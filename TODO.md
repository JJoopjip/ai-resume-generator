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

- [ ] **Repo hygiene**: no `.gitignore` yet. `output/` will contain generated
  PDFs/DOCXs/instance files per application — decide whether these are
  committed (application audit trail) or gitignored (repo stays clean, trail
  lives only locally). `master.yaml` itself contains PII (phone, email) —
  confirm this repo is/stays private before any push to a remote, especially
  if it's ever made public or shared.
- [ ] **Dependency manifest**: PRD lists packages (`pyyaml`, `jinja2`,
  `python-docx`, `jsonschema`) but there's no `requirements.txt`/`pyproject.toml`
  yet — needed before the Dockerfile can be written.
- [x] **README.md**: written — quick start (Docker + no-Docker), normal
  workflow, CLI/exit-code reference, repo layout.
- [ ] **Claude CLI auth/model config**: PRD doesn't yet say which Claude
  model/version the tailoring step should invoke, or how API auth is
  supplied (env var, config file) — needs to land in the Tech Spec.
- [ ] **Test job descriptions**: no sample JDs checked in yet for repeatable
  manual/automated dry runs — worth adding 2-3 real (or realistic) JDs across
  bd/pm/dm profiles to `tests/fixtures/` or similar.
- [ ] **Versioning discipline**: `master.yaml` has `schema_version: 1.0` but
  the instance schema and the prompt file have no version markers — if
  `master.yaml`'s shape changes later, nothing currently forces the prompt or
  validator to be checked for compatibility. Worth a lightweight convention
  (e.g. instance.yaml echoes `schema_version` and the script asserts it
  matches what it was built against).
