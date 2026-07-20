#!/usr/bin/env python3
"""A/B eval of the tailor stage: same JD, two model/effort settings.

The pipeline can prove a resume is truthful (validate.py) and score its keyword
fit (coverage.py), but nothing measures whether a pricier model actually
*selects better* — the default just moved Sonnet/medium -> Opus/high on that
belief. This harness turns the question into data:

    ./resume-gen eval jd.txt                # sonnet-medium vs opus-high
    ./resume-gen eval jd.txt --judge        # + blind LLM preference read
    ./resume-gen eval jd.txt --a "--model claude-sonnet-5 --effort low" \
                             --b "--model claude-sonnet-5 --effort high"

Each arm is a full ./resume-gen run (resume only, no cover letter) into its own
output/<slug>-<label>/ folder via RESUME_GEN_SLUG_SUFFIX. Afterwards each
instance is re-rendered deterministically to read coverage/pages/fit from the
render JSON, cost.json supplies spend, and everything lands side by side in
output/eval-<jd>-<date>/eval.md.

--judge runs a separate headless session (prompts/eval_judge.md) over the two
instances presented in RANDOM order as candidate_1/candidate_2, so the judge
never sees which model produced which. Advisory only.

NOTE: each arm is a real Claude run and costs real money (roughly the cost of
two tailored resumes, plus the judge if enabled).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Same pre-authorized perms the normal launcher uses (resume-gen CLAUDE_FLAGS).
_PERMS = "--permission-mode acceptEdits --allowedTools Bash Read Edit Write"
_DEFAULT_A = "--model claude-sonnet-5 --effort medium"
_DEFAULT_B = "--model claude-opus-4-8 --effort high"


def derive_label(flags: str, fallback: str) -> str:
    """'--model claude-sonnet-5 --effort medium' -> 'sonnet-5-medium'. The label
    doubles as the output-slug suffix, so keep it short and hyphen-safe."""
    model = re.search(r"--model\s+(\S+)", flags)
    effort = re.search(r"--effort\s+(\S+)", flags)
    parts = []
    if model:
        parts.append(model.group(1).removeprefix("claude-"))
    if effort:
        parts.append(effort.group(1))
    label = "-".join(parts) or fallback
    return re.sub(r"[^a-zA-Z0-9.-]", "-", label)


class Arm:
    def __init__(self, label: str, flags: str):
        self.label = label
        self.flags = flags
        self.run_dir: Path | None = None
        self.render: dict | None = None   # deterministic render JSON
        self.cost: dict | None = None     # cost.json contents
        self.seconds: float | None = None
        self.error: str | None = None


def _newest_run_dir(label: str, started: float) -> Path | None:
    """The tailor session picks its own slug; we only pinned its suffix. Find
    the folder it created: newest output/*-<label>/ modified since the arm
    started, that actually contains an instance.yaml."""
    candidates = [
        d for d in Path("output").glob(f"*-{label}")
        if d.is_dir() and d.stat().st_mtime >= started and (d / "instance.yaml").is_file()
    ]
    return max(candidates, key=lambda d: d.stat().st_mtime) if candidates else None


def run_arm(arm: Arm, jd: Path) -> None:
    print(f"\n  eval │ ━━ arm '{arm.label}'  ({arm.flags}) ━━", file=sys.stderr)
    env = os.environ.copy()
    env["RESUME_GEN_CLAUDE_FLAGS"] = f"{arm.flags} {_PERMS}"
    env["RESUME_GEN_SLUG_SUFFIX"] = f"-{arm.label}"
    env["RESUME_GEN_COVER"] = "0"     # resume only; letters would muddy cost
    started = time.time()
    proc = subprocess.run(["./resume-gen", str(jd)], env=env)
    arm.seconds = round(time.time() - started, 1)
    arm.run_dir = _newest_run_dir(arm.label, started)
    if arm.run_dir is None:
        arm.error = (f"tailor run exited {proc.returncode} and no "
                     f"output/*-{arm.label}/instance.yaml appeared")
        return
    if proc.returncode != 0:
        arm.error = f"tailor run exited {proc.returncode} (metrics below are from its last state)"

    # Deterministic re-render of the final instance: authoritative
    # coverage/page/fit numbers, independent of what the session reported.
    render = subprocess.run(
        ["./resume-gen", "render", "--instance", str(arm.run_dir / "instance.yaml")],
        capture_output=True, text=True,
    )
    try:
        arm.render = json.loads(render.stdout)
    except json.JSONDecodeError:
        arm.error = arm.error or f"could not parse render JSON (exit {render.returncode})"
    else:
        if arm.render.get("errors"):
            first = arm.render["errors"][0].get("message", "?")
            arm.error = arm.error or (
                f"final instance does not render clean (exit {render.returncode}): {first}")

    cost_path = arm.run_dir / "cost.json"
    if cost_path.is_file():
        try:
            arm.cost = json.loads(cost_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def _metric_rows(arms: list[Arm]) -> list[tuple[str, list[str]]]:
    """(metric name, one value per arm) — pure so it's unit-testable."""
    def per_arm(fn) -> list[str]:
        vals = []
        for a in arms:
            try:
                v = fn(a)
                vals.append("n/a" if v is None else str(v))
            except (KeyError, TypeError, AttributeError):
                vals.append("n/a")
        return vals

    def cov(a: Arm) -> dict:
        return (a.render or {})["coverage"]

    return [
        ("model / effort", per_arm(lambda a: a.flags)),
        ("JD coverage", per_arm(lambda a: f"{round(cov(a)['score'] * 100)}% "
                                          f"({cov(a)['terms_covered']}/{cov(a)['terms_total']})")),
        ("selection gaps (in bank, unpicked)", per_arm(lambda a: len(cov(a)["selection_gap"]))),
        ("content gaps (not in bank)", per_arm(lambda a: len(cov(a)["content_gap"]))),
        ("pages", per_arm(lambda a: (a.render or {})["page_count"])),
        ("lines of room left", per_arm(lambda a: (a.render or {})["fit"]["lines_free"])),
        ("bullets on page", per_arm(lambda a: f"{cov(a)['depth']['bullets_selected']}"
                                              f"/{cov(a)['depth']['bullets_available']}")),
        ("roles on page", per_arm(lambda a: f"{cov(a)['depth']['roles_selected']}"
                                            f"/{cov(a)['depth']['roles_available']}")),
        ("deterministic profile suggestion", per_arm(lambda a: cov(a)["profile"]["suggested"])),
        ("est. cost (USD)", per_arm(lambda a: f"{a.cost['cost_usd']:.2f}" if a.cost else None)),
        ("tokens", per_arm(lambda a: f"{a.cost['totals']['total_tokens'] // 1000}k" if a.cost else None)),
        ("assistant turns", per_arm(lambda a: a.cost["assistant_turns"] if a.cost else None)),
        ("wall time", per_arm(lambda a: f"{int(a.seconds // 60)}m{int(a.seconds % 60):02d}s"
                                        if a.seconds is not None else None)),
        ("output folder", per_arm(lambda a: a.run_dir)),
    ]


def render_report(arms: list[Arm], jd: Path, judge_note: str | None) -> str:
    header = " | ".join(a.label for a in arms)
    lines = [
        f"# Eval — {jd.name} — {dt.date.today().isoformat()}",
        "",
        "Same posting, same fact bank, two tailor settings. Coverage/page numbers",
        "come from a deterministic re-render of each final instance; cost from the",
        "session transcript. An ATS-style screen, **not** a quality verdict — for",
        "a preference read, see judge.md (if generated).",
        "",
        f"| metric | {header} |",
        f"|--------|{'--------|' * len(arms)}",
    ]
    for name, vals in _metric_rows(arms):
        lines.append(f"| {name} | " + " | ".join(vals) + " |")
    for a in arms:
        if a.error:
            lines += ["", f"> ⚠ arm **{a.label}**: {a.error}"]
    if judge_note:
        lines += ["", judge_note]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Blind judge (optional)
# ---------------------------------------------------------------------------
def run_judge(arms: list[Arm], jd: Path, eval_dir: Path) -> str:
    """Copy the two instances under neutral names in random order, then have a
    headless session apply prompts/eval_judge.md. Returns a note for eval.md
    that reveals the candidate->arm mapping (the judge never sees it)."""
    order = list(arms)
    random.shuffle(order)
    for i, arm in enumerate(order, start=1):
        shutil.copy(arm.run_dir / "instance.yaml", eval_dir / f"candidate_{i}.yaml")
    task = f"""Non-interactive eval-judge run. Working directory: {os.getcwd()}.
Follow prompts/eval_judge.md exactly as your specification.

Inputs:
- Job description: {jd}
- Candidate 1: {eval_dir}/candidate_1.yaml
- Candidate 2: {eval_dir}/candidate_2.yaml

Read all three, score both candidates against the rubric, and write your
judgment to {eval_dir}/judge.md. Do not ask questions. You are not told which
model produced which candidate — judge only what is on the page."""
    print("\n  eval │ ━━ blind judge ━━", file=sys.stderr)
    subprocess.run(["claude", "-p", task, "--model", "claude-opus-4-8", "--effort", "high",
                    "--permission-mode", "acceptEdits", "--allowedTools", "Read", "Write"])
    mapping = ", ".join(f"candidate {i} = **{arm.label}**" for i, arm in enumerate(order, 1))
    return (f"Blind judge ran over shuffled candidates — see `judge.md`. "
            f"Mapping (judge did not see this): {mapping}.")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="resume-gen eval",
        description="A/B the tailor stage on one JD and write a side-by-side eval.md.")
    ap.add_argument("jd", help="job-description file")
    ap.add_argument("--a", default=_DEFAULT_A, metavar="FLAGS",
                    help=f"claude flags for arm A (default: '{_DEFAULT_A}')")
    ap.add_argument("--b", default=_DEFAULT_B, metavar="FLAGS",
                    help=f"claude flags for arm B (default: '{_DEFAULT_B}')")
    ap.add_argument("--judge", action="store_true",
                    help="also run a blind LLM preference read (extra cost)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print what would run (arms, labels, folders) and exit")
    args = ap.parse_args(argv)

    jd = Path(args.jd)
    if not jd.is_file():
        print(f"resume-gen eval: '{args.jd}' is not a file", file=sys.stderr)
        return 4
    os.chdir(REPO_ROOT)
    jd = jd.resolve()

    arms = [Arm(derive_label(args.a, "a"), args.a), Arm(derive_label(args.b, "b"), args.b)]
    if arms[0].label == arms[1].label:
        arms[0].label += "-a"
        arms[1].label += "-b"

    eval_dir = Path("output") / f"eval-{jd.stem}-{dt.date.today().isoformat()}"
    if args.dry_run:
        for arm in arms:
            print(f"would run: RESUME_GEN_SLUG_SUFFIX=-{arm.label} "
                  f"RESUME_GEN_CLAUDE_FLAGS='{arm.flags} {_PERMS}' ./resume-gen {jd}")
        print(f"would write: {eval_dir}/eval.md" + (" + judge.md" if args.judge else ""))
        return 0

    for arm in arms:
        run_arm(arm, jd)

    # Create the eval dir only AFTER both arms: resume-gen's AUTO cost logging
    # targets the newest output/ dir, which must stay the arm's own folder.
    eval_dir.mkdir(parents=True, exist_ok=True)

    judge_note = None
    if args.judge:
        if all(a.run_dir for a in arms):
            judge_note = run_judge(arms, jd, eval_dir)
        else:
            judge_note = "> Judge skipped: at least one arm produced no instance."

    report = render_report(arms, jd, judge_note)
    (eval_dir / "eval.md").write_text(report, encoding="utf-8")
    print(f"\n  eval │ ✓ report → {eval_dir}/eval.md", file=sys.stderr)
    print(report)
    return 0 if all(a.error is None for a in arms) else 1


if __name__ == "__main__":
    sys.exit(main())
