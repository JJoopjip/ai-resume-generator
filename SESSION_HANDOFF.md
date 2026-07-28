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
  model/effort settings side-by-side. **Run live 2026-07-28** on two JDs.
  Low-match `jd.txt` (3 configs): identical output across all tiers — model
  changed only cost/speed. High-match `jd_highmatch.txt` (`--judge`): Opus/high
  made a better selection (blind judge 19 vs 16). **Outcome shipped:** kept
  Opus/high default, added `--fast` (Sonnet 5/medium) for routine/bulk/low-match
  runs, dropped Opus/medium (worst value). See `resume-gen` model note + Log.
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
  earlier output-mined stopgap. See Log. Also: an out-of-repo auto-synced backup
  now exists — see [[never-delete-master-yaml]] and `CLAUDE.md` working rules.
- **Phase 8 done (2026-07-28)**: repo is now portfolio-publishable without PII.
  `RESUME_GEN_MASTER` env indirection (default `./master.yaml`), fictional
  `master.example.yaml` + `docs/sample/` rendered sample, `tests/test_example_master.py`,
  README privacy/"try it" polish. Real bank stays git-ignored. See Log + `TODO.md`.
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

Highest-leverage remaining items:

1. **Phase 5 — DONE + decided + shipped (2026-07-28).** Two evals settled the
   model default. Low-match JD (`jd.txt`): all tiers produce identical output →
   Opus/high wasteful there. High-match JD (`jd_highmatch.txt`, `--judge`):
   Opus/high made a measurably better selection (blind judge 19 vs 16; kept a
   quantified bullet Sonnet/medium dropped). **Decision: keep Opus/high as the
   default; added a `--fast` flag (Sonnet 5/medium) for routine/bulk/low-match
   runs; Opus/medium not offered (worst value).** Implemented in `resume-gen`
   (arg pre-scan + tier block), README, TECH_SPEC §6. No open follow-ups here.
   Reports: `output/eval-run{1,2}-*-2026-07-28/`, `output/eval-jd_highmatch-2026-07-28/`.
