"""Deterministic (no-LLM) JD-coverage scoring, gap analysis, and selection depth.

This is the missing feedback half of the pipeline. `validate.py` proves the
instance is *truthful* (nothing invented, every locked field verbatim); it says
nothing about how *well* the selection matches the job. This module measures
that, deterministically, so:

  * the render JSON can carry a `coverage` block the tailoring agent reads to
    decide whether to swap a bullet back in (improvements 1 & 2);
  * a human gets a `coverage.md` that separates "you have this, you just didn't
    pick it" (a selection gap — fixable now) from "your master.yaml has nothing
    on this" (a content gap — enrich the bank, never fake it); and
  * the report exposes how aggressively content was trimmed and a coarse
    confidence read (improvement 3).

No AI, no third-party deps — pure stdlib, so it runs inside the same Docker
render step and is fully reproducible. The score is an ATS-style keyword screen,
NOT a quality verdict: a missing term is a nudge, not proof of a gap.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from typing import Any, Iterable

# -----------------------------------------------------------------------------
# Tokenization
# -----------------------------------------------------------------------------
# A compact, domain-neutral stopword set. Kept small on purpose: over-filtering
# hides real JD terms, and the frequency ranking already suppresses filler.
#
# Written unstemmed for readability; `_STOPWORDS` below is the stemmed set that
# callers actually test against. Membership is always checked on a stemmed
# token, so an unstemmed plural here would never match (see _STOPWORDS).
_STOPWORDS_RAW = {
    "a", "an", "the", "and", "or", "but", "if", "of", "to", "in", "on", "for",
    "with", "at", "by", "from", "as", "is", "are", "was", "were", "be", "been",
    "being", "this", "that", "these", "those", "it", "its", "will", "would",
    "can", "could", "should", "may", "might", "must", "have", "has", "had",
    "do", "does", "did", "not", "no", "you", "your", "we", "our", "they",
    "their", "he", "she", "his", "her", "them", "who", "which", "what", "when",
    "where", "how", "all", "any", "both", "each", "more", "most", "other",
    "some", "such", "than", "too", "very", "s", "t", "just", "into", "over",
    "up", "out", "about", "across", "per", "via", "within", "including",
    "etc", "e.g", "i.e", "also", "well", "able", "using", "use", "used",
    "work", "working", "role", "position", "job", "team", "teams", "years",
    "year", "including", "ability", "strong", "excellent", "including",
    "responsibilities", "requirements", "qualifications", "preferred",
    "plus", "new", "key", "including", "including",
    # Survives tokenization as one token because of the internal slash.
    "and/or",
}

# JD connective tissue: words a posting uses to *phrase* a duty rather than to
# name a skill. Without these, frequency ranking surfaces "considerable
# experience" and "conducts research" as top terms and a resume gets scored on
# whether it echoes the posting's prose style. Kept to words that carry no
# domain meaning on their own — anything a reader could mistake for a skill
# ("analysis", "budget", "compliance") stays out of this set.
_BOILERPLATE = {
    # Evaluative filler — grades a skill, never names one.
    "considerable", "various", "detailed", "specific", "effective",
    "effectively", "related", "relevant", "appropriate", "necessary",
    "successful", "proven", "demonstrated", "general", "overall", "strong",
    # Weak verbs. Dropping these is what lets the *object* surface on its own:
    # "conducts research" stops eating a slot, and "research" scores as a
    # unigram instead. Stronger verbs a resume genuinely echoes — prepare,
    # review, maintain, support, analyze, manage — are deliberately absent.
    "ensure", "ensuring", "conduct", "conducted", "conducting",
    "take", "taken", "taking", "provide", "provided", "providing",
    "perform", "performed", "performing", "considered",
    # Posting scaffolding: hiring-process prose, not the job.
    "duties", "assigned", "candidate", "applicant", "applicable", "please",
    "apply", "employment", "equity", "diversity", "accommodation",
}
_STOPWORDS_RAW |= _BOILERPLATE

# A token starts and ends on an alphanumeric, so trailing sentence punctuation
# ("chains." -> "chains") never sticks. Internal +#/&.'- keep "modern-trade",
# "e.g", and "r&d" intact.
_TOKEN_RE = re.compile(r"[a-zA-Z0-9]+(?:[+#/&.'\-][a-zA-Z0-9]+)*")

# Cosmetic character folds shared with validate._normalize's intent: we compare
# on meaning, not on which flavor of quote/dash a document happened to use.
_COSMETIC_MAP = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "…": "...", "·": " ",
}


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    return text.translate(str.maketrans(_COSMETIC_MAP))


def _stem(token: str) -> str:
    """Crude, deterministic plural fold. Applied to BOTH the JD side and the
    resume side.

    Being applied to both sides is not enough on its own — the fold must also
    map a word and its plural to the *same* stem, or a JD term never matches the
    resume's own wording of it. A blanket "…es" -> strip-two rule failed that:
    'policies' -> 'polici' while 'policy' -> 'policy', and 'takes' -> 'tak'
    while 'take' -> 'take', so those pairs silently scored as misses. Hence the
    'ies' -> 'y' rule, and stripping 'es' only after a sibilant, where English
    actually adds it ('processes' -> 'process').

    The sibilant test must look at the token's own suffix, not at whether the
    stripped stem happens to end in a sibilant letter: 'cases'[:-2] is 'cas',
    which ends in 's' — but that 's' belongs to 'case', so stripping two gave
    'cas' while 'case' stayed 'case' (same for database/release/expense/
    license). Matching the explicit sibilant+es suffixes lets those fall
    through to the plain '-s' rule instead.
    """
    t = token.lower()
    if len(t) > 4 and t.endswith("ies"):
        return t[:-3] + "y"                       # policies -> policy
    if len(t) > 4 and t.endswith(("sses", "xes", "zes", "ches", "shes")):
        return t[:-2]                             # processes -> process, boxes -> box
    if len(t) > 3 and t.endswith("s") and not t.endswith("ss"):
        return t[:-1]                             # systems -> system, takes -> take
    return t


# Stopwords are tested against *stemmed* tokens, so the set itself must be
# stemmed. Without this, every plural entry silently leaked back in as a content
# word ("requirements" stems to "requirement", which was not in the raw set), and
# JD boilerplate scored as a key term.
_STOPWORDS = {_stem(w) for w in _STOPWORDS_RAW}


def tokens(text: str) -> list[str]:
    """Ordered, stemmed content tokens (stopwords kept here so bigrams stay
    positional; callers drop stopwords as needed)."""
    return [_stem(m.group()) for m in _TOKEN_RE.finditer(_fold(text).lower())]


def token_set(text: str) -> set[str]:
    """Unordered stemmed content tokens with stopwords removed — the bag a
    keyphrase is checked against."""
    return {t for t in tokens(text) if t not in _STOPWORDS and len(t) > 1}


# -----------------------------------------------------------------------------
# JD keyphrase extraction
# -----------------------------------------------------------------------------
class Keyphrase:
    """A salient JD term. `display` is human-readable (original casing/words);
    `stems` are the stemmed tokens matched against a resume's token bag."""

    __slots__ = ("display", "stems")

    def __init__(self, display: str, stems: tuple[str, ...]):
        self.display = display
        self.stems = stems

    def covered_by(self, bag: set[str]) -> bool:
        return all(s in bag for s in self.stems)


