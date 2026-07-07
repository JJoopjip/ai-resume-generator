#!/usr/bin/env python3
"""coverage.py — a deterministic, no-LLM "how well does this resume cover the
job posting?" score.

This is the *relevance* companion to validate.py. validate.py answers "is every
fact real?" (truthfulness — locked fields + verbatim bullets vs. master.yaml).
coverage.py answers a different question: "of the things THIS posting cares
about, how many actually show up on the tailored resume?" — the same idea an
ATS (applicant tracking system) keyword screen uses.

It is deliberately a heuristic, not a verdict:
  * It extracts the job description's most salient terms (frequent, non-boiler-
    plate unigrams and two-word phrases) and checks each against the resume text
    that the instance.yaml actually renders (summary, titles, bullets, skills,
    highlights, education, certifications).
  * A high score means "the resume speaks the posting's language"; it does NOT
    mean the resume is good, and a *missing* term is a prompt to consider adding
    it back from omitted.md — not proof of a gap.

No AI, no network, stdlib + pyyaml only, so it is fast, free, and reproducible.

CLI:
  coverage.py --instance output/<slug>/instance.yaml [--jd <file>] [--out <file>]

--jd defaults to the sibling job_description.txt beside the instance. --out
defaults to coverage.md in the same folder. Prints a one-line JSON summary to
stdout ({"score": .., "covered": .., "total": ..}).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

import yaml

# Boilerplate that is common to nearly every posting and carries no signal about
# THIS role — folded into the stopword set so it never becomes a "key term".
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "but", "by",
    "can", "do", "does", "for", "from", "had", "has", "have", "how", "in",
    "into", "is", "it", "its", "of", "on", "or", "our", "that", "the", "their",
    "them", "they", "this", "to", "up", "was", "we", "were", "what", "when",
    "which", "who", "will", "with", "within", "you", "your", "about", "across",
    "all", "also", "any", "more", "most", "not", "other", "over", "per", "so",
    "such", "than", "then", "these", "those", "through", "under", "using", "via",
    # résumé / posting boilerplate
    "ability", "able", "candidate", "candidates", "company", "day", "description",
    "environment", "etc", "experience", "experienced", "following", "including",
    "job", "join", "key", "including", "level", "like", "looking", "must", "new",
    "opportunity", "plus", "position", "preferred", "provide", "qualifications",
    "related", "required", "requirements", "responsibilities", "role", "roles",
    "skills", "strong", "team", "teams", "us", "well", "work", "working",
    "would", "year", "years", "eg", "e.g", "i.e", "ie", "based", "help", "make",
    "including", "including", "part", "including", "every", "including", "we're",
    "we'll", "you'll", "you're", "including", "high", "including", "including",
}

# Common French glue words (accent-folded to match _norm's output). Many
# postings for Canadian roles are bilingual EN/FR; without this the French half
# floods the term list with connectives. Content words (projet, gestion, santé…)
# are deliberately NOT here — they are the signal we use to *detect* a bilingual
# posting and warn that the score understates true relevance.
FR_STOPWORDS = {
    "le", "la", "les", "un", "une", "des", "du", "de", "et", "en", "au", "aux",
    "pour", "avec", "dans", "dan", "sur", "par", "que", "qui", "est", "sont",
    "ce", "cette", "ces", "son", "sa", "ses", "leur", "nous", "vous", "votre",
    "notre", "ainsi", "comme", "plus", "ou", "ne", "pas", "se", "il", "elle",
    "vos", "nos", "afin", "tout", "tous", "toute", "entre", "chez",
}

# A token starts on alphanumerics and must END on one too (or +/# for c++/c#),
# so trailing punctuation like the period in 'management.' is never captured —
# otherwise 'management' and 'management.' count as different words and phrase
# frequencies collapse. Internal dots/hyphens survive (node.js, end-to-end).
WORD_RE = re.compile(r"[a-z0-9](?:[a-z0-9+#.\-]*[a-z0-9+#])?")
MAX_TERMS = 25            # cap on how many JD terms we score against
MIN_COUNT = 2            # a term must occur at least this often in the JD
MAX_BIGRAMS = 12         # of MAX_TERMS, at most this many two-word phrases


def _norm(text: str) -> str:
    """Lowercase and fold accents (santé → sante, café → cafe) so accented words
    stay whole instead of shredding on the non-ASCII byte — otherwise a bilingual
    posting turns into junk fragments ('comp', 'tences'). Diacritic-only; it does
    not translate, so genuinely foreign-language terms are handled as a
    documented limitation, not silently mangled."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _tokens(text: str) -> list[str]:
    return WORD_RE.findall(_norm(text))


