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
- **`master.yaml` restored (2026-07-28)**: recovered the genuine original from
  Claude Code session transcripts (`~/.claude/projects/.../*.jsonl`) — 7 roles,
  25 bullets, 80 variants, full `dm` angle, plus `authoring_rules`/`profiles`/
  `projects`. This is the real thing, not a reconstruction; supersedes the
  earlier output-mined stopgap. See Log.
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

- **2026-07-28 (later)** — **Recovered the genuine original `master.yaml` from
  Claude Code session transcripts.** User asked to look through old
  conversations where they'd built the master. Scanned all 81 `*.jsonl`
  transcripts under `~/.claude/projects/-home-joopjip-resume-generator/`,
  extracted every embedded master block, and scored each by how many of the 10
  past instances it validates + richness. Best = `b9187442-…jsonl` (2026-07-23):
  **7 roles** (adds `yorkta` + a full 8-bullet `winnergy` the mined version
  lacked), **25 bullets, 80 variants incl. full `dm` angle**, plus
  `authoring_rules`, `profiles` (bd/pm/dm/general), 4 `summaries`, 6
  `highlights` (incl. dm-only `hl_followers`/`hl_engagement`), 8 skill groups,
  `projects`, languages. Validates 8/10 past instances; the 2 that don't are the
  **07-24 runs, which were themselves generated from the lossy reconstructed
  bank (not the real master)** — so those instances are the off ones, master is
  authoritative. Adopted this as `master.yaml` (git-ignored, untracked),
  replacing the output-mined stopgap below. This is a strict superset of it.
  Not truncated (parses fully, all 12 sections complete). **Nothing invented —
  every byte is the user's own prior content.** Next: re-run the AstraZeneca
  tailor (Docker up now; render stage needs it).
- **2026-07-28** — Output-mined stopgap reconstruction of `master.yaml` (later
  superseded by the transcript recovery above). Merged the partial
  `output/general-resume-2026-07-24/_content_bank.yaml` with real bullets from
  all 10 past `output/*/instance.yaml` runs, verbatim. Gave 6 roles / 17
  bullets / 33 variants, no `dm`. Kept in history as the fallback method if
  transcripts are ever unavailable.
- **2026-07-28** — Re-themed the web UI (`web/templates/index.html`) from the
  sage-green "matches the tracker" palette to a pastel-pink **"Blush Rosé"**
  theme, so the resume generator reads as visually distinct from the
  Fieldnotes tracker (:8000, still sage). Renamed the CSS `--sage*` tokens to
  `--pink*` (primary `#C4657F`, strong `#A24862`, tint `#F8E2EA`), retinted the
  neutrals to warm blush, updated the favicon fill + header comment. Scope was
  **web UI only** by the user's choice — the resume/cover-letter PDF+DOCX
  accent stays maroon `#7A2E2E`, so **no Docker rebuild** was needed. App
  serves the template from disk per-request, so the change is live on reload.
- **2026-07-25** — Full-repo health/effectiveness review (no code changes).
  Tests green (31 passed, 23 skipped). No bugs found in validate/coverage/
  render/launcher — code is clean and well-commented. Confirmed two standing
  gaps, both = Phase 8: (a) `master.yaml` still absent from this checkout, so
  tailoring can't run normally; (b) 23/54 tests skip for lack of a checked-in
  master, so the core guardrails (validate.py, coverage.py) get **no real-data
  assertions in CI** — a `master.example.yaml` fixture fixes both the CI gap
  and portfolio-publishability at once. Also: eval harness still never run
  live, so AI-selection quality remains unmeasured. Recommended next step:
  Phase 8 `master.example.yaml`.
- **2026-07-24** — Tailored a resume + cover letter for AstraZeneca's
  "Project Manager, GBS Project Services" posting (Mississauga, ON) at
  `output/astrazeneca-projectmanager-2026-07-24/`. Real `master.yaml` is
  **still absent** from this checkout (see below), so this run reused the
  same reduced, verbatim-only content bank a prior session reconstructed at
  `output/general-resume-2026-07-24/_content_bank.yaml` (via
  `--master` override on `render`; `cover` doesn't take `--master`, it reads
  the letterhead from `instance.yaml` directly). Profile: `pm`. Resume hit
  2-page overflow on first render (~3 lines over) — cut `win_portfolio`
  (Winnergy) per §6, re-rendered to 1 page (exit 0, coverage 36%, no
  worthwhile selection-gap swap available given the thin bank). Cover letter
  rendered 1 page on first attempt (exit 0). **Open:** real `master.yaml`
  still missing — every tailored run until it's restored is working off the
  reduced bank (single `default` bullet variant only, no `bd`/`pm`/`dm`
  angles, no `server`/`projects`), so coverage and bullet selection are
  weaker than the pipeline is designed for. Restoring it is the top blocker
  for normal operation.
- **2026-07-24** — User asked for a general (un-tailored) resume. Discovered
  `master.yaml` is **absent from this checkout** (pipeline can't render without
  it). Reconstructed a small content bank from real data in past
  `output/*/instance.yaml` runs (verbatim, nothing invented) at
  `output/general-resume-2026-07-24/_content_bank.yaml`, wrote a `general`-profile
  `instance.yaml`, and rendered one-page PDF+DOCX via
  `resume-gen render --instance … --master …`. Dropped the part-time Boots role
  to fit one page. **Open:** real `master.yaml` still missing — restore it to
  get the normal tailoring pipeline working again.
- **2026-07-24** — User asked to create `CLAUDE.md` + this handoff; both already
  existed and satisfy the ask, so nothing was recreated. Re-verified the
  `master.yaml` remediation holds (untracked, absent from history bar the
  synthetic test fixture, `.gitignore` anchored). Repo visibility still
  **UNVERIFIED** — `gh` not authed here; user must confirm/set the repo private.
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