def extract_keyphrases(
    jd_text: str, limit: int = 25, unigram_share: float = 0.4
) -> list[Keyphrase]:
    """Rank the JD's most salient terms: bigrams of adjacent content words
    (they're specific — 'business analysis', 'acceptance testing') alongside
    single content words by frequency.

    Both kinds get a reserved share of `limit` — `unigram_share` of the slots go
    to unigrams — and whichever side runs out first donates its unused slots to
    the other. This split is load-bearing: ranking bigrams ahead of unigrams and
    filling to `limit` sounds equivalent, but a real JD offers hundreds of
    bigrams, so unigrams never survived the cut and salient one-word terms
    ('stakeholder', 'reporting', 'budget') scored zero no matter how often the
    resume said them.
    """
    folded = _fold(jd_text)
    matches = list(_TOKEN_RE.finditer(folded))
    lowered = [m.group().lower() for m in matches]
    stemmed = [_stem(m.group()) for m in matches]

    def is_content(i: int) -> bool:
        # Pure numbers are posting scaffolding, never a skill: they gave us
        # "799 islington" (the office address), "35 hours/week", "18 months".
        # Alphanumerics survive, so "p3", "iso9001", and "sql" still count.
        if stemmed[i].isdigit():
            return False
        return stemmed[i] not in _STOPWORDS and len(stemmed[i]) > 1

    def adjacent(i: int) -> bool:
        # Only tokens separated by plain spaces/tabs form a bigram — a comma,
        # period, or line break between them is a phrase boundary, so we never
        # invent cross-clause bigrams like "chains experience".
        gap = folded[matches[i].end():matches[i + 1].start()]
        return gap == "" or gap.strip(" \t") == ""

    bigram_counts: Counter[tuple[str, str]] = Counter()
    bigram_display: dict[tuple[str, str], str] = {}
    for i in range(len(matches) - 1):
        if is_content(i) and is_content(i + 1) and adjacent(i) and stemmed[i] != stemmed[i + 1]:
            key = (stemmed[i], stemmed[i + 1])
            bigram_counts[key] += 1
            bigram_display.setdefault(key, f"{lowered[i]} {lowered[i + 1]}")

    unigram_counts: Counter[str] = Counter()
    unigram_display: dict[str, str] = {}
    for i in range(len(matches)):
        if is_content(i):
            unigram_counts[stemmed[i]] += 1
            unigram_display.setdefault(stemmed[i], lowered[i])

    phrases: list[Keyphrase] = []
    seen: set[tuple[str, ...]] = set()

    # Bigrams first (more specific), then unigrams — both ranked by frequency.
    # Unigrams are NOT suppressed for appearing inside a bigram: a JD bigram
    # whose partner word is absent shouldn't hide the salient word's own
    # coverage (e.g. "distribution" must still count even under "manage
    # distribution").
    # Rank bigrams by their own count, then by how salient their two words are
    # on their own (summed unigram frequency). The second key does nearly all
    # the work: in a single posting ~98% of bigrams occur exactly once, so
    # count alone is a near-universal tie. That tie used to fall through to an
    # alphabetical tiebreak, which is why the term list read "account
    # developments, act professionally, and/or operations" — the front of the
    # alphabet rather than the heart of the job. Weighting by constituent
    # salience puts "business analyst" and "analytical skills" on top instead.
    def _bigram_rank(kv: tuple[tuple[str, str], int]) -> tuple:
        (a, b), count = kv
        return (-count, -(unigram_counts[a] + unigram_counts[b]), bigram_display[(a, b)])

    ranked_bigrams = sorted(bigram_counts.items(), key=_bigram_rank)
    ranked_unigrams = sorted(unigram_counts.items(), key=lambda kv: (-kv[1], kv[0]))

    # Reserve each side its share, then let the shorter side's leftovers go to
    # the other so a JD that is all prose (or all jargon) still fills `limit`.
    want_uni = min(len(ranked_unigrams), max(1, round(limit * unigram_share)))
    want_big = min(len(ranked_bigrams), limit - want_uni)
    want_uni = min(len(ranked_unigrams), limit - want_big)

    for key, _ in ranked_bigrams[:want_big]:
        if key in seen:
            continue
        phrases.append(Keyphrase(bigram_display[key], key))
        seen.add(key)
    for stem, _ in ranked_unigrams[:want_uni]:
        if (stem,) in seen:
            continue
        phrases.append(Keyphrase(unigram_display[stem], (stem,)))
        seen.add((stem,))
    return phrases


