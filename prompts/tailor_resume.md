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

**Do not commit to one profile for the whole resume.** Decide per bullet and
for the summary independently — that's what `variants` is built for. A
resume can pull `bd` wording for one role's bullets and `pm` wording for
another's, if that's what best mirrors the posting. Still record one label in
`instance.yaml`'s top-level `profile` field — the dominant angle, used for
the tagline and output-folder naming — even when individual bullets draw
from other profiles.

If a bullet has no `variants` entry for your chosen profile, fall back to
`general` if present, otherwise pick whichever variant is closest and use it
unedited.

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

## 4. Summary guidance

Start from the closest-matching `summaries` entry for your chosen dominant
profile. You may rephrase connective prose and re-emphasize which
achievements lead, but every locked fact inside it (percentages, "seven
years", GPA, institution name, "PMP certified", etc.) must survive verbatim.
If blending two profiles' summaries reads better for this JD, you may draw
sentences from both — but do not introduce a claim that appears in neither.

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
  written to `coverage.md`). If `selection_gap` lists JD terms you *do* have
  content for in `master.yaml` but didn't select, and the page has room, swap a
  relevant bullet back in (still verbatim) and re-render — this is the cheap way
  to raise real fit. `content_gap` terms are ones the bank has nothing on: never
  invent a bullet to cover them. A large `profile.suggested`-vs-your-`profile`
  disagreement is worth a second look at your profile choice. Coverage is a
  nudge, not a gate — never sacrifice truthfulness or the one-page rule for it.

  Swap only when the bullet you are adding is *genuinely* the better evidence
  for this role. Never trade a stronger bullet for a weaker one to make a term
  appear: the screen matches words, it cannot see relevance, and a resume that
  reads worse but scores higher is a worse resume. Some `selection_gap` entries
  are single generic words ("process", "plans") — those are the least worth
  chasing. If no omitted bullet is a real improvement, change nothing and stop;
  leaving a term uncovered is a perfectly good outcome.
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
     chosen profile.
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
- **Category**: `never-selected` (didn't make the relevance cut in §3) vs
  `overflow-cut` (was selected, then dropped by the §6 loop to reach one page).
  Keep these distinct — the reviewer treats them differently.
- **Reason**: one concrete phrase (e.g. "low JD relevance — no ops keywords",
  "cut first per §6 additional-role rule", "duplicate metric already shown by
  `hl_experience`").

Cover every omitted item in these classes: experience bullets not in the final
`instance.yaml`, the `server` role if dropped, highlights not selected, and any
skills items you trimmed out of an included group. If nothing was omitted in a
class, you may skip its rows, but the file must always exist.

## 8. Before you finish

- Copy the job description to `output/<company>-<role>-<date>/job_description.txt`
  as part of writing the output (audit trail).
- Confirm every locked field in `instance.yaml` string-matches `master.yaml`
  for its id — this is what `validate.py` checks, so pre-checking it
  yourself avoids a wasted render cycle.
- Report the `output/<slug>/resume.pdf` path and its page count as the first
  line of your result, whether you finished at one page or stopped at the cap
  (see §6a) — the human's next action is to open it.
- Remind the user this is a draft: they should read it before sending
  anywhere.
