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