# -----------------------------------------------------------------------------
# Resume / master text harvesting
# -----------------------------------------------------------------------------
def instance_text(instance: dict) -> str:
    """Everything a reader/ATS actually sees on the rendered resume."""
    parts: list[str] = [str(instance.get("summary", ""))]
    for exp in instance.get("experience", []):
        parts += [str(exp.get("title", "")), str(exp.get("company", ""))]
        for b in exp.get("bullets", []):
            parts.append(str(b.get("text", "")))
    for hl in instance.get("highlights", []):
        parts.append(str(hl.get("label", "")))
    for group in instance.get("skills", []):
        parts.append(str(group.get("label", "")))
        parts += [str(i) for i in group.get("items", [])]
    return " ".join(parts)


def master_text(master: dict) -> str:
    """Every term the bank *could* surface: all bullet variants, all their
    themes, and every skill item — the universe a selection gap is measured
    against."""
    parts: list[str] = []
    for exp in master.get("experience", []):
        parts += [str(exp.get("title", "")), str(exp.get("company", ""))]
        for b in exp.get("bullets", []):
            parts += [str(t).replace("-", " ") for t in b.get("themes", [])]
            for text in b.get("variants", {}).values():
                parts.append(str(text))
    for group in master.get("skills", {}).values():
        parts.append(str(group.get("label", "")))
        parts += [str(i) for i in group.get("items", [])]
    for s in master.get("summaries", []):
        parts.append(str(s.get("text", "")))
    return " ".join(parts)


