# Tailor Resume — Master Prompt

You are tailoring a resume from a fixed content bank (`master.yaml`) to a
specific job description. **You select and lightly rephrase; you never
invent.** Your output is `instance.yaml`, consumed by a deterministic
renderer (`resume-gen`) that never calls an LLM itself.

Read, in full, before writing anything:
- `master.yaml` — the content bank (summaries, experience bullets with
  per-profile `variants`, education, certifications, skills, languages).
- The job description file at the path you were given.

## 1. Hard rules

These mirror `master.yaml`'s `authoring_rules` verbatim. The render pipeline
enforces them mechanically (`validate.py`) — a violation is a hard failure,
not a style note.

**Locked fields — select and reorder only, never rewrite:**
- Metrics/numbers (e.g. "90%", "100%", "20+ SKUs", "10K+")
- Dates and durations
- Job titles
- Company names and locations
- Degree names, GPA, certifications

**Rephrasable — you may adjust wording:**
- Summary prose (the one field with real rewriting latitude)
- Nothing else. Bullet `text` fields are picked verbatim from an existing
  `variants[profile]` string — not edited, not merged, not paraphrased. If no
  variant fits well, pick the closest one as-is; do not blend two variants'
  wording into a new sentence.

**Absolute rules:**
1. Never invent an achievement, metric, tool, or responsibility not present
   in `master.yaml`.
2. Never upgrade a number or a scope word to fit the JD (e.g. "supported" →
   "led").
3. Output is a DRAFT for human review. Never auto-submit anywhere.
4. One page. If content overflows, drop the lowest-priority bullets — never
   shrink fonts, margins, or facts to make room.
5. **No em dashes and no hyphens used as punctuation.** Do not use `—`, `–`,
   or a `-` as a sentence-level pause anywhere you're rewriting text (i.e. in
   the Summary — bullet/locked-field text is copied verbatim from
   `master.yaml` so this doesn't apply there, and a pre-existing dash in
   `master.yaml` source itself is out of scope). Use a comma, period, or
   restructure the sentence instead. A hyphen in a genuine compound word
   (e.g. "cross-functional") or a date range (e.g. "2023-2025") is fine; a
   hyphen or dash used as a sentence-level pause is not.

## 2. Profile guidance

`master.yaml` has three angles — `bd` (business development / partnerships),
`pm` (project management / PMP), `dm` (digital commerce / brand marketing) —
plus `general` as a neutral default. Read the job description and form a
judgment of which angle(s) it rewards:

- Heavy on partnerships, channel/market expansion, negotiation, account
  growth → **bd**.
- Heavy on program/project delivery, scope-schedule-budget, cross-functional
  coordination, PMP/Agile/Waterfall language → **pm**.
- Heavy on e-commerce, digital campaigns, brand/content, social/retail
  channels → **dm**.
- Ambiguous, generalist, or none of the above dominate → **general**, or
  blend.

**Anchor to your dominant profile, with narrow, justified exceptions.** Use
that profile's variant for every bullet by default — record it in
`instance.yaml`'s top-level `profile` field. (The summary is a separate,
looser case — see §4, which already has its own blending rule; nothing below
tightens that.) This is deliberate, not laziness: variants carry different
**metrics**, not just different wording (e.g. one bullet's `pm` variant states "4 engagement
stages" while its `bd` variant states "12 new relationships" for the same
underlying work) — swapping variants just to echo more of the JD's own
keywords changes which achievement the reader actually sees, and can break
§4a's "highlights should reinforce a selected bullet" rule. Chasing the
deterministic coverage score this way was tried and measured: it moved the
score up while making the resume read worse (see `SESSION_HANDOFF.md`'s
2026-07-28 A/B if you want the specifics) — do not repeat that mistake.

Deviate from the anchor profile for a specific bullet **only** when a
sibling profile's variant states a fact or metric the job description
explicitly asks for, **and your anchor variant doesn't contain it.** That is
the whole test. "This variant reads slightly better," "this uses the JD's
exact word," and "this would raise the coverage score" are each, on their
own, **not** sufficient reasons. When you do deviate:

- Prefer `general`'s variant over a rival profile's, if `general` also
  carries the needed fact — its neutral register blends into an anchored
  resume without a voice seam, where a rival profile's distinct voice is
  more noticeable next to your anchor-profile bullets.
- Cap it at roughly **1/3** of your selected bullets. Reaching for more than
  that is a signal the JD probably calls for a different dominant profile —
  reconsider that choice first, rather than patching it bullet by bullet.