def _stem(word: str) -> str:
    """Very light stemming so 'launches'/'launch' and 'partners'/'partner'
    match. Deliberately crude — this is a keyword screen, not linguistics."""
    for suf in ("ing", "ies", "es", "s"):
        if word.endswith(suf) and len(word) - len(suf) >= 3:
            base = word[: -len(suf)]
            return base + "y" if suf == "ies" else base
    return word


ALL_STOPWORDS = STOPWORDS | FR_STOPWORDS


def is_bilingual(jd_text: str) -> bool:
    """True when French glue words are common enough that the posting is likely
    bilingual EN/FR — in which case an English resume mechanically can't cover
    the French terms and the score understates true relevance."""
    toks = _tokens(jd_text)
    if len(toks) < 40:
        return False
    fr = sum(1 for t in toks if t in FR_STOPWORDS)
    return fr / len(toks) > 0.04


def extract_jd_terms(jd_text: str) -> list[str]:
    """The posting's salient terms: frequent non-stopword unigrams plus the most
    frequent adjacent two-word phrases, ranked and capped. Deterministic given
    the same text."""
    toks = _tokens(jd_text)
    content = [t for t in toks if t not in ALL_STOPWORDS and len(t) > 2]

    # Count by stem (so launch/launches collapse) but remember each stem's most
    # common surface spelling, so we DISPLAY 'kubernetes', not the stem
    # 'kubernet'. Ties in surface frequency break alphabetically for determinism.
    unigram_freq: dict[str, int] = {}
    surface: dict[str, dict[str, int]] = {}
    for t in content:
        s = _stem(t)
        unigram_freq[s] = unigram_freq.get(s, 0) + 1
        surface.setdefault(s, {})[t] = surface.setdefault(s, {}).get(t, 0) + 1

    def _display(stem: str) -> str:
        forms = surface[stem]
        return sorted(forms, key=lambda w: (-forms[w], w))[0]

    # Bigrams from the ORIGINAL token stream, skipping any pair touching a
    # stopword so phrases like "of the" never form.
    bigram_freq: dict[str, int] = {}
    for a, b in zip(toks, toks[1:]):
        if a in ALL_STOPWORDS or b in ALL_STOPWORDS or len(a) <= 2 or len(b) <= 2:
            continue
        bigram_freq[f"{a} {b}"] = bigram_freq.get(f"{a} {b}", 0) + 1

    # Rank bigrams first (more specific), then fill with unigrams not already
    # represented inside a chosen bigram. Ties broken alphabetically for a
    # stable, reproducible ordering.
    bigrams = sorted(
        (t for t, c in bigram_freq.items() if c >= MIN_COUNT),
        key=lambda t: (-bigram_freq[t], t),
    )[:MAX_BIGRAMS]
    # Stem the bigram's words so their unigram forms (e.g. 'business' inside
    # 'business development') are recognised as already-represented and dropped.
    bigram_words = {_stem(w) for bg in bigrams for w in bg.split()}

    unigram_stems = sorted(
        (s for s, c in unigram_freq.items()
         if c >= MIN_COUNT and s not in bigram_words),
        key=lambda s: (-unigram_freq[s], s),
    )
    unigrams = [_display(s) for s in unigram_stems]

    terms = bigrams + unigrams
    # Preserve order (bigrams then unigrams) while trimming to the cap.
    return terms[:MAX_TERMS]


