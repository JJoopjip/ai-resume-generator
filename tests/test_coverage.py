"""Golden regression tests for the deterministic coverage/gap/depth module.

These lock in behavior that has no other guardrail: the JD-fit keyword screen,
the selection-gap vs content-gap split, selection depth, and the deterministic
profile suggestion. They run against the real master.yaml content bank so a
prompt/content change that quietly breaks scoring shows up here.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import coverage as cov  # noqa: E402
import validate as v  # noqa: E402

MASTER_PATH = REPO_ROOT / "master.yaml"


@pytest.fixture(scope="module")
def master():
    if not MASTER_PATH.exists():
        pytest.skip("master.yaml is private and not checked in (fresh/CI checkout)")
    return v.load_yaml(MASTER_PATH)


def _bd_instance(master):
    """A minimal bd-profile instance: just Winnergy's B2C bullet, so we know
    exactly which terms are 'selected'."""
    winnergy = next(e for e in master["experience"] if e["id"] == "winnergy")
    win_b2c = next(b for b in winnergy["bullets"] if b["id"] == "win_b2c")
    return {
        "profile": "bd",
        "summary": "Business development professional opening new channels.",
        "experience": [
            {
                "id": "winnergy",
                "title": winnergy["title"],
                "company": winnergy["company"],
                "bullets": [{"id": "win_b2c", "text": win_b2c["variants"]["bd"]}],
            }
        ],
        "skills": [{"label": "Business Development & Partnerships",
                    "items": ["Channel development"]}],
    }


# --- profile suggestion (deterministic JD -> profile) -------------------------
def test_profile_suggestion_pm(master):
    jd = ("Seeking a PMP-certified project manager to lead cross-functional "
          "program delivery, managing scope, schedule, and budget across Agile "
          "and Waterfall, coordinating regulatory compliance, risk and issue "
          "management, stakeholder management and KPI reporting.")
    assert cov.suggest_profile(jd, master)["suggested"] == "pm"


def test_profile_suggestion_bd(master):
    jd = ("Business development manager to source and negotiate partners, build "
          "channel and pipeline, drive market entry and expansion, and own "
          "account management and retention across the portfolio.")
    assert cov.suggest_profile(jd, master)["suggested"] == "bd"


def test_profile_suggestion_dm(master):
    jd = ("Digital marketing and e-commerce brand manager for DTC retail and "
          "social commerce channels: run digital and email campaigns, content "
          "and creative production, and brand positioning.")
    assert cov.suggest_profile(jd, master)["suggested"] == "dm"


# --- coverage scoring + gap classification ------------------------------------
def test_covered_selection_gap_and_content_gap(master):
    instance = _bd_instance(master)
    jd = ("Manage distribution across modern-trade chains. Experience with "
          "pharmacovigilance and drug safety is required. Kubernetes deployment "
          "experience a strong plus.")
    report = cov.coverage_report(jd, instance, master)

    covered = " ".join(report["covered"]).lower()
    sel_gap = " ".join(report["selection_gap"]).lower()
    content_gap = " ".join(report["content_gap"]).lower()

    # In the selected bullet -> covered.
    assert "distribution" in covered
    # In master.yaml (skills + otsuka regulatory bullet) but not selected here.
    assert "pharmacovigilance" in sel_gap
    assert "pharmacovigilance" not in covered
    # Nowhere in the bank -> a content gap the user must NOT fabricate.
    assert "kubernetes" in content_gap


def test_score_is_a_fraction(master):
    instance = _bd_instance(master)
    jd = "Distribution, channels, partnerships, and market expansion."
    report = cov.coverage_report(jd, instance, master)
    assert 0.0 <= report["score"] <= 1.0
    assert report["terms_covered"] <= report["terms_total"]


def test_empty_jd_is_safe(master):
    report = cov.coverage_report("", _bd_instance(master), master)
    assert report["score"] is None
    assert report["terms_total"] == 0
    assert report["covered"] == []


# --- selection depth ----------------------------------------------------------
def test_selection_depth_counts_and_confidence(master):
    instance = _bd_instance(master)
    depth = cov.selection_depth(instance, master)
    total_master_bullets = sum(len(e["bullets"]) for e in master["experience"])
    assert depth["bullets_available"] == total_master_bullets
    assert depth["bullets_selected"] == 1
    assert depth["roles_selected"] == 1
    # The single-bullet instance never includes the additional (server) role.
    assert depth["additional_role_dropped"] is True

    # A one-bullet resume is unambiguously thin.
    report = cov.coverage_report("channels and distribution", instance, master)
    assert report["depth"]["confidence"] == "thin"


# --- markdown rendering -------------------------------------------------------
def test_render_markdown_has_sections(master):
    instance = _bd_instance(master)
    report = cov.coverage_report("distribution and channels", instance, master)
    md = cov.render_markdown(report, "acme-analyst-2026-01-01", instance)
    assert "# JD coverage — acme-analyst-2026-01-01" in md
    assert "## Covered" in md
    assert "not in your master.yaml" in md


# ---------------------------------------------------------------------------
# Keyphrase extraction — regressions for four scoring bugs that made the JD
# screen report near-zero coverage on resumes that genuinely matched, and fed
# the tailoring agent junk `selection_gap` terms to chase.
# ---------------------------------------------------------------------------
# A JD long enough to offer far more bigrams than the term budget, which is the
# condition under which every one of these bugs surfaced.
_JD = """
Business Analyst, Finance and Treasury. The successful candidate conducts
research and evaluates corporate policies. Considerable experience with
business process and business operations is required. Develops project plans
and detailed action plans. Reports to the Management Division at 799 Islington
Avenue, 35 hours/week, for 18 months. Provides administrative support and
ensures effective stakeholder reporting across various committees. Strong
analytical skills required. Prepares and reviews financial reporting and
maintains budget procedures.
"""


def test_unigrams_are_never_starved_by_bigrams():
    """The bug: bigrams were ranked first and `return`ed on hitting the limit,
    so a real JD (hundreds of bigrams) left zero unigram slots and one-word
    terms scored 0 no matter how often the resume said them."""
    phrases = cov.extract_keyphrases(_JD, limit=25)
    unigrams = [p for p in phrases if len(p.stems) == 1]
    assert unigrams, "unigrams were starved out by bigrams"
    assert len(unigrams) >= 5


def test_stopword_set_is_stemmed_so_plurals_do_not_leak():
    """The bug: stopwords were stored unstemmed but tested against stemmed
    tokens, so 'requirements' -> 'requirement' leaked in as a content word."""
    assert all(cov._stem(w) in cov._STOPWORDS for w in cov._STOPWORDS_RAW)
    displays = {p.display for p in cov.extract_keyphrases(_JD, limit=25)}
    assert not any("requirement" in d for d in displays)


def test_stemmer_unifies_singular_and_plural():
    """The bug: a blanket '-es' strip mapped 'policies'->'polici' but
    'policy'->'policy', so a JD term never matched the resume's own wording."""
    for singular, plural in [
        ("policy", "policies"), ("take", "takes"),
        ("process", "processes"), ("system", "systems"),
        # Singulars that themselves end in a sibilant-looking '-se': the fix's
        # first cut stripped 'es' whenever the *stem* ended in a sibilant
        # letter, so 'cases' -> 'cas' while 'case' -> 'case' — the exact
        # silent-miss class the stemmer exists to prevent.
        ("case", "cases"), ("database", "databases"), ("release", "releases"),
        ("expense", "expenses"), ("license", "licenses"), ("phase", "phases"),
        # True sibilant + es plurals must still strip the full 'es'.
        ("box", "boxes"), ("match", "matches"),
    ]:
        assert cov._stem(singular) == cov._stem(plural), (singular, plural)
    assert cov._stem("business") == "business"  # …ss is not a plural


def test_bigrams_rank_by_salience_not_alphabetically():
    """The bug: ~98% of a single JD's bigrams occur once, so the count sort tied
    and fell through to an alphabetical tiebreak — the term list was the front
    of the alphabet ('account developments', 'act professionally'), not the job."""
    displays = [p.display for p in cov.extract_keyphrases(_JD, limit=25)]
    assert "business analyst" in displays
    # Pure-numeric scaffolding must never score: address, hours, contract length.
    assert not any(t in " ".join(displays) for t in ("799", "35", "18"))


def test_salient_unigram_scores_when_the_resume_says_it():
    """End to end: the screen must credit a one-word JD term the resume uses.
    This is what reported 0% before — 'reporting' could not reach the term list."""
    phrases = cov.extract_keyphrases(_JD, limit=25)
    bag = cov.token_set("Stakeholder reporting and budget analysis for business operations")
    assert any(p.covered_by(bag) for p in phrases)
