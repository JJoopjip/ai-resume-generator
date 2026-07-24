#!/usr/bin/env python3
"""Content-gap digest: which JD terms recur across postings that your bank has
nothing on.

Every tailored run already writes a `coverage.md` that splits missing JD terms
into a *selection gap* (in `master.yaml`, just not picked — fixable now) and a
*content gap* (nowhere in the bank). The content gaps are the actionable signal
for growing the bank, but each run's list dies in its own folder, so a term one
posting wanted looks like a one-off even when five postings wanted it.

This walks every `output/<slug>/` folder that has both a `job_description.txt`
and an `instance.yaml`, **recomputes** coverage against the *current*
`master.yaml` (never parses the stale `coverage.md` — the bank evolves, so an
old report overstates today's gaps), and aggregates the content-gap terms across
runs. The result, `output/gap_digest.md`, ranks terms by how many postings asked
for them.

It is a to-write list, not a to-fake list: a recurring term is worth writing up
*only if it's truly part of your experience*. The scorer is a keyword screen;
never invent content to move it. Pure stdlib + PyYAML, runs on the host (no
Docker) — the same deterministic coverage code the renderer uses.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import coverage as coverage_mod  # noqa: E402
import validate as validate_mod  # noqa: E402


class GapTerm:
    """One aggregated content-gap term. Keyed by its stems (so 'analytics' and
    'analytic' collapse), but shows the display form postings phrased it as."""

    __slots__ = ("stems", "_displays", "slugs", "occurrences")

    def __init__(self, stems: tuple[str, ...]):
        self.stems = stems
        self._displays: Counter[str] = Counter()
        self.slugs: list[str] = []
        self.occurrences = 0   # total keyphrase hits across all runs

    def add(self, display: str, slug: str, count: int) -> None:
        self._displays[display] += 1
        self.occurrences += count
        if slug not in self.slugs:
            self.slugs.append(slug)

    @property
    def display(self) -> str:
        # Most common phrasing wins; alphabetical tiebreak keeps it deterministic.
        return min(self._displays.items(), key=lambda kv: (-kv[1], kv[0]))[0]

    @property
    def postings(self) -> int:
        return len(self.slugs)


def iter_run_dirs(output_root: Path):
    """Every output/<slug>/ folder that is a complete run: has both a job
    description and a tailored instance. Sorted by slug for stable output."""
    if not output_root.is_dir():
        return
    for d in sorted(output_root.iterdir()):
        if d.is_dir() and (d / "job_description.txt").is_file() and (d / "instance.yaml").is_file():
            yield d


def _phrase_count(stems: tuple[str, ...], jd_stems: list[str]) -> int:
    """How many times this keyphrase's stem sequence occurs in the JD's ordered
    stem stream — a unigram's raw frequency, or a bigram's adjacent-pair count.
    (Adjacency here ignores clause boundaries, but extract_keyphrases already
    proved the phrase is a real bigram, so this only affects the tally.)"""
    n = len(stems)
    if n == 1:
        return jd_stems.count(stems[0])
    return sum(1 for i in range(len(jd_stems) - n + 1)
               if tuple(jd_stems[i:i + n]) == stems)


def content_gaps_for_run(jd_text: str, instance: dict, master: dict):
    """The JD keyphrases this run's bank can't cover at all — neither on the
    rendered resume nor anywhere in master.yaml. Same classification the live
    coverage report uses; returns (keyphrase, mention_count) so aggregation
    keeps both the stems and how insistently this posting asked."""
    resume_bag = coverage_mod.token_set(coverage_mod.instance_text(instance))
    master_bag = coverage_mod.token_set(coverage_mod.master_text(master))
    jd_stems = coverage_mod.tokens(jd_text)
    return [
        (kp, _phrase_count(kp.stems, jd_stems))
        for kp in coverage_mod.extract_keyphrases(jd_text)
        if not kp.covered_by(resume_bag) and not kp.covered_by(master_bag)
    ]


def aggregate(runs: list[tuple[str, list]]) -> list[GapTerm]:
    """runs: [(slug, [(Keyphrase, count), ...]), ...] -> gap terms ranked by how many
    postings wanted them (desc), then by total mentions (desc) so a term the
    postings kept returning to outranks one they named in passing, then by
    display for a stable tie."""
    terms: dict[tuple[str, ...], GapTerm] = {}
    for slug, gaps in runs:
        for kp, count in gaps:
            term = terms.setdefault(kp.stems, GapTerm(kp.stems))
            term.add(kp.display, slug, count)
    return sorted(terms.values(), key=lambda t: (-t.postings, -t.occurrences, t.display))


def render_markdown(ranked: list[GapTerm], n_runs: int, min_postings: int = 2) -> str:
    recurring = [t for t in ranked if t.postings >= min_postings]
    lines = [
        "# Content-gap digest",
        "",
        f"Aggregated across **{n_runs}** tailored run(s). A *content gap* is a JD "
        "key term your `master.yaml` has nothing on — neither on the rendered "
        "resume nor anywhere in the bank.",
        "",
        "> This is a **to-write** list, not a to-fake list. A term recurring here "
        "means several postings asked for it; add it to `master.yaml` **only if "
        "it's truly part of your experience**. The score is a keyword screen — "
        "never invent content to move it.",
        "",
    ]

    if not ranked:
        lines += ["_No content gaps found — every posting's key terms are already "
                  "somewhere in the bank._", ""]
        return "\n".join(lines)

    if recurring:
        lines += [
            f"## Recurring ({len(recurring)}) — wanted by ≥{min_postings} postings",
            "",
            "These come up again and again and the bank can't speak to them. If "
            "they're genuinely yours, they're the highest-leverage things to write "
            "up next.",
            "",
            "| term | postings | mentions | asked by |",
            "|------|----------|----------|----------|",
        ]
        for t in recurring:
            lines.append(
                f"| {t.display} | {t.postings} | {t.occurrences} | {', '.join(t.slugs)} |")
        lines.append("")

    one_offs = [t for t in ranked if t.postings < min_postings]
    if one_offs:
        lines += [
            f"## Seen once ({len(one_offs)})",
            "",
            "One posting each — lower priority, but listed so nothing is lost.",
            "",
        ]
        lines += [f"- {t.display} — {t.slugs[0]}" for t in one_offs]
        lines.append("")

    return "\n".join(lines)


def build_digest(output_root: Path, master: dict, min_postings: int = 2):
    """Walk runs under output_root, recompute content gaps against the current
    master, and return (markdown, ranked_terms, n_runs). Runs that fail to load
    are skipped with a stderr note rather than aborting the whole digest."""
    runs: list[tuple[str, list]] = []
    for d in iter_run_dirs(output_root):
        try:
            instance = validate_mod.load_yaml(d / "instance.yaml")
            jd_text = (d / "job_description.txt").read_text(encoding="utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001 — one bad folder shouldn't kill the digest
            print(f"gap-digest: skipping {d.name}: {exc}", file=sys.stderr)
            continue
        runs.append((d.name, content_gaps_for_run(jd_text, instance, master)))
    ranked = aggregate(runs)
    return render_markdown(ranked, len(runs), min_postings), ranked, len(runs)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="resume-gen gaps",
        description="Aggregate recurring content gaps across all tailored runs.")
    ap.add_argument("--output", default="output", metavar="DIR",
                    help="folder holding the per-run output/<slug>/ dirs (default: ./output)")
    ap.add_argument("--master", default="master.yaml", metavar="FILE",
                    help="fact bank to score against (default: ./master.yaml)")
    ap.add_argument("--min-postings", type=int, default=2, metavar="N",
                    help="terms wanted by ≥N postings are the 'recurring' list (default: 2)")
    args = ap.parse_args(argv)

    master_path = Path(args.master)
    if not master_path.is_file():
        print(f"resume-gen gaps: master '{args.master}' not found", file=sys.stderr)
        return 4
    output_root = Path(args.output)

    master = validate_mod.load_yaml(master_path)
    md, _ranked, n_runs = build_digest(output_root, master, args.min_postings)
    if n_runs == 0:
        print(f"resume-gen gaps: no complete runs under '{args.output}/' "
              "(each needs job_description.txt + instance.yaml)", file=sys.stderr)
        return 1

    out_path = output_root / "gap_digest.md"
    out_path.write_text(md, encoding="utf-8")
    print(f"gap-digest: {n_runs} run(s) → {out_path}", file=sys.stderr)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