- Never let two **adjacent** bullets within the same role both come from a
  non-anchor profile — that's where a voice shift is most jarring to a
  reader. (An anchor-profile bullet next to a single deviation is fine; two
  deviations back to back are not, even from the same sibling profile.)
- Record it in `omitted.md` (§7) — the anchor profile's own variant for that
  bullet, marked `cross-profile-swap`, with the specific JD fact that
  justified using the other variant instead. A reviewer should be able to
  see exactly what you set aside and why.

The rule above governs a *choice* between variants that both exist. It's a
different case entirely when your anchor profile has no `variants` entry for
a bullet at all — that's a mandatory fallback, not a judgment call, and does
not count against the 1/3 cap: fall back to `general` if present, otherwise
pick whichever variant is closest and use it unedited.

## 3. Bullet-selection guidance

For each experience entry in `master.yaml`:

1. Read every bullet's `themes` tags. Match them against keywords and
   priorities in the job description — direct keyword overlap, but also
   conceptual overlap (e.g. a JD emphasizing "stakeholder alignment" matches
   `themes: [executive-comms, stakeholder-management]`).
2. Rank bullets within that role by relevance to the JD.
3. Include enough bullets per role to represent the role credibly — as a
   guideline, 3-5 for the two most senior/relevant roles (Winnergy, LG Chem),
   2-3 for shorter or less relevant roles (Otsuka, Boots) — but let JD
   relevance override the guideline; do not pad with irrelevant bullets just
   to hit a count, and do not cut a highly relevant bullet just to stay under
   it.
4. Order bullets within a role from most to least relevant/impressive — the
   first bullet under a role carries the most weight with a skimming reader.
5. Every bullet you select for a role must still get an entry in that role's
   `priority_order` (see §5) — including ones you're confident about keeping;
   `priority_order` covers all selected bullets, not just marginal ones.

Do not select a bullet id that has no `variants` entry at all under any
profile you're using — check the bank before writing the id into
`instance.yaml`.

**Aim to fit one page on the first render.** The overflow loop in §6 is a
safety net, not the plan — every extra attempt costs a full render cycle. Since
the final resume is trimmed to one page regardless, a lean first pass reaches
the same one-page result in fewer iterations. So start at the **lower** end of
the per-role bullet counts above and treat the upper end as headroom you add
back only if space clearly remains — prefer selecting conservatively over
selecting maximally and relying on the loop to cut back.

### 3a. Role inclusion & timeline continuity

Bullet ranking decides *which bullets* within a role; this decides *whether a
role appears at all*. Most roles are included on relevance. **`boots` is the
exception — it is timeline-load-bearing, not filler.** Her full-time roles leave
two gaps a reader will notice: LG Chem ends Oct 2021 and Winnergy doesn't start
until Aug 2022 (~10 months, a post-layoff job search), and Winnergy ends Oct 2023
before the master's begins. `boots` (Sep 2021 – Aug 2024, concurrent) spans both.

Therefore: **whenever both `lgchem` and `winnergy` appear on the resume, include
`boots` as well**, even if its JD relevance is low — omitting it exposes an
unexplained gap. Keep `boots` in the main **Experience** section (it is relevant
pharma domain experience); never mark it `additional`. One bullet is enough when
relevance is thin — the point is that its dates sit in the timeline. On overflow
(§6), prefer trimming `boots` down to a single bullet before removing the role
entirely, so the dates stay visible.

### 3b. Canadian experience — the thaifest role (always included)

`master.yaml` has a `thaifest` role (Public Relations Intern, Thai Festival
Toronto Foundation, Toronto — May 2026 – Present). **Include it on every resume,
regardless of the JD's topical fit.** It is her current, Canadian-based role, and
a Canadian recruiter reads local experience as a signal in its own right — that
signal is the point, so it is never dropped for low keyword overlap the way an
ordinary role would be. Keep it in the main **Experience** section (never
`additional`).

Scale *how much* of it appears to the JD, but never below one bullet:

- **JD is relevant** (marketing, communications, PR, partnerships, BD, events,
  stakeholder/vendor coordination, program/process setup): select 2–4 bullets
  and pick the profile variant that matches, as you would for any strong role.
- **JD is unrelated** (e.g. a pharma reimbursement or lab role): keep just the
  **single strongest / most transferable** bullet — `tf_infrastructure`
  (systems/process/CRM) or `tf_partnerships` (stakeholder coordination) usually
  travel furthest — so the role and its current Canadian dates still appear
  without spending page space on off-topic detail.

