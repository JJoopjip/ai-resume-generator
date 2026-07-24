# Session Handoff

**Read this first.** This file is the fast-path for any agent (or the user)
picking up work on `ai-resume-generator`. It answers "what's the state of
things and what do I do next" without re-reading the whole repo. See
`CLAUDE.md` for the hygiene rule that keeps this file trustworthy — update it
before you end your turn.

For deep context on *why* the project is shaped this way, see `README.md`
(product pitch + architecture), `PRD.md` (product spec), `TECH_SPEC.md`
(implementation spec). For the full phased task list, see `TODO.md` —
this file only summarizes the current front line.

## What's done

- Core pipeline (Phases 0–4): `master.yaml` content bank, AI tailoring prompt,
  deterministic validator/renderer (PDF + DOCX), `resume-gen` one-command
  launcher, Docker packaging. Live end-to-end run verified.
- Phase 4.5 quick wins: stemmer bug fix, CI (`pytest` + `docker build` on
  push).
- Phase 5 (eval harness): `resume-gen eval <jd> [--judge]` compares
  model/effort settings side-by-side. **Not yet run live** (costs real
  money — user's call when).
- Phase 6 (content-gap digest): `resume-gen gaps` aggregates unmatched JD
  terms across past runs into `output/gap_digest.md`. Fully tested (6 tests,
  synthetic fixtures).
- Phase 7 (application tracker): skipped — already exists as a separate
  local service; the web UI already integrates with it.
- Content additions to `master.yaml`: Thai Festival Toronto PR internship
  (pinned as always-include anchor), York University FinTech TA role
  (relevance-gated).
- **2026-07-24 security incident, resolved same day**: the real (private)
  `master.yaml` had been force-added and pushed to this public GitHub repo
  across 4 commits (`ad28b68`, `8483748`, `6e7a5e9`, and present in `46a65cb`),
  exposing the user's name, phone, email, and full work history. Remediated:
  rewrote `origin/main` history to strip `master.yaml` from every commit
  (preserving the legitimate non-master.yaml changes in those commits — the
  thaifest-anchor logic and the `gaps` digest feature both survived), force-
  pushed the clean history, and verified via a full commit-tree walk that no
  trace of `master.yaml` remains anywhere in history. `.gitignore` was also
  anchored to `/master.yaml` (root only) so it stops accidentally hiding
  synthetic test fixtures named `master.yaml` (a real bug that broke CI) —
  note this anchor does **not** prevent a deliberate `git add -f`, which is
  how the exposure happened in the first place; see `CLAUDE.md`'s working
  rules.
  - **Still open, and not this repo's to fix**: the user should make
    the GitHub repo private (github.com/JJoopjip/ai-resume-generator/settings)
    as the real backstop — force-pushing doesn't erase clones/caches made
    during the exposure window. Flag this if it comes up; don't assume it's
    done.

## What's next

Highest-leverage remaining items, in the order `TODO.md` recommends (Phase 8
last since it touches everything):

1. **Phase 5 — run a real live eval**: `./resume-gen eval <jd> --judge` on an
   actual posting to answer "is Opus/high worth 2× Sonnet/medium?" Costs
   real API/subscription usage — confirm with the user before running.
2. **Phase 8 — make the repo portfolio-publishable without PII**:
   - `RESUME_GEN_MASTER` env var for master-path indirection (default stays
     `./master.yaml` for back-compat).
   - `master.example.yaml`: fictional persona, must pass `validate` and
     render to one page (add a CI/pytest assertion so it can't rot).
   - Sample rendered output checked into `docs/sample/`.
   - README polish: swap personal references for the example persona.
3. Two small open items from the original gaps list (`TODO.md` lines ~146,
   148): checked-in sample JDs for repeatable dry runs (mostly superseded by
   the Phase 5 fixtures — verify before treating as still open), and a
   versioning-compatibility check between `master.yaml`'s `schema_version`
   and the prompt/instance schema.

Full checklist with all sub-items and completion history: **`TODO.md`**.

## Log

- **2026-07-24** — Created `CLAUDE.md` and this handoff file per user request,
  to give future agents a fast pickup path. No code changes.
- **2026-07-24** — Resolved public exposure of real `master.yaml` (see
  "What's done" above for full detail). Local `main` and `origin/main` both
  at `5fc2c0a`.
- **2026-07-24** — Local commit `640ef1f` → rebased as `5fc2c0a`: anchored
  `.gitignore`'s `master.yaml` rule to repo root, added synthetic
  `tests/fixtures/gap_runs/master.yaml` fixture the gap-digest tests need.
- **2026-07-24** — `46a65cb` (pre-rewrite): added `resume-gen gaps` command
  (Phase 6) and fixed a backtick command-substitution bug in the tailor
  prompt's TASK heredoc.
- **2026-07-23** — Added York University FinTech TA role; pinned Thai
  Festival role as an always-include anchor after a pharma-JD run dropped it.
- **2026-07-22** — Added the Thai Festival Toronto PR internship to
  `master.yaml`.
- **2026-07-20** — Phase 7 (application tracker) marked skipped — already
  exists as a separate service.
- **2026-07-19** — Phase 5 (eval harness) and Phase 6 (gap digest) built;
  CI added; stemmer bug fixed.
