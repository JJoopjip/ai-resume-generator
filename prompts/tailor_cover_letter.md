# Tailor Cover Letter — Master Prompt

You are writing a one-page cover letter to accompany a resume that has **already
been tailored** to a specific job description. You draw every fact from that
tailored resume; you mirror the target company's culture in *tone and framing
only*; you never invent. Your output is `cover_letter.yaml`, consumed by the
deterministic `resume-gen cover` renderer (which never calls an LLM itself).

Read, in full, before writing anything:
- `instance.yaml` — the tailored resume in this output folder. **This is your
  fact bank.** Its `meta`, `summary`, selected `experience` bullets, `highlights`,
  `education`, `certifications`, and `skills` are the *only* facts about the
  candidate you may use. The letter must not claim anything the resume doesn't.
- `job_description.txt` in the same folder — the role, the company, and the
  cultural signal you tailor toward.

You are not re-selecting achievements from `master.yaml`. The resume already
made those choices; the letter's job is to *narrate a few of them* persuasively.

## 1. Hard rules

The letter is prose, so it has more wording latitude than the resume — but the
truthfulness guard is identical and non-negotiable.

**Locked — reproduce verbatim, never rewrite:**
- Every metric/number (e.g. "100%", "20+ SKUs", "10K+", "seven years", GPA).
  Copy the digits and units exactly as they appear in `instance.yaml`.
- Job titles, company names, dates, degree names, certifications.

**You may freely write:**
- Connective and persuasive prose — the hook, the framing, the transitions, the
  enthusiasm, the culture-mirroring word choice.

**Absolute rules:**
1. **Every claim must trace to `instance.yaml`.** If a sentence asserts an
   achievement, responsibility, skill, or metric, you must be able to point to
   the exact bullet / summary / highlight / skill in the resume it came from.
   No new achievements, tools, numbers, or scope.
2. **Never upgrade scope or numbers** to fit the JD ("supported" → "led",
   "contributed to" → "drove", "20+" → "30+"). Match the resume's verbs and
   magnitudes.
3. **Culture-matching is framing only.** You mirror the company's tone and
   vocabulary; you never invent alignment, shared values, or facts about the
   candidate to manufacture fit. If the JD's culture rewards something she
   hasn't done, don't claim she has — lean on what she *has* done that is
   adjacent.
4. Output is a DRAFT for human review. Never auto-submit anywhere.
5. **One page.** ~250–350 words, 3–4 short paragraphs. If it overflows, tighten
   prose — never shrink fonts, margins, or facts (see §6).

## 2. Read the company and its culture

Before writing, extract from the job description:

- **Company name** — for the recipient block and for the "why this company"
  paragraph. Use the JD's exact name.
- **Role title** — name it explicitly in the opening. Use the JD's exact title.
- **Cultural signal** — the tone and values the posting broadcasts. Look at:
  register (formal/institutional vs. casual/scrappy), stated values (e.g.
  "resident-focused", "move fast", "collaborative", "mission-driven"),
  repeated vocabulary, and what the org seems to care about beyond the task list.

Then **mirror that signal** in the letter's voice: a public-sector role that
stresses service and accountability wants measured, service-oriented language;
an early-stage product team that stresses ownership and speed wants crisp,
energetic language. The register shifts; the facts do not. Aim for
**professional but genuinely enthusiastic** in every case — warmth carried by
*specificity about this company and role*, not by adjectives or hype.

## 3. Addressee

- If the JD names a hiring manager or recruiter, address them by name
  (`recipient.addressee: "Dr. Jane Lee"`, `salutation: "Dear Dr. Lee,"`).
- Otherwise use `recipient.addressee: "Hiring Team"` and
  `salutation: "Dear Hiring Team,"`. Do not use "To Whom It May Concern."
- `recipient.company` is the target employer from the JD; `recipient.location`
  is optional (include if the JD states a clear work location).

## 4. The letter — four paragraphs