2. **Phase 8 leftover (optional)**: a demo GIF/asciinema of `./resume-gen jd.txt`
   for the README. The rest of Phase 8 is done (see What's done). Also possible:
   actually relocate the real bank to `~/.config/resume-gen/master.yaml` via
   `RESUME_GEN_MASTER` (indirection is wired; the move itself is untaken).
3. Two small open items from the original gaps list (`TODO.md` lines ~146,
   148): checked-in sample JDs for repeatable dry runs (mostly superseded by
   the Phase 5 fixtures — verify before treating as still open), and a
   versioning-compatibility check between `master.yaml`'s `schema_version`
   and the prompt/instance schema.

Full checklist with all sub-items and completion history: **`TODO.md`**.

## Log

- **2026-07-28 (latest)** — **Model default decided + `--fast` flag shipped.**
  After the two evals (identical output on low-match `jd.txt`; Opus/high
  judge-preferred on high-match `jd_highmatch.txt`), kept Opus/high as the
  default and added `--fast`/`RESUME_GEN_FAST=1` → Sonnet 5/medium for
  routine/bulk/low-match runs (~60% cheaper, ~20% faster, identical output on
  low-match). Opus/medium deliberately not offered (measured worst value).
  `resume-gen`: added an arg pre-scan (rotate loop strips `--fast` from `$@` in
  any position, preserving order/spaces) + a FAST-conditional model-flags block;
  `RESUME_GEN_CLAUDE_FLAGS` still overrides everything. Verified: default→opus/high,
  `--fast`→sonnet/medium (incl. with `--cover` and in any position), override
  wins. Docs synced (README table + "dialing down"; TECH_SPEC §6, which was
  stale — still claimed sonnet/medium was the default). Launcher-only change,
  no baked scripts/templates touched → no Docker rebuild. `pytest` 58 passed.
- **2026-07-28** — **Eval judge run on high-match JD** (`jd_highmatch.txt`,
  the Brand & BD Manager posting). Scored two locked-fact drafts in
  `output/eval-jd_highmatch-2026-07-28/` → `judge.md`. **Verdict: candidate_2**
  (16 vs 19). Decider: c2 keeps `win_engagement` ("100% growth in online
  engagement... 10K+ followers"), covering the JD's named digital-campaign duty
  with quantified proof; c1 drops it for `win_ceo`/`ot_access` (qualitative,
  partly redundant), leaving no digital-marketing evidence. This is follow-up
  (b) from What's-next #1 — the fair `--judge` eval on a high-match JD.
- **2026-07-28** — **Tailored run: Brand & Business Development Manager,
  Consumer Health (high-match JD `jd_highmatch.txt`).** Profile `bd` (blending
  `dm` variants for the brand/DTC/retention bullets). Output
  `output/consumerhealthco-brand-bd-manager-2026-07-28-opus-4-8-high/` → **1 page**
  (exit 0, lines_free 1 / slack 19.7pt — tight). First render overflowed 2 pages
  / ~12 lines; in one edit dropped the `server` additional role, `win_portfolio`,
  `lg_xfn_kpi`, `ot_access`, and trimmed `thaifest` to 1 bullet → 1 page. Final:
  thaifest×1, winnergy×3 (b2c/engagement/retention), lgchem×2, otsuka×1, boots×1;
  highlights engagement/retention/skus. Coverage 52% (13/25); selection_gap
  (supply chain, launching/end-to-end product, commercial performance) left
  uncovered — already conceptually covered by lg_sourcing/ot_launch and no
  room/no better verbatim swap. `profile.suggested` pm 62 vs bd 58 (4-pt gap,
  kept bd — JD core is brand/BD/DTC). Draft only; not submitted.
- **2026-07-28** — **Tailored run: Metrolinx, Project Coordinator, Rail
  Corridor Extensions (Kitchener Corridor, GO Expansion).** Profile `pm`
  (`profile.suggested` agrees, pm 52 highest of 40/52/42/47). Output
  `output/metrolinx-project-coordinator-2026-07-28/` → **1 page** (exit 0,
  lines_free 1 / slack 19.2pt — tight). First render overflowed by 7 lines;
  cut `win_team`+`win_ceo`, `lg_stakeholders`, `ot_access` in one edit → still
  3 lines over; cut `win_portfolio` in a second edit → 1 page. Final: 5 roles /
  7 bullets — thaifest(1: tf_partnerships), winnergy(1: win_b2c), lgchem(2:
  lg_sourcing, lg_xfn_kpi), otsuka(2: ot_launch, ot_regulatory), boots(1:
  boots_frontline); highlights hl_experience + hl_gpa; no projects section
  (dropped for space, JD doesn't reward tooling/systems work). `yorkta` (FinTech
  TA) omitted — no relevance to a civil/rail JD. Coverage 20% (5/25);
  `selection_gap` was generic noise ("during", "go expansion") not worth
  chasing with only 1 line free; `content_gap` is Metrolinx/rail-specific
  vocabulary (railway corridor, civil engineering, construction) the bank has
  nothing on — left uncovered per the truthfulness guard. Cover letter
  (`cover_letter.yaml`) rendered 1 page on the first attempt — mirrors
  Metrolinx's public-sector/mission register (equity, "serving with passion,
  thinking forward, playing as a team"), leans on `ot_launch` (scope/schedule/
  budget, on-time, full regulatory compliance) and `lg_sourcing`/`lg_xfn_kpi`
  (contract negotiation, cross-functional coordination, KPI reporting) as
  proof, and the current `thaifest` role (multi-stakeholder partnership
  coordination, Toronto-based) for culture fit. Both PDFs are drafts pending
  human review.
- **2026-07-28** — **First live eval run (Phase 5), 3 configs on `jd.txt`.**
  Ran the harness twice (2-arm limit) with opus/high as the shared anchor:
  sonnet/medium vs opus/high, then opus/medium vs opus/high. All four runs
  selected the identical resume (7/25 bullets, 5/7 roles, 12% coverage 3/25,
  22 content gaps, 1 page, pm profile) — so model/effort changed only cost &
  speed here, not content. Cost: sonnet/medium $1.38, opus/medium $3.32,
  opus/high $3.70–3.73. Wall: 4m17s / 4m42s / 5m34s–5m59s. Tokens all ~2M
  (turn-count/context-reread dominated, not model). Takeaways: sonnet/medium
  = 63% cheaper + 35% faster for identical output; opus/medium = worst value
  (kill it); the real lever on this JD is the 22 content gaps, not the model
  (see [[raise-coverage-by-enriching-master]]). Caveat: single low-coverage JD,
  no `--judge`. Reports under `output/eval-run{1,2}-*-2026-07-28/`. Handoff
  "What's next" updated with the default-flip decision (awaiting user).
- **2026-07-28** — **Tailored run (opus-4-8-high): CSA Group, Project
  Manager – Health Care & Well-being (12-mo contract, bilingual EN/FR).** Profile
  `pm` (`profile.suggested` agrees, pm 59 highest). Output
  `output/csa-group-project-manager-2026-07-28-opus-4-8-high/` → 1 page (exit 0,
  lines_free 2 / slack 27pt). First render overflowed by ~13 lines; one big §6
  edit dropped `server` (additional role), the `highlights` block, `win_ceo`,
  `lg_sourcing`, `ot_regulatory`, and trimmed `thaifest` to its single strongest
  bullet → 1 page, 4 lines free. With real room and `selection_gap` empty, added
  `ot_regulatory` back (verbatim) since it directly hits this JD's core
  ("standards development", "health & safety standards", compliance) → still
  1 page, 2 lines free. Final: 5 roles / 7 bullets — thaifest(1: tf_infrastructure),
  winnergy(2: win_b2c, win_portfolio), lgchem(1: lg_xfn_kpi), otsuka(2: ot_launch,
  ot_regulatory), boots(1); no highlights. Coverage reads 12% but that's the
  bilingual-JD artifact again (content_gap = French stopwords); selection_gap
  empty, no term-swap. Resume-only (no cover letter requested). Draft only, not
  submitted. Note: distinct from the earlier `csagroup-…` (no hyphen) opus-4-8
  medium/high + sonnet-5 runs for this same posting.
- **2026-07-28** — Tailored-application run for the Toronto Transit
  Commission's "Operational Planner" posting (Operational Safety and Planning
  dept.) at `output/ttc-operational-planner-2026-07-28/`. Profile `pm` (JD is
  construction-project scheduling/rehab coordination — no direct domain overlap
  in `master.yaml`, but scope/schedule/budget + regulatory-compliance + MS
  Project/scheduling-software language transfers cleanly; `profile.suggested`
  agreed, pm 67 highest). `thaifest` trimmed to its single strongest bullet
  (`tf_partnerships`, per §3b "JD unrelated" branch) since this JD is
  ops/construction, not marketing/PR — chose the stakeholder-coordination
  variant over `tf_infrastructure` as more transferable. `yorkta` skipped
  (FinTech-only, no relevance). First render overflowed by 12 lines — in one
  edit dropped `server` (additional role, first per §6), then the
  lowest-priority bullet from each multi-bullet role (`ot_access`, `win_ceo`,
  `lg_stakeholders`) plus the `highlights` block (low-cost trim, §6 step 3) →
  1 page, exit 0, 3 lines free. Final: 5 roles / 7 bullets — otsuka(2:
  ot_launch, ot_regulatory), winnergy(2: win_b2c, win_portfolio), lgchem(1:
  lg_xfn_kpi), boots(1), thaifest(1); no highlights selected in the final cut.
  Coverage 12%/thin — `content_gap` is almost entirely TTC-specific/hiring-
  process boilerplate the bank has nothing on; `selection_gap` terms ("ai
  tool", "processes", "service") were generic/low-value or ironic to chase
  (the JD explicitly **prohibits AI-tool use in application materials** — see
  flag below) — no swap made. Cover letter (pm-grounded, mirrors TTC's
  public-sector/measured/mission-driven "Moving Toronto, Connecting
  Communities" register) rendered 1 page on the first attempt. Both
  `resume.pdf` and `cover_letter.pdf` draft-ready; not submitted anywhere.
  **Flagged to user in the report:** this specific JD's fine print bars use of
  any AI tool to generate submitted materials/responses and could disqualify
  an application that uses them — the human should weigh this carefully
  before using this draft as a starting point, independent of the repo's
  standing "draft for human review" rule.
- **2026-07-28** — **Tailored run (medium): CSA Group, Project Manager – Health
  Care & Well-being.** Profile `pm`. Output
  `output/csagroup-project-manager-2026-07-28-opus-4-8-medium/` → 1 page (exit 0,
  lines_free 0 / slack 9.5pt). First render overflowed 2 pages (~7 lines over);
  one §6 pass (dropped `server` additional role + `lg_stakeholders` +
  `win_portfolio`… then restored `win_portfolio` to keep hl_skus reinforced,
  cut `lg_stakeholders`+`server`) landed it. Final: 5 roles / 7 bullets —
  thaifest(1), winnergy(2: win_b2c, win_portfolio), lgchem(1: lg_xfn_kpi),
  otsuka(2: ot_launch, ot_regulatory), boots(1); highlights hl_experience +
  hl_gpa + hl_skus. Coverage 12% is the bilingual-JD artifact again
  (content_gap = French stopwords); selection_gap empty, no swap. Draft only.
  Mirrors the earlier opus-4-8-high run closely (that one used 2 highlights, no
  hl_skus/win_portfolio); sonnet-5-medium run also exists for this posting.
- **2026-07-28** — **Tailored run: CSA Group, Project Manager – Health Care &
  Well-being (12-mo contract, bilingual EN/FR posting).** Profile `pm`. Output
  `output/csagroup-project-manager-2026-07-28-opus-4-8-high/` → 1 page (exit 0,
  slack 9.5pt). First render overflowed 2 pages (~12 lines over); one §6 cut
  pass (dropped `server` additional role, then `win_ceo`, `tf_infrastructure`,
  `lg_sourcing`) landed it. Final: 5 roles / 7 bullets — thaifest(1),
  winnergy(2), lgchem(1), otsuka(2), boots(1); highlights hl_experience +
  hl_gpa. Coverage reads 12% but that's a bilingual-JD artifact (content_gap is
  mostly French stopwords); `selection_gap` empty, no worthwhile swap. Draft
  only. Note: a prior sonnet-5-medium run for the same posting already exists
  (`csagroup-projectmanager-2026-07-28-sonnet-5-medium`).
- **2026-07-28 (night, later)** — **Built Phase 8 — repo is now portfolio-
  publishable without PII.** (1) `RESUME_GEN_MASTER` env indirection: default
  still `./master.yaml`, threaded through `scripts/generate_resume.py` +
  `scripts/gap_digest.py` (env-aware `--master` default) and `resume-gen`
  (launcher `MASTER` var used in the agent prompt + Docker `-e` passthrough).
  (2) `master.example.yaml`: fictional "Robin Ellery Santos", 4 roles (1
  `additional:true`), all 4 profiles, per-bullet variants+themes, summaries,
  highlights, skills, projects. (3) `docs/sample/`: hand-tailored pm-profile
  `instance.yaml` + fixture `job_description.txt`, rendered to `resume.pdf`/
  `.docx` + `coverage.md` (exit 0, 1 page, 14 lines free, 68% coverage). (4)
  `tests/test_example_master.py` (4 tests: shape, no-real-PII tripwire, sample
  validates, JD coherence) — full suite 58 passed. (5) README: repo-layout +
  privacy note rewritten to the example-persona reality + a copy-paste "Try it
  without any setup" block. Real `master.yaml` confirmed still git-ignored/
  untracked throughout. `TODO.md` Phase 8 checked off.
- **2026-07-28 (night)** — Tailored-application run for Metrolinx's "Junior
  Project Coordinator, Environmental Programs and Assessment (EPA)" posting
  (Toronto, public-sector transit agency) at
  `output/metrolinx-junior-project-coordinator-2026-07-28/`. No domain overlap
  in `master.yaml` (no environmental/civil-engineering content) — profile `pm`
  chosen as closest angle (scope/schedule/budget, regulatory compliance,
  contractor/vendor/stakeholder coordination all transfer conceptually; JD's
  own `profile.suggested` agreed, pm 52 highest). thaifest included at 2
  bullets per §3b ("stakeholder/vendor coordination" JD-relevant category);
  `yorkta` skipped (FinTech-only, no relevance). First render overflowed by 13
  lines — cut `server` (additional role, first per §6). Second render still 7
  over — cut `win_ceo`, `lg_sourcing`, `tf_infrastructure` (lowest-priority per
  role) in one edit. Third render 3 over — cut `ot_access`. Fourth render: 1
  page, exit 0, `lines_free: 0` (no slack). Coverage 16%/thin — `content_gap`
  is almost entirely environmental-domain vocabulary (`environmental
  assessments`, `mitigation`, `transit`, etc.) the bank genuinely has nothing
  on; the two `selection_gap` terms ("assessment", "project assessment") had
  no room to swap for anyway. Cover letter (pm-grounded, mirrors Metrolinx's
  public-sector/mission-driven "passion, forward thinking, playing as a team"
  register) rendered 1 page on the first attempt — dropped a claimed metric
  (20,000+ attendees) from the culture paragraph mid-draft because the bullet
  carrying it (`tf_outreach`) wasn't in the final `instance.yaml`, only
  `tf_partnerships` was — a reminder to double check every letter claim against
  the *final* (post-overflow-cut) instance, not just the master bank. Both
  `resume.pdf` and `cover_letter.pdf` draft-ready; not submitted anywhere.
- **2026-07-28 (evening, later)** — Tailored-application run for AstraZeneca's
  "Project Manager, GBS Project Services" posting (Mississauga, ON) at
  `output/astrazeneca-project-manager-2026-07-28/`, this time off the recovered
  **real** `master.yaml` (not the 07-24 reduced-bank run). Profile `pm` (JD is
  project/change-management + customer service in pharma; `profile.suggested`
  agrees, pm 53). First render overflowed by 12 lines; in one edit cut `server`
  (additional role, first per §6) plus the lowest-priority bullet of each
  multi-bullet role (`tf_partnerships`, `win_team`, `lg_stakeholders`,
  `ot_agile`) → 1 page, exit 0, 3 lines free. Swapped `lg_stakeholders` back
  (verbatim) to cover the customer-engagement/stakeholder `selection_gap` → still
  1 page, 1 line free. Final: 7 bullets across thaifest/winnergy/lgchem/otsuka/
  boots. Remaining gap terms generic ("services", "collaboration") / boilerplate
  `content_gap` — no further swap. Cover letter (pm-grounded, mirrors AZ's
  collaborative/communities-of-practice/patient-mission tone) rendered 1 page on
  the first attempt. Both `resume.pdf` and `cover_letter.pdf` draft-ready; not
  submitted anywhere.
- **2026-07-28 (evening)** — Tailored-application run for Attix Pharmaceuticals'
  "Sales Manager, Inside Sales" posting (`output/attix-pharmaceuticals-sales-manager-2026-07-28/`).
  Profile `bd` (JD is pharma-distribution sales-team leadership + revenue/pipeline
  targets — closest fit even though the automated `profile.suggested` reads `pm`,
  scores were flat: bd 46 / pm 51 / dm 50 / general 49, not a real disagreement).
  First render overflowed by 10 lines; cut `server` (additional role, first per
  §6), `win_ceo`, `lg_intelligence`, `ot_clinical`, `tf_infrastructure` in one
  edit → 1 page, exit 0, `lines_free: 0` (essentially no slack left). Coverage
  16%/thin — `content_gap` was almost entirely job-posting boilerplate (benefits,
  "bachelor's degree", company name) master.yaml has nothing on, and the one
  `selection_gap` term ("time") wasn't worth chasing per §6 guidance — no swap
  made. Cover letter (bd-grounded, mirrors Attix's results-driven/team-development
  tone) rendered 1 page on the first attempt. Both `resume.pdf` and
  `cover_letter.pdf` are draft-ready for human review; not submitted anywhere.
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
