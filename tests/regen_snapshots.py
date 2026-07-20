"""Regenerate the keyphrase golden files under tests/fixtures/keyphrases/.

Run after an intentional change to the JD keyphrase extractor:

    python3 -m tests.regen_snapshots

then review the git diff of the .tsv files — that diff IS the review artifact:
it shows exactly how the change moves the term list on real postings, which is
the whole point of snapshotting (scorer changes used to shift every score
silently).
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import coverage as cov  # noqa: E402

JD_DIR = REPO_ROOT / "tests" / "fixtures" / "jds"
SNAP_DIR = REPO_ROOT / "tests" / "fixtures" / "keyphrases"


def snapshot(jd_text: str) -> str:
    """One term per line, in rank order: display text, TAB, matched stems.
    Both columns matter — a stemmer change can move `stems` while `display`
    stays put, and vice versa."""
    lines = [
        f"{p.display}\t{' '.join(p.stems)}"
        for p in cov.extract_keyphrases(jd_text, limit=25)
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    jds = sorted(JD_DIR.glob("*.txt"))
    if not jds:
        sys.exit(f"no fixture JDs found in {JD_DIR}")
    for jd in jds:
        out = SNAP_DIR / (jd.stem + ".tsv")
        out.write_text(snapshot(jd.read_text()))
        print(f"wrote {out.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
