# Eval judge — which selection serves this posting better?

You are judging two tailored resume drafts (`candidate_1.yaml`,
`candidate_2.yaml`) built from the **same** career fact bank for the **same**
job posting. Every bullet's text is verbatim-locked and identical wherever both
candidates picked it — so you are judging **selection and ordering only**:
which draft chose the more persuasive subset of the same true facts.

You are deliberately not told which model/settings produced which candidate.
Judge only what is on the page.

## Rubric

Score each candidate 1–5 on each dimension:

1. **Relevance** — do the chosen bullets speak to this posting's core duties
   and qualifications, not just its industry?
2. **Evidence strength** — did it prefer concrete, quantified achievements over
   generic claims where both were available?
3. **Story coherence** — do the summary, chosen profile/angle, bullet order,
   and skills read as one deliberate pitch for *this* job?
4. **Use of the page** — does the mix of roles/bullets/highlights use the
   one-page budget on what matters most (nothing important crowded out by
   something weaker)?

## Rules

- Keyword echo is NOT the rubric. A draft that mirrors the posting's wording
  but picks weaker evidence loses to one that picks stronger evidence in its
  own words.
- Never propose rewording, new facts, or edits — the facts are locked upstream
  and truthfulness is enforced elsewhere. Selection judgment only.
- A tie is a legitimate verdict; do not manufacture a preference. If the two
  drafts differ by a bullet or two of no consequence, say so.

## Output — `judge.md`

Write exactly one file, `judge.md`, in the folder named in your task, with:

1. A rubric table: one row per dimension, one column per candidate, scores 1–5.
2. **Verdict:** `candidate_1`, `candidate_2`, or `tie`, in bold on its own line.
3. A short rationale (≤ 150 words) citing the specific differing bullets that
   decided it — quote fragments so a human can find them.

This is advisory input to a human decision, never a gate.
