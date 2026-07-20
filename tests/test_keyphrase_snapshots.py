"""Golden-file snapshots of extract_keyphrases over real fixture postings.

A failing test here means the extractor's term list moved on a real JD. If the
change is intentional, regenerate and REVIEW the diff — it shows exactly which
terms entered/left the screen:

    python3 -m tests.regen_snapshots
"""

from pathlib import Path

import pytest

import regen_snapshots as snap

_JDS = sorted(snap.JD_DIR.glob("*.txt"))


def test_fixture_jds_exist():
    assert _JDS, f"no fixture JDs in {snap.JD_DIR}"


def test_no_orphan_golden_files():
    stems = {p.stem for p in _JDS}
    orphans = [g.name for g in snap.SNAP_DIR.glob("*.tsv") if g.stem not in stems]
    assert not orphans, f"golden files without a fixture JD: {orphans}"


@pytest.mark.parametrize("jd_path", _JDS, ids=lambda p: p.stem)
def test_keyphrases_match_golden(jd_path: Path):
    golden = snap.SNAP_DIR / (jd_path.stem + ".tsv")
    assert golden.exists(), (
        f"missing golden file {golden.name} — run: python3 -m tests.regen_snapshots"
    )
    got = snap.snapshot(jd_path.read_text())
    assert got == golden.read_text(), (
        f"extract_keyphrases output changed for {jd_path.name}. If intended, "
        "run `python3 -m tests.regen_snapshots` and review the .tsv diff."
    )