def resume_text(instance: dict) -> str:
    """Every string a reader actually sees on the rendered resume, concatenated
    so we can test term presence against it."""
    parts: list[str] = [str(instance.get("summary", ""))]
    for exp in instance.get("experience", []):
        parts.append(str(exp.get("title", "")))
        parts.append(str(exp.get("company", "")))
        for b in exp.get("bullets", []):
            parts.append(str(b.get("text", "")))
    for hl in instance.get("highlights", []):
        parts.append(f"{hl.get('value', '')} {hl.get('label', '')}")
    for group in instance.get("skills", []):
        parts.append(str(group.get("label", "")))
        parts.extend(str(i) for i in group.get("items", []))
    for edu in instance.get("education", []):
        parts.append(f"{edu.get('degree', '')} {edu.get('detail', '')}")
    for cert in instance.get("certifications", []):
        parts.append(str(cert.get("name", "")))
    return " ".join(parts)


def score(jd_text: str, resume: str) -> dict:
    terms = extract_jd_terms(jd_text)
    resume_norm = _norm(resume)
    resume_stems = {_stem(t) for t in _tokens(resume)}

    covered, missing = [], []
    for term in terms:
        words = term.split()
        if len(words) == 1:
            hit = _stem(words[0]) in resume_stems
        else:
            # phrase present verbatim, OR both stems present anywhere.
            hit = term in resume_norm or all(_stem(w) in resume_stems for w in words)
        (covered if hit else missing).append(term)

    total = len(terms)
    pct = round(100 * len(covered) / total) if total else 0
    return {"score": pct, "covered": covered, "missing": missing,
            "total": total, "bilingual": is_bilingual(jd_text)}


def render_markdown(result: dict, slug: str) -> str:
    covered = result["covered"]
    missing = result["missing"]
    total = result["total"]
    lines = [
        f"# JD coverage — {slug}",
        "",
        f"**{result['score']}%** of the job posting's key terms appear on the "
        f"resume ({len(covered)} of {total}).",
        "",
        "> Heuristic keyword screen (like an ATS), **not** a quality verdict. A "
        "missing term is a nudge to check `omitted.md` for content you could add "
        "back — not proof of a gap. Truthfulness is enforced separately by "
        "`validate.py`.",
        "",
    ]
    if result.get("bilingual"):
        lines += [
            "> ⚠️ **This posting looks bilingual (EN/FR).** Roughly half its text "
            "is in French, which an English resume can't match — so this score "
            "*understates* true relevance. Read it as a floor, not a verdict.",
            "",
        ]
    lines += [
        f"## Covered ({len(covered)})",
        "",
    ]
    lines += [f"- {t}" for t in covered] or ["- _(none)_"]
    lines += ["", f"## Missing ({len(missing)})", ""]
    lines += [f"- {t}" for t in missing] or ["- _(none — full coverage)_"]
    lines.append("")
    return "\n".join(lines)


def write_coverage(instance_path: Path, jd_path: Path | None = None,
                   out_path: Path | None = None) -> dict:
    """Compute coverage for a rendered instance and write coverage.md beside it.
    Returns the score dict. Raises FileNotFoundError if inputs are missing."""
    instance_path = Path(instance_path)
    folder = instance_path.resolve().parent
    if jd_path is None:
        jd_path = folder / "job_description.txt"
    jd_path = Path(jd_path)
    if out_path is None:
        out_path = folder / "coverage.md"

    instance = yaml.safe_load(instance_path.read_text(encoding="utf-8"))
    jd_text = jd_path.read_text(encoding="utf-8")
    result = score(jd_text, resume_text(instance))
    Path(out_path).write_text(
        render_markdown(result, folder.name), encoding="utf-8")
    result["output_file"] = str(out_path)
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="coverage")
    ap.add_argument("--instance", required=True, help="path to instance.yaml")
    ap.add_argument("--jd", help="job-description text file "
                                 "(default: sibling job_description.txt)")
    ap.add_argument("--out", help="output markdown path "
                                  "(default: coverage.md beside the instance)")
    args = ap.parse_args(argv)
    try:
        result = write_coverage(
            Path(args.instance),
            Path(args.jd) if args.jd else None,
            Path(args.out) if args.out else None,
        )
    except FileNotFoundError as e:
        print(f"coverage: {e}", file=sys.stderr)
        return 4
    print(json.dumps({k: result[k] for k in ("score", "covered", "total", "output_file")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
