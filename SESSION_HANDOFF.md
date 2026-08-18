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
- **Web UI redesign (2026-07-28)**: `web/templates/index.html` rebuilt as a
  two-column working screen (paste box on top, five named steps instead of a
  raw log, file list with page count/size, right rail with JD coverage / page
  fit / cost, collapsible agent log, Drafts tab). `web/app.py` gained the
  metric readers behind it (`_page_count`/`_coverage`/`_cost`/`_run_meta`,
  `GET /drafts`) and a `?tier=` switch (`best` = Opus/high, `fast` =
  Sonnet/medium) — the page has to set the model itself because
  `RESUME_GEN_CLAUDE_FLAGS` overrides the launcher's own tier. Same palette,
  same routes otherwise.
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
- **Selection-gap summary nudge (2026-08-17)**: added §4 guidance to
  `prompts/tailor_resume.md` — before finalizing the summary, check the JD's
  top terms against near-misses (present in a sibling profile's summary
  variant or elsewhere in `master.yaml`, just phrased out of the chosen one)
  and prefer working them in over losing them to a rewrite. Applies to both
  tiers (`--fast` only swaps model, not prompt). Verified live on
  `output/sentrex-stakeholder-partnerships-lead-2026-08-17/instance.yaml`:
  reworded the `bd` summary to keep "industry" (present in `sum_dm` for the
  same fact) → JD coverage 32%→40% (8→10 of 25 terms), re-rendered, still 1
  page (~1 line free). See Log.

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
2. **`coverage.py` tokenizer fix (NEW, 2026-07-28 — highest-leverage bug).**
   Hyphenated/closed compounds are single tokens, so real matches score as
   misses and one ("medical devices") is wrongly reported as a *content* gap.
   Proposed: in `token_set()`/`tokens()`, emit a compound both whole and split
   on its internal punctuation ("market-share" → market-share, market, share),
   and add a closed-compound fold so "healthcare" also yields health+care.
   JD-side extraction stays as-is. Regression risk is low (it only ever adds
   tokens to the bag) but `tests/test_coverage.py` snapshots will move — regen
   via `tests/regen_snapshots.py`. Verified against
   `output/abbott-associate-product-manager-2026-07-28/`: 8/25 → 12/25.