# -----------------------------------------------------------------------------
# Selection depth
# -----------------------------------------------------------------------------
def selection_depth(instance: dict, master: dict) -> dict:
    """How much of the bank made the page, and a coarse read on whether the
    result looks thin (heavy trimming / few bullets) vs. full."""
    avail_bullets = sum(len(e.get("bullets", [])) for e in master.get("experience", []))
    sel_bullets = sum(len(e.get("bullets", [])) for e in instance.get("experience", []))
    avail_roles = len(master.get("experience", []))
    sel_roles = len(instance.get("experience", []))

    additional_ids = {e.get("id") for e in master.get("experience", []) if e.get("additional")}
    sel_ids = {e.get("id") for e in instance.get("experience", [])}
    additional_dropped = bool(additional_ids) and not (additional_ids & sel_ids)

    ratio = round(sel_bullets / avail_bullets, 3) if avail_bullets else None
    return {
        "bullets_selected": sel_bullets,
        "bullets_available": avail_bullets,
        "bullet_ratio": ratio,
        "roles_selected": sel_roles,
        "roles_available": avail_roles,
        "additional_role_dropped": additional_dropped,
    }


# -----------------------------------------------------------------------------
# Profile suggestion (deterministic; a sanity signal, not the decision)
# -----------------------------------------------------------------------------
def _profile_vocab(master: dict) -> dict[str, set[str]]:
    """Build a term bag per profile from the bank: profile summary, that
    profile's bullet variants + themes, and skill groups tagged with it."""
    vocab: dict[str, set[str]] = {}
    profiles = list(master.get("profiles", {}).keys())
    for p in profiles:
        vocab[p] = set()

    for s in master.get("summaries", []):
        p = s.get("profile")
        if p in vocab:
            vocab[p] |= token_set(str(s.get("text", "")))

    for exp in master.get("experience", []):
        for b in exp.get("bullets", []):
            theme_terms = token_set(" ".join(str(t).replace("-", " ") for t in b.get("themes", [])))
            for p, text in b.get("variants", {}).items():
                if p in vocab:
                    vocab[p] |= token_set(str(text)) | theme_terms

    for group in master.get("skills", {}).values():
        terms = token_set(group.get("label", "") + " " + " ".join(group.get("items", [])))
        for p in group.get("profiles", []):
            if p in vocab:
                vocab[p] |= terms
    return vocab


def suggest_profile(jd_text: str, master: dict) -> dict:
    """Score each profile by how many of its distinctive terms the JD hits.
    Deterministic, so it's regression-testable and gives a cheap check on the
    LLM's own profile pick (a large disagreement is worth a human glance).
    `general` is excluded from winning — it's the neutral fallback, not an
    angle — but reported for reference."""
    jd_bag = token_set(jd_text)
    vocab = _profile_vocab(master)
    scores = {p: len(jd_bag & terms) for p, terms in vocab.items()}
    ranked = [p for p in sorted(scores, key=lambda p: (-scores[p], p)) if p != "general"]
    suggested = ranked[0] if ranked and scores[ranked[0]] > 0 else "general"
    return {"suggested": suggested, "scores": scores}


