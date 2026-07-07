"""Tests for scripts/coverage.py — the deterministic JD-coverage scorer.

Coverage is a heuristic *relevance* signal (an ATS-style keyword screen), the
counterpart to validate.py's *truthfulness* check. These tests pin the
behaviours that make the number trustworthy and reproducible: accent folding,
bilingual detection, phrase/stem matching, and deterministic term selection.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import coverage as cov  # noqa: E402


def test_accent_folding_keeps_words_whole():
    # 'santé' must fold to 'sante' as one token, not shred into 'sant'.
    assert cov._tokens("Santé publique") == ["sante", "publique"]


def test_stemming_matches_singular_and_plural():
    assert cov._stem("launches") == cov._stem("launch")
    assert cov._stem("partners") == cov._stem("partner")


def test_extract_terms_ranks_repeated_phrases_first():
    jd = ("Business development leader. Business development strategy. "
          "Business development pipeline. We value partnerships and pipeline.")
    terms = cov.extract_jd_terms(jd)
    assert "business development" in terms
    # A two-word phrase should outrank a bare unigram it contains.
    assert terms.index("business development") < len(terms)
    # The unigram 'business' should not also appear (deduped by the bigram).
    assert "business" not in terms


def test_extract_terms_is_deterministic():
    jd = "Alpha beta alpha beta gamma gamma delta delta epsilon epsilon zeta"
    assert cov.extract_jd_terms(jd) == cov.extract_jd_terms(jd)


def test_score_counts_present_terms():
    jd = ("Stakeholder management stakeholder management. Vendor negotiation "
          "vendor negotiation. Budget budget forecasting forecasting.")
    resume = ("Led stakeholder management across teams and ran vendor "
              "negotiation for budget planning.")
    result = cov.score(jd, resume)
    assert "stakeholder management" in result["covered"]
    assert "vendor negotiation" in result["covered"]
    assert 0 <= result["score"] <= 100
    assert result["total"] == len(result["covered"]) + len(result["missing"])


def test_score_flags_missing_terms():
    jd = "Kubernetes kubernetes deployment. Kubernetes cluster orchestration."
    resume = "Managed spreadsheets and stakeholder reports."
    result = cov.score(jd, resume)
    assert result["score"] < 50
    assert any("kubernetes" in m for m in result["missing"])


def test_bilingual_detection():
    english = ("We are looking for a project manager to lead product launches "
               "and manage stakeholders across the organization every week.") * 2
    bilingual = english + " " + (
        "Nous recherchons un chef de projet pour diriger des lancements et "
        "gerer les parties prenantes dans toute l organisation avec succes.") * 3
    assert cov.is_bilingual(bilingual) is True
    assert cov.is_bilingual(english) is False


def test_write_coverage_roundtrip(tmp_path):
    import yaml
    inst = {
        "summary": "Project manager delivering cross-functional launches.",
        "experience": [{"title": "Program Manager", "company": "Acme",
                        "bullets": [{"text": "Led vendor negotiation and budget planning."}]}],
        "skills": [{"label": "Delivery", "items": ["Stakeholder management"]}],
    }
    inst_path = tmp_path / "instance.yaml"
    inst_path.write_text(yaml.safe_dump(inst), encoding="utf-8")
    jd_path = tmp_path / "job_description.txt"
    jd_path.write_text(
        "Vendor negotiation vendor negotiation. Stakeholder management "
        "stakeholder management. Budget budget planning planning.",
        encoding="utf-8")

    result = cov.write_coverage(inst_path)  # jd defaults to the sibling file
    md = (tmp_path / "coverage.md").read_text(encoding="utf-8")
    assert "JD coverage" in md
    assert f"{result['score']}%" in md
    assert result["score"] > 0