3. **Teach the tailoring prompt the cross-profile variant lever (NEW,
   2026-07-28).** `validate.py:194` accepts *any* variant of a bullet id, but
   `prompts/tailor_resume.md` (~line 66) only permits leaving the chosen
   profile when that profile has **no** variant. The Abbott re-fit showed
   re-picking a variant that already exists under another profile is a free,
   truthful coverage gain (3 swaps ≈ +4 terms). Proposed wording: allow picking
   any variant when it materially better matches the JD's own language, with
   the chosen profile still the default — and require `omitted.md` to record
   the swap (which variant, why), as the Abbott run now does.
   **Discussed with user 2026-07-28; sharpened, not yet written.** Note the
   prompt contradicts itself today: §2 line 58 says "decide per bullet
   independently", line 66 frames cross-profile as a *fallback only*. Fix both
   together. Agreed shape = **anchor with justified exceptions**: dominant
   profile is the default for every bullet; deviate only when the other variant
   carries a fact/metric the JD explicitly asks for (not synonym-level gains);
   prefer `general` over a rival angle (neutral register, no seam); cap ~1/3 of
   bullets and never two adjacent bullets in one role from different profiles
   (voice whiplash is most visible there); summary stays anchored (§4 already
   allows sentence-level blending there — that's the right place for it).
   Rationale the scorer can't see: variants carry *different metrics*, not just
   different wording (`master.example.yaml:88` — pm "4 engagement stages",
   bd "12 new relationships", dm "35% sign-up lift"), so a keyword-driven swap
   silently changes which achievement the reader sees, and can break §4a's
   "highlights should reinforce a selected bullet" rule. **Open decision:**
   user was offered an A/B (one JD, strict-single-profile vs cherry-picked,
   compare coverage + read both PDFs) to set the cap empirically — awaiting
   go-ahead before touching the prompt. **User said yes to the A/B (2026-07-28),
   on a real JD they need anyway so no tokens are spent on a throwaway.**
   Method agreed — costs *one* paid run: pay for the normal tailor run, then
   derive both arms from its `instance.yaml` by mechanically re-picking variants
   (arm A = force dominant profile, `general` only where absent; arm B = per
   bullet, whichever variant best matches the JD) and `resume-gen render` each
   (no-LLM subcommand, writes its own `coverage.md`). Selection is held
   constant so the variant dial is the only variable; both arms stay
   `validate`-clean since they only substitute real variants of the same id.
   Watch for arm B overflowing to 2 pages (longer variants) — that's a finding.
   Pick a **hybrid** posting; a single-angle JD makes both arms identical and
   the test says nothing. **A/B RUN 2026-07-28 — result in, and it argues
   AGAINST keyword-driven swapping.** JD: `output/abbott-product-manager-2026-07-28/`
   (Abbott Diabetes Care, consumer *digital* PM — website/CRO/GA4/SEO).
   Arm A = the paid run itself, which happened to be a clean strict control
   (`profile: dm`, dm variant on all 7 bullets that have one, `general` only for
   `boots_frontline` which has no dm). Arm B = greedy re-pick of every bullet's
   variant to maximize `coverage.py`'s score, selection/summary/highlights/skills
   held identical; built free via `resume-gen render` (script:
   `$CLAUDE_JOB_DIR/tmp/build_arm_b.py`), output `…-armB/`, validate clean, 1 page,
   2 lines free. **A 6/25 (24%) → B 8/25 (32%).** But both gained terms are
   junk: `conversion` comes from `boots_frontline`'s bd variant ("sales
   conversion" — retail pharmacy, not digital CRO), and `conversion rate` is a
   pure artifact — "conversion" from that Boots bullet + "rate" from
   `win_retention`'s bd variant ("90% repeat-order **rate**"), two unrelated
   bullets at two different companies. Meanwhile the `win_retention` dm→bd swap
   made the resume *substantively worse*: dm reads "customer retention …
   customer-facing content across product launches", bd reads "repeat-order rate
   across **hospital and clinic accounts**" — B2B institutional, the wrong
   direction for a JD about "consumer facing digital ecosystem" and "authentic
   consumer connections". So the scorer moved +8 pts while the resume got worse.
   **Conclusion: implement the anchor-with-exceptions rule as specified above,
   and make the exception test "the variant carries a fact the JD asks for",
   explicitly NOT "the swap raises coverage."** Caveat before over-generalizing:
   this JD is a poor match (15 of 25 terms are *content* gaps — GA4, Adobe
   Analytics, CMS, SEO/GEO, automation platforms), so the variant dial had little
   real work to do here; the earlier `abbott-associate-product-manager` re-fit
   did get a genuine +4 from 3 swaps. One JD, one data point.
4. **`coverage.py` has no adjacency requirement (NEW, 2026-07-28, found during
   the A/B).** `Keyphrase.covered_by` (`coverage.py:159`) is
   `all(s in bag for s in self.stems)` against a **whole-resume** token bag, so a
   multi-word phrase counts as covered when its words appear in unrelated bullets
   — "conversion rate" scored as covered off "conversion" in a pharmacy bullet
   plus "rate" in a retention bullet. This is what makes the score gameable and
   is distinct from the tokenizer fix in item 2 (that one *adds* tokens; this one
   needs proximity/adjacency, e.g. match bigrams within a single bullet's token
   sequence rather than bag-wide). Fix both before trusting coverage deltas as
   evidence for anything.
5. **Web UI follow-ups (from the 2026-07-28 redesign)**: the new screen has not
   yet been driven through a *real* (paid) run — it was verified with a stub
   pipeline, so eyeball the step list and the rail on the next genuine
   generation. **2026-08-17: the same real-run check should specifically cover
   a `--fast`/Sonnet run that overflows**, to confirm the new page-count gate
   (see Log) actually fires — it's only been exercised with a synthetic 2-page
   `resume.aux` so far, not a live overflow-cap run. Two ideas deliberately
   left unbuilt, in priority order:
   (a) a live page-one preview that fills in while the agent writes (the
   highest-value idea from the design deck — needs a mid-run render or an
   `instance.yaml` parse); (b) an optional dark "developer view" showing the
   raw trace with per-step timings, useful when tuning prompts.
6. **Phase 8 leftover (optional)**: a demo GIF/asciinema of `./resume-gen jd.txt`
   for the README. The rest of Phase 8 is done (see What's done). Also possible:
   actually relocate the real bank to `~/.config/resume-gen/master.yaml` via
   `RESUME_GEN_MASTER` (indirection is wired; the move itself is untaken).
7. Two small open items from the original gaps list (`TODO.md` lines ~146,
   148): checked-in sample JDs for repeatable dry runs (mostly superseded by
   the Phase 5 fixtures — verify before treating as still open), and a
   versioning-compatibility check between `master.yaml`'s `schema_version`
   and the prompt/instance schema.

Full checklist with all sub-items and completion history: **`TODO.md`**.

## Log

- **2026-08-17** — **Coverage: close free selection gaps via summary wording.**
  User asked whether all matched JD keywords can fit on one page. Investigated
  `coverage.py`'s selection_gap vs content_gap split on a live run
  (sentrex-stakeholder-partnerships-lead): 3 of 25 unmatched terms were
  selection gaps, 2 real (`industry`, `industry relationships` — the `bd`
  summary dropped a word the `dm` summary kept for the same fact), 1 a false
  positive from `coverage.py`'s bag-of-words matching (`client meetings`
  matched an unrelated `yorkta` bullet's "meeting each deadline", not real
  content — left alone, not a real gap). Fixed the 2 real ones by rewording
  that instance's summary (kept truthful, no new claims) and added durable
  guidance to `prompts/tailor_resume.md` §4 so future runs catch this
  automatically. Re-rendered: 32%→40% coverage, still 1 page. `master.yaml`
  untouched (this was a wording fix, not a content-gap fix).
- **2026-08-17** — **Cover letter: AppLovin, Business Development Associate.**
  Wrote `cover_letter.yaml` grounded only in that run's `instance.yaml` →
  `resume-gen cover` exit 0, **1 page** on first render. Addressee "Hiring
  Team" (JD names no manager). Mirrored AppLovin's fast-moving, "win together /
  support of others", big-data culture in framing only; narrated the from-
  scratch B2C channel build (20+ SKUs, 100% engagement / 10K+ followers, 90%
  repeat-order rate) and the LG Chem market-intelligence/KPI through-line — all
  metrics verbatim from the instance, no new claims. Draft for human review,
  not submitted. `master.yaml` untouched.

- **2026-08-17** — **Tailored run: AppLovin, Business Development Associate
  (Toronto, Consumer/ad-tech performance-marketing team).** Output
  `output/applovin-business-development-associate-2026-08-17/` → **1 page**
  (exit 0, lines_free 0 / slack 9.5pt — tight). Profile **bd** (title-driven;
  `profile.suggested` leaned dm 46 vs bd 41, close/flat — kept bd for the
  "Business Development Associate" title match, pulling `dm` variants for the
  Winnergy e-commerce/campaign bullets since the JD explicitly rewards
  Consumer/e-commerce experience and data-driven campaign work). First render
  overflowed 2 pages (~7 lines over) from a 12-bullet/5-role first pass; one
  edit cut the lowest-priority bullet from each of thaifest/winnergy/lgchem/
  otsuka (`tf_outreach`, `win_portfolio`, `lg_sourcing`, `ot_clinical`) → 1
  page, exit 0. `server` (additional role) was never included even in the
  first pass — omitted from the start to stay lean, consistent with it being
  the lowest-priority content and the final page having 0 lines free. Final:
  5 roles / 8 bullets — thaifest(1: tf_partnerships), winnergy(3: win_b2c,
  win_engagement, win_retention), lgchem(2: lg_intelligence, lg_xfn_kpi),
  otsuka(1: ot_access), boots(1: boots_frontline); highlights hl_engagement/
  hl_retention/hl_skus; no projects. `yorkta` (FinTech TA) never selected —
  no relevance to an ad-tech/consumer BD posting. Coverage 32% (8/25);
  `selection_gap` empty; `content_gap` is almost entirely AppLovin-specific
  boilerplate (compensation language, company name, "own right" culture
  copy) the bank has nothing on — left uncovered per the truthfulness guard.
  `omitted.md` written. Draft only, not submitted. `master.yaml` untouched.
- **2026-08-17** — **Web UI: close the "fast tier can silently ship a 2-page
  resume" gap.** User asked to guarantee one-page output even under `--fast`.
  Root cause: `web/app.py`'s `_run_pipeline` gated `result["ok"]` on the
  `claude` CLI's own exit code only — but that code reflects whether the
  headless session *completed*, not whether the §6 overflow-trim loop actually
  reached one page (`tailor_resume.md` caps at 5 attempts and, if still >1
  page, just reports that in text — `resume-gen`'s exit code is `claude`'s raw
  `$rc`, per `resume-gen`'s `run_claude_and_log`). `scripts/eval_run.py`
  already knew not to trust that exit code for page count — it re-derives
  `page_count` from a deterministic re-render instead. Applied the same fix to
  the web UI: `_run_pipeline` now reads the real page count via the existing
  `_page_count()` (parses `resume.aux`'s `\lastpage@lastpage`) and only marks
  `ok: true` when it's 1; on overflow it emits an explicit log line and the
  frontend (`web/templates/index.html`) shows a distinct "Couldn't fit one
  page" card instead of quietly offering a 2-page download. Verified
  `_page_count` parsing against a synthetic 2-page `resume.aux` (returns `2`)
  and `python3 -m py_compile web/app.py`; **not yet exercised against a real
  overflow-cap run** (see What's next item 5) since that needs a paid `--fast`
  session that genuinely can't fit one page. Files: `web/app.py`,
  `web/templates/index.html`.
- **2026-08-17** — **Tailored run + cover letter: Sentrex Health Solutions,
  Stakeholder Partnerships Lead (PSP business development, Canada-wide travel).**
  Output `output/sentrex-stakeholder-partnerships-lead-2026-08-17/` → **1 page**
  resume (exit 0, lines_free 1 / slack 19.7pt) + **1 page** cover letter (exit 0,
  first attempt). Profile **bd** (JD is pure BD/partnerships: pharma
  manufacturer relationships, RFP positioning, conference/industry engagement,
  CRM & pipeline reporting, executive-level relationship building —
  `profile.suggested` disagreed, general 77/pm 73 highest, bd 72 close behind;
  kept bd since the JD's substance is textbook partnerships/BD, not PM
  delivery). First render overflowed 2 pages (~12 lines over) from a 12-bullet/
  6-role first pass; one edit dropped `server` (additional role, first per §6)
  + the lowest-priority bullet from thaifest/winnergy/lgchem/otsuka
  (`tf_outreach`, `win_ceo`, `lg_intelligence`, `ot_clinical`) → 1 page, exit 0.
  Final: 5 roles / 7 bullets — thaifest(1: tf_partnerships), winnergy(2:
  win_b2c, win_b2b), lgchem(2: lg_sourcing, lg_stakeholders), otsuka(1:
  ot_access), boots(1: boots_frontline); highlights hl_experience (7 yrs) +
  hl_retention (90%); no projects. `yorkta` (FinTech TA) never selected — no
  relevance. Coverage 32% (8/25); remaining `selection_gap` ("client meetings",
  "industry relationships", "industry") is thin/generic and there was only 1
  line of room, so no swap made. `content_gap` is almost entirely
  Sentrex/PSP-specific boilerplate (patient support programs, capability
  presentations, company name) the bank has nothing on. Cover letter mirrors
  Sentrex's "proudly Canadian", patient-outcomes-mission, collaborative
  register — proof paragraph leans on `win_b2c`/`win_b2b` (channel + B2B
  partner sourcing) and `lg_sourcing`/`lg_stakeholders` (international partner
  sourcing, account growth), reinforced by the 90% retention highlight; fit
  paragraph connects her Toronto-based `thaifest` partnerships work + two
  multinational pharma employers to Sentrex's cross-border PSP work. All
  metrics verbatim. `omitted.md` written. Both PDFs draft-only, not submitted.
  `master.yaml` untouched.
- **2026-08-12** — **Cover letter: University of Toronto, Special Projects
  Consultant (University HR) — ONE PAGE, exit 0 first render.** Wrote
  `output/university-of-toronto-special-projects-consultant-2026-08-12/cover_letter.yaml`
  grounded only in that folder's `instance.yaml`. Addressee "Hiring Team" (JD
  names no manager, only the AVP UHR office). Public-sector/institutional
  register: measured, service-oriented prose mirroring the JD's political
  acuity / discretion / consensus-among-senior-stakeholders signal. Proof =
  Otsuka end-to-end launch (scope/schedule/budget across R&D, regulatory, mfg,
  marketing, on time in full compliance) + LG Chem KPI business reviews →
  stakeholder decisions; metrics verbatim (seven years, GPA 3.9, up to CEO
  level). 1 render attempt, `cover_letter.pdf` (+docx) on disk. DRAFT.
- **2026-08-12** — **Tailored run: University of Toronto, Special Projects
  Consultant (University HR) — reached ONE PAGE.** Output
  `output/university-of-toronto-special-projects-consultant-2026-08-12/`. Profile
  **pm** (`profile.suggested` agrees, pm 60). JD is a PM-heavy HR admin role
  (project charters/work plans/milestone tracking, governance, risk & issue
  mgmt, change mgmt, research, dashboards, PMP preferred). Render 1: 6 roles /
  9 bullets incl. `server`, 2 pages (~5 lines over); one edit dropped `server`
  (§6.1) + trimmed thaifest to `tf_infrastructure` → 1 page, 2 lines free
  (coverage 24%); swapped `lg_intelligence` in verbatim (research/analysis
  evidence the JD rewards) → still 1 page, 0 lines free, exit 0. Final: thaifest
  (tf_infrastructure) / winnergy (win_b2c, win_portfolio) / lgchem (lg_xfn_kpi,
  lg_intelligence, lg_stakeholders) / otsuka (ot_launch) / boots (boots_frontline);
  highlights 7 yrs + GPA 3.9. `omitted.md` written. 3 render attempts. DRAFT.
- **2026-08-12** — **Tailored run: Pharma Medica Research (PMRI), Project
  Manager — reached ONE PAGE.** Output
  `output/pharmamedica-project-manager-2026-08-12/` (new slug; distinct from the
  earlier `pmri-project-manager-2026-08-12` cap-stop below). Profile **pm**
  (`profile.suggested` agrees, pm 44). Same CRO PM JD. **Leaner first pass than
  the prior run** — 6 roles / 10 bullets on render 1 (~9 lines over, not 18);
  one edit dropped `server` + `win_ceo` + `lg_stakeholders` + `ot_regulatory`
  → 1 page, 2 lines free (coverage 32%); swapped `win_ceo` back in verbatim to
  cover `selection_gap` "progress" (JD's core = keeping clients informed of
  trial progress) → still 1 page, 1 line free, coverage 36%. 3 renders total,
  exit 0. Final: 5 roles / 7 bullets — thaifest(1: tf_infrastructure),
  winnergy(3: win_b2c, win_portfolio, win_ceo), lgchem(1: lg_xfn_kpi),
  otsuka(1: ot_launch), boots(1: boots_frontline); highlights hl_experience/
  hl_gpa/hl_skus; no server, no projects. Remaining `selection_gap` "research"
  left uncovered (only ot_clinical carries it, ~2.5 lines, no room — generic
  single word per §6). `resume.pdf` + `resume.docx` current; `omitted.md`
  written. Draft only, not submitted. `master.yaml` untouched.
- **2026-08-12** — **Tailored run: Pharma Medica Research (PMRI), Project
  Manager (clinical trials / CRO, client-facing).** Output
  `output/pmri-project-manager-2026-08-12/` → **stopped at the 5-attempt cap,
  still 2 pages (~3 lines over)** — first render this run doesn't reach one
  page (§6/§6a). Profile **pm** (`profile.suggested` agrees, pm 44 highest of
  30/35/41/44) — JD is CRO project management: client comms on trial progress,
  study quotations/contracts, GCP, ERB documentation, scheduling/tracking
  systems, cross-divisional coordination. First render overflowed badly
  (~18 lines over, 15 bullets/6 roles) — one big edit dropped `server`
  (additional role) + the lowest-priority bullet from winnergy/lgchem/otsuka
  → 5 lines over; cut `tf_partnerships` + `hl_gpa` → 3 lines over; cut
  `win_ceo` → still 3 lines over (unchanged); cut `lg_stakeholders` (5th and
  final render under the cap) → still 3 lines over, unchanged. **Notable: the
  last three single-bullet cuts (each ~2-3 lines of source text) left
  `lines_over`/`overflow_pt` completely unchanged (3 / 27.0pt) across 3
  consecutive renders** — worth a follow-up look at whether `fit` estimation
  has a rounding floor or the LaTeX compiler isn't reclaiming space near a
  page-break boundary; not investigated further this run (out of scope, cap
  reached). Final content: 5 roles / 8 bullets — thaifest(1: tf_infrastructure),
  winnergy(2: win_b2c, win_portfolio), lgchem(1: lg_xfn_kpi), otsuka(3:
  ot_launch, ot_regulatory, ot_access), boots(1: boots_frontline); highlight
  hl_experience only; no projects section. `resume.pdf` is a viewable 2-page
  draft reflecting this final `instance.yaml` (§6a honored — last action was
  a render). `omitted.md` written. Reported to user as "cannot fit one page
  without further human trimming" per §6. Draft only, not submitted.
  `master.yaml` untouched.
- **2026-08-12** — **Cover letter: Precision AQ, Project / Portfolio Manager
  (HEOR / JCA).** Wrote `output/precisionaq-pm-2026-08-12/cover_letter.yaml` from
  the tailored `instance.yaml` fact bank → `cover_letter.pdf` **1 page, exit 0 on
  first render** (no tighten loop needed). Addressee "Hiring Team" (JD names no
  manager); location omitted (role is Vancouver/London, candidate Toronto).
  Culture mirrored: "from promises to proof, evidence to access" + start-up pace
  inside an established global org, client-facing partnership with Directors/VPs.
  4 paras (hook / proof: ot_launch + win_portfolio 20+ SKUs / fit: CEO-level
  stakeholders + monthly-and-quarterly reviews / close) — all claims traceable,
  metrics verbatim. Draft for human review, not submitted.

- **2026-08-12** — **Tailored run: Precision AQ (Precision Medicine Group),
  Project / Portfolio Manager, Evidence Synthesis & Decision Modelling / HEOR
  (JCA submissions).** Output `output/precisionaq-pm-2026-08-12/` → **1 page**
  (exit 0, lines_free 0 / slack 9.5pt — tight). Profile **pm**
  (`profile.suggested` agrees, pm 72 highest of 54/72/59/62) — JD is
  client-facing HEOR project/portfolio management: scope/schedule/budget,
  multi-stakeholder coordination, risk escalation, regulatory/JCA context, PM
  tools & templates. Coverage 20% (5/25); most `content_gap` terms are
  HEOR/JCA-specific vocabulary (evidence synthesis, decision modelling, HTA)
  the bank has nothing on — correctly left uncovered per §6, not invented.
  First render overflowed 2 pages (~17 lines over); one big §6 edit dropped
  `server` (additional role, first cut) + `tf_partnerships`, `win_team`,
  `lg_intelligence`, `ot_access` → still 3 lines over; two more single-bullet
  cuts (`win_ceo`, then `ot_regulatory`) closed it to 1 page on the 4th render
  (within the 5-attempt cap). No swap-back attempted — `lines_free` was 0 at
  exit 0, no room. Final: 5 roles / 7 bullets — thaifest(1: tf_infrastructure),
  winnergy(2: win_portfolio, win_b2c), lgchem(2: lg_xfn_kpi, lg_stakeholders),
  otsuka(1: ot_launch), boots(1: boots_frontline); highlights hl_experience/
  hl_gpa/hl_skus; projects section omitted (no room). Full omissions in
  `output/precisionaq-pm-2026-08-12/omitted.md`.

- **2026-08-12** — **Tailored run: Eli Lilly Canada, Patient Support Programs
  (PSP) role (Toronto, flexible/hybrid).** Output
  `output/lilly-psp-manager-2026-08-12/` → **1 page** (exit 0, lines_free 0 /
  slack 9.5pt — tight). Profile **pm** (`profile.suggested` agrees, pm 83 highest
  of 71/83/73/77) — JD is PSP strategy + operational delivery: cross-functional
  coordination (brand/medical/IT/legal/market access/finance), vendor & contract
  management, budget/financial tracking, KPI + Quarterly Business Reviews,
  timelines/dependencies, plus heavy patient-safety/quality/compliance and pharma
  domain. First render overflowed 2 pages (~12 lines over); one §6 edit dropped
  `server` (additional role, first cut) + `win_ceo`, `lg_intelligence`,
  `ot_regulatory` → 1 page. Final: 5 roles / 7 bullets — thaifest(1:
  tf_partnerships), winnergy(2: win_b2c, win_portfolio), lgchem(2: lg_xfn_kpi,
  lg_stakeholders), otsuka(1: ot_launch), boots(1: boots_frontline); highlights
  hl_experience + hl_gpa + hl_skus; no projects (dropped for space). `yorkta`
  never selected (FinTech, no relevance). Coverage 28% (7/25); `selection_gap` =
  "cross functional / market access / functional brand" — no room (0 lines free)
  and weak candidates (cross-functional already conveyed; swapping flagship
  `ot_launch` for `ot_access` just to surface "market access" would trade
  stronger evidence for a keyword), so no swap. `content_gap` is Lilly/PSP
  boilerplate (patient support programs, PSP vendor/strategy, company name,
  benefit program) the bank has nothing on. Docker Desktop wasn't running at
  start — launched from WSL, engine up ~20s, image already built. Resume-only (no
  cover letter requested). `omitted.md` written. Draft only, not submitted.
  `master.yaml` untouched.
- **2026-08-04** — **Tailored run: Loblaw Companies Limited, Product Owner,
  Healthcare Data Products (Brampton, ON).** Output
  `output/loblaw-product-owner-2026-08-04/` → **1 page** (exit 0, lines_free 0 /
  slack 9.5pt — tight). Profile **pm** (`profile.suggested` general 57 / pm 56 —
  flat, no real disagreement; JD is Product Owner + Business Analyst, Agile/Scrum
  backlog prioritization, cross-functional delivery, regulatory + healthcare, so
  pm is the right substantive angle — leaned the summary on "business analyst" +
  "translating business problems into requirements and prioritized delivery" to
  mirror the PO/BA language). First render overflowed 2 pages (~12 lines over);
  one §6 edit dropped `server` (additional role, first cut) + `win_ceo`,
  `ot_regulatory`, `lg_xfn_kpi` → 1 page. Final: 5 roles / 7 bullets —
  thaifest(1: tf_infrastructure), winnergy(2: win_b2c, win_portfolio), lgchem(1:
  lg_stakeholders), otsuka(2: ot_launch, ot_access), boots(1: boots_frontline);
  highlights hl_experience + hl_gpa. Coverage 32% (8/25); `selection_gap` = "data
  products / healthcare data / digital products / data" — generic and no room to
  add (0 lines free, 9.5pt slack), so no swap. `content_gap` is Loblaw/PO
  boilerplate (product owner, product backlog, company name, "top employers") the
  bank has nothing on. Docker Desktop wasn't running at start — launched it from
  WSL, waited for the engine, image already built. Cover letter (`cover_letter.yaml`)
  rendered 1 page on the first attempt — mirrors Loblaw's warm, community/
  healthcare-mission, CORE-values ("Live Life Well", care/ownership, customer-
  first) register; leans on `ot_launch` (end-to-end product dev, scope/schedule/
  budget, on-time, full regulatory compliance, Agile) + `win_portfolio` (20+ SKUs
  prioritization) as proof, and `lg_stakeholders` + `boots_frontline` (pharmacy-
  floor context) for fit. `omitted.md` written. Both PDFs draft-only, not
  submitted. `master.yaml` untouched.
- **2026-07-28** — **Non-interactive tailoring run: Abbott Diabetes Care —
  Product Manager (Consumer Digital Ecosystem, Mississauga).** New draft at
  `output/abbott-product-manager-2026-07-28/` — 1 page, exit 0, `validate` clean,
  `master.yaml` untouched. Profile **dm** (JD = consumer digital ecosystem,
  social/influencer, campaigns, content, CRO in a medical-device/regulated
  context; scorer nudged `bd` on generic-keyword bias but substance is dm). 3
  renders: first overflowed 2pp (~10 lines over) → cut `server` role +
  trimmed thaifest/lgchem/otsuka to 1 bullet each (one edit) → 1pp w/ 3 lines
  free → added `win_ai` back (genuinely-relevant AI-content bullet) → 1pp, 1
  line free. Final cut: thaifest(tf_outreach), winnergy(win_engagement/b2c/
  retention/ai), lgchem(lg_intelligence), otsuka(ot_clinical), boots(frontline);
  highlights engagement/followers/retention. Remaining selection_gap (conversion
  rate, digital/content performance) is CRO-specific — bank has nothing (all in
  content_gap), no worthwhile swap. `omitted.md` written. Distinct from the
  earlier same-day Abbott *Associate PM* run below.
- **2026-07-28** — **Abbott run re-fitted: JD coverage 32% → 56% (8/25 → 14/25),
  still 1 page, `validate` clean, `master.yaml` untouched (md5 matches the
  backup).** No LLM re-run — hand-edited `instance.yaml` + `resume-gen render`.
  Four changes, all verbatim-legal: (1) three already-selected bullets switched
  to a *different profile's* variant of the same bullet — `lg_xfn_kpi` dm→pm
  ("market share" spaced, not "market-share"), `win_engagement` dm→pm ("social
  programs"), `boots_frontline` general→bd ("promotional cycles, sales
  conversion"); (2) `win_retention` restored (its "communication plans …
  product launches" is the bank's only backing for the JD's plan/launch-plan
  language); (3) `omitted.md` rewritten to match. **All four languages kept** —
  an initial trim of German/French was reverted on user correction: the template
  joins languages with `\quad` onto ONE line, so dropping entries frees zero
  space (`slack_pt` 9.5 either way). Don't propose it again as a fit lever. **Key technique worth reusing:
  `validate.py:194` accepts ANY variant of a bullet id, not just the chosen
  profile's — so re-picking a variant is a free, truthful coverage lever the
  tailoring prompt currently under-uses** (prompt §"If a bullet has no variants
  entry for your chosen profile…" only covers the *missing*-variant case).
  Left uncovered on purpose: "product lines" (only backing is `win_b2c`'s bd
  variant, which would cost the 20+ SKU channel-breadth content — not worth one
  keyword). Page now has `lines_free: 0` (9.5pt slack). Cover letter left as-is
  — still truthful, no contradiction.

- **2026-07-28** — **Investigated the Abbott run's 32% JD coverage (8/25).
  Found a real scorer defect: `coverage.py` tokenizes hyphenated compounds as
  ONE token**, so a resume saying "market-share KPIs" / "medical-device" never
  matches the JD's spaced bigrams "market share" / "medical devices". Same for
  closed vs. open compounds ("healthcare" vs. "health care"). Four of the 25
  terms are false misses on that alone (market share, share growth, medical
  devices, health care) — and "medical devices" is *mis-filed as a content gap*
  ("not in your master.yaml") while appearing twice on the page. Fixing the
  tokenizer alone → 12/25 = 48%, no content change. Second finding: the
  `selection_gap` terms (plans, programs, product lines, business/product plan)
  exist in master only inside **pm-profile variants** of already-selected
  bullets, so `master_text()` pooling all profiles makes them look swappable
  when they aren't — matches the ⚠ that the deterministic pick was `pm` but the
  instance chose `dm`. Page is effectively full (`lines_free: 1`, 19.7pt slack),
  so any fix is a swap, not an addition. **No code changed yet** — see What's
  next item 2b for the proposed tokenizer fix.

- **2026-07-28** — **Generated tailored application: Abbott, Associate Product
  Manager (Coronary), Vascular** → `output/abbott-associate-product-manager-2026-07-28/`.
  dm profile; 1-page resume (9 bullets / 5 roles) + 1-page cover letter, both
  exit 0. Overflow loop cut server role + win_portfolio + tf_partnerships to fit;
  added ot_access back for the market-access/reimbursement theme. Output only — no
  code changes.

- **2026-07-28 (latest)** — **Web UI redesigned (":5000" front end).** Picked
  the "Blush Rosé, refined" direction from a three-option design deck (the
  other two — a dark operator console, and a paper/letterpress "atelier" where
  the résumé preview is the hero — were rejected as too big a break from the
  tracker sibling / too much new backend for now). Kept the palette; replaced
  the gradient band that ate the top third with a one-line header, made the
  paste box the top of the page, turned the streamed log into five named steps
  (mapping table in the template's JS, driven by `make_narrator()`'s phrases)
  with the raw log collapsed into the rail, and replaced the identical download
  pills with a file list carrying page count + size. New right rail shows the
  run's real numbers — JD coverage (+ the "you have this, it just didn't make
  the page" terms), page fit, cost — all *read* from files the pipeline already
  writes (`coverage.md`, `resume.aux`, `cost.json`); nothing is recomputed.
  Added a Drafts tab over a new read-only `GET /drafts`, a Best-quality/Fast
  tier switch (`?tier=`), and ⌘/Ctrl-Enter to run. Note the tier switch fixes a
  real bug: the web app hardcoded `--model claude-sonnet-5 --effort medium` into
  `RESUME_GEN_CLAUDE_FLAGS`, so every browser run silently used the *fast* tier
  regardless of the launcher's Opus/high default. Verified with a stub
  `resume-gen` (no LLM spend): narration → steps, `__RESULT__` payload, meta
  readers, `/drafts`, tier flags (default→opus/high, `?tier=fast`→sonnet/medium,
  env override still wins). `pytest` 58 passed. Web image is bind-mounted, so no
  Docker rebuild. **Not yet seen in a real paid run — check it on the next one.**
- **2026-07-28** — **Tailored application run: Abbott Trade Marketing
  Manager (Nutrition), Mississauga.** `output/abbott-trade-marketing-manager-2026-07-28/`
  — profile `dm`, resume hit 1 page on the second render (started 3 lines over,
  trimmed `lg_positioning` and `ot_agile`, dropped `server` from the initial
  draft since the page was already over without it). Cover letter rendered
  clean on the first attempt. Both are drafts pending human review; nothing
  submitted. No repo/pipeline changes.
- **2026-07-28** — **Model default decided + `--fast` flag shipped.**
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