This is the same treatment as `boots` in §3a (timeline-load-bearing, trimmed not
dropped), applied here for Canadian-experience continuity. On overflow (§6),
trim `thaifest` toward one bullet before ever removing it.

## 4. Summary guidance

Start from the closest-matching `summaries` entry for your chosen dominant
profile. You may rephrase connective prose and re-emphasize which
achievements lead, but every locked fact inside it (percentages, "seven
years", GPA, institution name, "PMP certified", etc.) must survive verbatim.
If blending two profiles' summaries reads better for this JD, you may draw
sentences from both — but do not introduce a claim that appears in neither.

Before finalizing the summary, scan the JD's most-repeated terms against it.
If a term is a near-miss — present in a *sibling* profile's summary variant or
elsewhere in `master.yaml`, just not in the wording you drafted — prefer
working it in over inventing new phrasing, since it costs nothing extra and
closes a keyword gap for free. E.g. `sum_bd` may drop a word like "industry"
that `sum_dm` keeps for the same underlying fact; pull it across rather than
losing it to a rewrite. This is a wording nudge, not a rule to force every
JD term in — do not distort a sentence's meaning or pad it just to land a
keyword.

## 4a. Highlights — the colored impact line

`master.yaml` has a `highlights` bank of headline KPIs. Select **up to 3** that
best match what the JD rewards, ordered most-relevant first, and copy each into
`instance.yaml`'s `highlights` list as `{id, value, label}` — `value` and
`label` are **locked** (verbatim from the bank, never rewritten); do not copy
the bank's `profiles` field. Prefer highlights whose numbers also appear in a
bullet you selected, so the line reinforces the body rather than floating alone.
Omit the `highlights` key entirely if none are a good fit — the impact line then
simply doesn't render.

## 4b. Additional Experience — the server role

`master.yaml` has a `server` role carrying `additional: true`. Include it by
default: it fills the Canadian timeline and renders under its own "Additional
Experience" heading, after the main roles. It is the **lowest-priority** content
on the resume — see the overflow rule in §6, where it is the first thing cut.
Copy `additional: true` verbatim (it's a locked passthrough field) so the
renderer routes it to the right heading.

## 5. Output schema — `instance.yaml`

Write exactly this shape (see `TECH_SPEC.md` §3 for the full structural
spec the script validates against):

```yaml
schema_version: 1.0              # must equal master.yaml's schema_version
profile: bd                      # dominant angle label: bd | pm | dm | general
job_description_ref: job_description.txt
meta: { ...copied verbatim from master.yaml.meta... }
summary: "..."                    # rephrased prose, profile-appropriate
experience:
  - id: winnergy                  # must match an id in master.yaml
    company: ...                  # copied verbatim (locked)
    location: ...
    title: ...
    start: ...
    end: ...
    # copy verbatim if present on this id in master.yaml:
    # multinational, multinational_note, part_time, concurrent, additional
    bullets:                      # ordered, most to least relevant, subset only
      - id: win_b2c
        text: "Opened the company's first B2C channel from scratch, ..."
      - id: win_retention
        text: "Sustained a 90% repeat-order rate ..."
highlights:                       # optional; up to 3, most-relevant first
  - { id: hl_engagement, value: "100%", label: "online-engagement growth" }
  - { id: hl_retention,  value: "90%",  label: "customer retention" }
  - { id: hl_skus,       value: "20+ SKUs", label: "across 4 pipelines" }
projects:                         # optional; omit entirely if the page is tight
  - id: proj_jobsearch_tools      # must match an id in master.yaml.projects
    name: ...                     # copied verbatim (locked)
    link: ...                     # copied verbatim if present
    stack: ...                    # copied verbatim if present
    bullets:                      # ordered, most to least relevant, subset only
      - id: pj_generator
        text: "Scoped and delivered an AI résumé generator end-to-end, ..."
education: [ ...copied verbatim, reordering allowed... ]
certifications: [ ...copied verbatim... ]
skills:
  - label: "Business Development & Partnerships"
    items: [ ... ]                # subset/reorder of that group's items only
languages: [ ...copied verbatim... ]
priority_order:                   # per-role bullet ids, ascending priority —
  winnergy: [win_ai, win_b2b, win_engagement, ...]   # lowest-priority FIRST,
  lgchem: [...]                                       # i.e. first to cut
  otsuka: [...]
  boots: [...]
```

Notes:
- `priority_order` is required for every role that appears in `experience`,
  and must contain exactly the bullet ids you selected for that role — same
  set, no more, no less. Order = cut order (§6), not display order.
- `meta`, `education` (non-id fields), `certifications`, and `languages` are
  locked — copy them from `master.yaml` verbatim; you may reorder education
  entries but not alter their content.
- `projects` is optional and self-built work, not employment — never merge it
  into `experience`. Include it when the role values building, automating or
  systems thinking, and pick each bullet's `variants` entry by profile exactly
  as you do for experience bullets. `name`, `link` and `stack` are locked. It
  is the lowest-priority section on the page: if the draft runs to two pages,
  cut project bullets before cutting any real role, and drop the section whole
  before losing an employment bullet.
- `skills` groups/items must be a subset of what's already in `master.yaml`
  under a matching `label` — pick the groups relevant to the chosen
  profile(s) and trim `items` to what's most relevant to the JD, but don't
  add anything not already listed there.

## 6. Overflow loop

After writing `instance.yaml`, run:

```
resume-gen render --instance <path> --master master.yaml --out <output-dir>
```

Read the exit code and the JSON on stdout:

- **Exit 0**: done. One page, valid. Before you stop, glance at the
  `coverage` block in the JSON (a deterministic ATS-style keyword screen, also
  written to `coverage.md`). `content_gap` terms are ones the bank has nothing
  on: never invent a bullet to cover them. A large `profile.suggested`-vs-your-
  `profile` disagreement is worth a second look at your profile choice.
  Coverage is a nudge, not a gate — never sacrifice truthfulness or the
  one-page rule for it.

  If `selection_gap` lists JD terms you *do* have content for in `master.yaml`
  but didn't select, try to close them with one of two moves, in this order:

  1. **Add**, if `fit.lines_free` > 0: swap a relevant omitted bullet back in
     (still verbatim) using the free space, and re-render.
  2. **Replace**, if `fit.lines_free` is 0 (the common case on a full page):
     find an omitted bullet *in the same role* as a currently-selected bullet
     that is weaker evidence for this JD, and swap the two. Same-role keeps
     the "never empty a core role" rule (point 2 below) out of danger, and a
     same-role substitution is usually similar enough in length that it
     rarely reopens overflow. Re-render to confirm it still fits; if the
     replacement is longer and now overflows, pick a shorter alternative or
     revert the swap.

  **Before either move, verify the JD term's literal words actually appear in
  the candidate bullet's chosen-profile `text`** — not just in its `themes`
  tag or in a different profile's variant. `themes` and other-profile wording
  never render, so a bullet can look like it "covers" a term when the
  rendered resume would not actually gain that word. After re-rendering,
  check that the term moved into the new `covered` list, not just that the
  score number changed — if it didn't, the swap did nothing and should be
  reverted.

  Swap only when the bullet you are adding is *genuinely* the better evidence
  for this role. Never trade a stronger bullet for a weaker one to make a term
  appear: the screen matches words, it cannot see relevance, and a resume that
  reads worse but scores higher is a worse resume. Some `selection_gap` entries
  are single generic words ("process", "plans") — those are the least worth
  chasing. Cap coverage-driven swap experiments at 2 extra re-renders beyond
  whatever the overflow loop already used (still inside the overall 5-attempt
  cap below); if no omitted bullet is a real improvement within that budget,
  change nothing and stop — leaving a term uncovered is a perfectly good
  outcome.
- **Exit 1**: validation failure — `errors[]` names the id/field mismatch.
  Fix `instance.yaml` (you likely copied a locked field wrong or altered
  bullet text) and re-run. This does not count against the overflow retry
  cap.
- **Exit 2**: render/compile error — likely a malformed `instance.yaml`
  shape. Fix and re-run; does not count against the overflow retry cap.
- **Exit 3**: page overflow. `page_count` in the JSON tells you it's >1.
  Cut in this order:
  1. **First, drop the Additional Experience role entirely** (the entry with
     `additional: true`, i.e. `server`) if it's still present: remove the whole
     entry from `experience` *and* its key from `priority_order` — the entire
     role, header and all, not just one of its bullets. The "Additional
     Experience" heading disappears on its own once the role is gone.
  2. Only after that role is gone, drop the next-lowest-priority bullet id — the
     first entry in whichever role's `priority_order` array still has entries —
     from that role's `bullets` list (and remove it from `priority_order` too).
     Use judgment on *which* role to trim from if multiple roles have
     low-priority bullets left: prefer trimming the role least central to the
     chosen profile. **Never remove the last remaining bullet of any role in
     `experience`** — including `winnergy`, `lgchem`, and `otsuka`, not just
     `boots` (§3a) and `thaifest` (§3b). Dropping a core role's last bullet
     removes the role's header and dates too, silently opening an unexplained
     employment gap — worse than a denser page. Trim every role down to one
     bullet before touching a role's last one, and keep the role and its dates
     visible no matter how tight the page gets.
  3. If still overflowing and the impact line is present, dropping a `highlights`
     entry (or the whole `highlights` key) is a low-cost trim before cutting more
     substantive bullets.
  Re-run after each cut.

Cap at **5 render attempts total**. If still >1 page after 5 attempts, stop
and report to the user: "Cannot fit one page without further human
trimming" — do not shrink fonts/margins/facts to force it, and do not keep
looping past the cap.

### 6a. Always leave a viewable PDF (even on failure)

A tailoring run must **never** end without a rendered PDF the human can open
and vet — one page or not. The renderer already writes `resume.pdf` (and
`resume.docx`) on exit 3 (overflow), so a normal cap-stop always leaves a
viewable draft. Two rules keep that guarantee honest:

- **End on a render, not an edit.** When you stop — whether at exit 0 or the
  5-attempt cap — your *last* action on `instance.yaml` must have been rendered.
  Never make a cut you don't then render: the on-disk `resume.pdf` must always
  correspond to the current `instance.yaml`. If you edited and hit the cap,
  render that edit once more (it's the state you're reporting) before stopping.
- **If you can't reach a rendered state at all** (e.g. you cannot resolve an
  exit 1 validation error or exit 2 compile error), say so explicitly and
  report that **no PDF was produced and why** — that is the one case where a
  viewable draft does not exist, and the human needs to know.

When you stop at the cap, frame the result around the draft, not the failure:
**lead with the PDF path and its page count** ("Draft ready for review:
`output/<slug>/resume.pdf` — 2 pages, needs further trimming to fit one"),
then explain what you cut and what still overflows. The human's next step is
to open that PDF, so its path is the headline, not a footnote.

## 7. Omissions report — write `omitted.md`

Alongside `instance.yaml`, write `output/<company>-<role>-<date>/omitted.md`: a
human-readable audit of **everything from `master.yaml` that did NOT make the
final resume**, so a reviewer can see what was left on the table and put
anything back. Write it once, reflecting the *final* rendered state (after any
§6 overflow cuts) — not intermediate attempts.

It must be a Markdown file with a single table. **For bullets, put the full
verbatim text — never just the id.** Use the text of the variant you would have
used (your chosen profile, else `general`, else the closest, per §2). Columns:

| Type | Role / Group | ID | Full text (verbatim) | Category | Reason |
|------|--------------|----|----------------------|----------|--------|

- **Type**: `bullet`, `highlight`, `role`, or `skill`.
- **Full text (verbatim)**: for a bullet, the whole variant sentence; for a
  highlight, its `value` + `label` (e.g. `100% — online-engagement growth`);
  for a role, its title + company + dates; for a skill, the item text.
- **Category**: `never-selected` (didn't make the relevance cut in §3),
  `overflow-cut` (was selected, then dropped by the §6 loop to reach one
  page), or `cross-profile-swap` (§2 — your anchor profile had its own
  variant for this bullet, but you used a sibling profile's variant instead;
  this row is the anchor variant you passed over, full text and all). Keep
  all three distinct — the reviewer treats them differently.
- **Reason**: one concrete phrase (e.g. "low JD relevance — no ops keywords",
  "cut first per §6 additional-role rule", "duplicate metric already shown by
  `hl_experience`"; for `cross-profile-swap`, the specific JD-required fact
  the other variant had that this one didn't).

Cover every omitted item in these classes: experience bullets not in the final
`instance.yaml`, the `server` role if dropped, highlights not selected, any
skills items you trimmed out of an included group, and every bullet where you
used a non-anchor-profile variant per §2's exception test. If nothing was
omitted in a class, you may skip its rows, but the file must always exist.

## 8. Before you finish

- Copy the job description to `output/<company>-<role>-<date>/job_description.txt`
  as part of writing the output (audit trail).
- Confirm every locked field in `instance.yaml` string-matches `master.yaml`
  for its id — this is what `validate.py` checks, so pre-checking it
  yourself avoids a wasted render cycle.
- Any em dash, en dash, or punctuation-style hyphen in the Summary? Rewrite
  it out (see §1.5).
- Report the `output/<slug>/resume.pdf` path and its page count as the first
  line of your result, whether you finished at one page or stopped at the cap
  (see §6a) — the human's next action is to open it.
- Remind the user this is a draft: they should read it before sending
  anywhere.
