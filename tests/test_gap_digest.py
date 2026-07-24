"""Tests for the content-gap digest.

Unlike test_coverage.py these do NOT need the private master.yaml: the whole
point of the digest is to aggregate across runs, so the fixture ships its own
self-contained mini bank plus two synthetic run folders
(tests/fixtures/gap_runs/). run-alpha and run-beta both want "kubernetes" (a
recurring content gap the bank has nothing on); alpha alone wants "terraform",
beta alone wants "graphql" (one-offs). Both cover python/sql (in the bank), so
those must never surface as gaps.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import gap_digest  # noqa: E402
import validate as validate_mod  # noqa: E402

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "gap_runs"


def _master() -> dict:
    return validate_mod.load_yaml(FIXTURES / "master.yaml")


def test_iter_run_dirs_finds_complete_runs():
    slugs = sorted(d.name for d in gap_digest.iter_run_dirs(FIXTURES))
    assert slugs == ["run-alpha", "run-beta"]


def test_recurring_gap_ranked_first_with_all_slugs():
    md, ranked, n_runs = gap_digest.build_digest(FIXTURES, _master())
    assert n_runs == 2
    top = ranked[0]
    assert top.display == "kubernetes"
    assert top.postings == 2
    # Mentioned twice in each of the two postings — the tally counts real JD
    # hits, not just the number of runs, so it can exceed `postings`.
    assert top.occurrences == 4
    assert sorted(top.slugs) == ["run-alpha", "run-beta"]


def test_one_off_gaps_are_per_posting():
    _md, ranked, _n = gap_digest.build_digest(FIXTURES, _master())
    by_display = {t.display: t for t in ranked}
    assert by_display["terraform"].slugs == ["run-alpha"]
    assert by_display["graphql"].slugs == ["run-beta"]


def test_covered_bank_terms_never_appear_as_standalone_gaps():
    _md, ranked, _n = gap_digest.build_digest(FIXTURES, _master())
    # python and sql are in the bank AND on both resumes, so neither is a
    # content gap on its own. (They can still ride along inside a bigram gap
    # whose *other* word is missing — that's the bigram's gap, not theirs.)
    unigram_gap_stems = {t.stems[0] for t in ranked if len(t.stems) == 1}
    assert "python" not in unigram_gap_stems
    assert "sql" not in unigram_gap_stems


def test_markdown_has_recurring_table_and_no_fake_note():
    md, _ranked, _n = gap_digest.build_digest(FIXTURES, _master())
    assert "# Content-gap digest" in md
    assert "across **2**" in md
    assert "Recurring" in md
    assert "kubernetes" in md
    # The truthfulness guard must be visible in the wording.
    assert "to-fake" in md
    assert "truly part of your experience" in md


def test_empty_output_root_renders_clean_message():
    md = gap_digest.render_markdown([], n_runs=0)
    assert "No content gaps found" in md