# -----------------------------------------------------------------------------
# Top-level report
# -----------------------------------------------------------------------------
def coverage_report(jd_text: str, instance: dict, master: dict, limit: int = 25) -> dict:
    """Full deterministic coverage/gap/depth report for one instance + JD."""
    phrases = extract_keyphrases(jd_text, limit=limit)
    resume_bag = token_set(instance_text(instance))
    master_bag = token_set(master_text(master))

    covered: list[str] = []
    selection_gap: list[str] = []   # in the bank, just not selected — fixable now
    content_gap: list[str] = []     # nowhere in the bank — enrich master.yaml, never fake
    for kp in phrases:
        if kp.covered_by(resume_bag):
            covered.append(kp.display)
        elif kp.covered_by(master_bag):
            selection_gap.append(kp.display)
        else:
            content_gap.append(kp.display)

    total = len(phrases)
    score = round(len(covered) / total, 3) if total else None

    depth = selection_depth(instance, master)
    # Coarse confidence: "thin" when the keyword screen is low OR the page is
    # sparse. A nudge for the human/agent, not a gate.
    thin = (score is not None and score < 0.20) or depth["bullets_selected"] <= 5
    depth["confidence"] = "thin" if thin else "ok"

    return {
        "score": score,
        "terms_total": total,
        "terms_covered": len(covered),
        "covered": covered,
        "selection_gap": selection_gap,
        "content_gap": content_gap,
        "profile": suggest_profile(jd_text, master),
        "depth": depth,
    }


# -----------------------------------------------------------------------------
# Markdown rendering (the human-facing coverage.md)
# -----------------------------------------------------------------------------
def _bullet_list(items: Iterable[str]) -> str:
    items = list(items)
    return "\n".join(f"- {i}" for i in items) if items else "_(none)_"


def render_markdown(report: dict, slug: str, instance: dict) -> str:
    score = report["score"]
    pct = f"{round(score * 100)}%" if score is not None else "n/a"
    depth = report["depth"]
    prof = report["profile"]
    chosen = instance.get("profile")
    agree = "" if chosen == prof["suggested"] else (
        f" ⚠ instance chose **{chosen}** — worth a glance"
    )

    lines = [
        f"# JD coverage — {slug}",
        "",
        f"**{pct}** of the job posting's key terms appear on the resume "
        f"({report['terms_covered']} of {report['terms_total']}).",
        "",
        "> Heuristic keyword screen (like an ATS), **not** a quality verdict. "
        "A missing term is a nudge, not proof of a gap; truthfulness is enforced "
        "separately by `validate.py`.",
        "",
        f"Suggested profile (deterministic): **{prof['suggested']}**{agree}  ",
        f"Selection depth: **{depth['bullets_selected']}/{depth['bullets_available']}** "
        f"bullets, **{depth['roles_selected']}/{depth['roles_available']}** roles, "
        f"confidence **{depth['confidence']}**"
        + ("  ·  additional role dropped" if depth["additional_role_dropped"] else ""),
        "",
        f"## Covered ({len(report['covered'])})",
        "",
        _bullet_list(report["covered"]),
        "",
        f"## Missing — in your master.yaml, not selected ({len(report['selection_gap'])})",
        "",
        "You already have content that speaks to these; consider swapping a "
        "relevant bullet back in (still verbatim) if the page has room. See "
        "`omitted.md`.",
        "",
        _bullet_list(report["selection_gap"]),
        "",
        f"## Missing — not in your master.yaml ({len(report['content_gap'])})",
        "",
        "The bank has nothing on these. If they're truly part of your "
        "experience, add them to `master.yaml` — never invent them to score.",
        "",
        _bullet_list(report["content_gap"]),
        "",
    ]
    return "\n".join(lines)