Write 3–4 short paragraphs into the `paragraphs` list, in this order. Keep each
to 3–5 sentences; skimmable beats complete.

1. **Hook.** Name the exact role and company, give one *specific, genuine*
   reason this role/company excites her (drawn from the JD's mission or focus),
   and land one headline credential or achievement from the resume that signals
   fit. Never open with "I am writing to apply for…".
2. **Proof.** Pick the 1–2 achievements from `instance.yaml` most relevant to the
   JD's top requirements and narrate them in prose — with the metric reproduced
   verbatim. Show the through-line from what she did to what this role needs.
   Prefer achievements that also appear in the resume's `highlights` so the two
   documents reinforce each other.
3. **Fit / culture.** Why *this* company specifically — connect her background
   to the company's mission, product, or values as expressed in the JD. This is
   where the culture-mirroring is most visible. Make it concrete and particular;
   a sentence that could be pasted into any other company's letter has failed.
4. **Close.** Reinforce fit in one line, make a clear, warm call to action (a
   conversation / interview), and thank them. Two sentences.

Voice checks before you commit each paragraph:
- Could this exact sentence appear in a letter to a different company? If yes,
  make it specific or cut it.
- Does every factual claim map to a line in `instance.yaml`? If not, remove it.
- Is a metric quoted? Does it match the resume digit-for-digit?

## 5. Output schema — `cover_letter.yaml`

Write exactly this shape into the resume's output folder, beside `instance.yaml`:

```yaml
schema_version: 1.0                 # must equal instance.yaml's schema_version
instance_ref: instance.yaml         # the fact bank + letterhead source
job_description_ref: job_description.txt
date: "July 7, 2026"                # today's date, "Month D, YYYY"
recipient:
  addressee: "Hiring Team"          # a named manager if the JD gives one
  company: "City of Toronto"        # target employer, from the JD
  location: "Toronto, ON"           # optional
salutation: "Dear Hiring Team,"
paragraphs:                         # 3-4 items, in the §4 order
  - "Hook paragraph …"
  - "Proof paragraph …"
  - "Fit / culture paragraph …"
  - "Close paragraph …"
signoff: "Sincerely,"
```

Notes:
- Do **not** put the candidate's name/contact in the letter body — the renderer
  builds the letterhead from `instance.yaml`'s `meta`, so it can never drift from
  the resume. You only supply date, recipient, salutation, paragraphs, sign-off.
- Write plain text in `paragraphs`; the renderer handles all LaTeX escaping
  (`%`, `&`, `$`, `#`, `_`), so write `100%` and `R&D` normally.
- `signoff` is normally "Sincerely," — match the register if the culture calls
  for something warmer (e.g. "Warm regards,"), but keep it professional.

## 6. Render loop

After writing `cover_letter.yaml`, run:

```
resume-gen cover --letter <path-to-cover_letter.yaml>
```

Read the exit code and the JSON on stdout (same contract as `render`):

- **Exit 0**: done. One page, valid.
- **Exit 1**: letter invalid — `errors[]` names the problem (missing required
  field, or too many paragraphs). Fix `cover_letter.yaml` and re-run.
- **Exit 2**: render/compile error — likely a malformed `cover_letter.yaml`
  shape. Fix and re-run.
- **Exit 3**: page overflow (`page_count` > 1). The letter is too long. Tighten
  the prose — shorten paragraphs, cut the weakest sentence, or drop to three
  paragraphs (merge Proof and Fit) — then re-render. Never shrink
  fonts/margins/facts to force it.

Cap at **4 render attempts**. Always end on a render, so the on-disk
`cover_letter.pdf` matches the final `cover_letter.yaml` (mirror
`tailor_resume.md` §6a — never stop on an unrendered edit).

## 7. Before you finish

- Confirm every metric in the letter string-matches `instance.yaml`.
- Confirm no paragraph makes a claim absent from `instance.yaml`.
- Lead your report with the `cover_letter.pdf` path and its page count — the
  human's next action is to open it.
- Remind the user this is a draft to read and personalize before sending.
