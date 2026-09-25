#!/usr/bin/env python3
"""append_handoff_log.py -- deterministically append one Log line to
SESSION_HANDOFF.md for an automated resume-gen run, instead of letting the
headless agent hand-edit that file itself.

Why this exists: CLAUDE.md's hygiene rule ("every agent that touches this repo
must update SESSION_HANDOFF.md") used to be followed literally by the headless
tailor/cover-letter agent too. That's a read-the-whole-file, rewrite-the-whole-
file edit -- fine for one agent at a time, but with concurrent web-UI runs
enabled (RESUME_WEB_CONCURRENCY > 1) two agents doing that at once is a classic
lost-update race: whichever writes second overwrites the first's entry with a
copy of the file that never saw it.

This script is deterministic and takes a real OS file lock, so concurrent
invocations queue instead of racing: each one blocks for the lock, re-reads
the CURRENT file (not a stale copy from before it waited), appends its line,
and atomically replaces the file. resume-gen's TASK now tells the agent not to
touch SESSION_HANDOFF.md itself for these automated runs -- this script is the
only writer for that Log line.

Best-effort by contract, like session_cost.py: any failure prints a note to
stderr and exits 0 so it can never fail the surrounding resume-gen run.
"""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import json
import os
import re
import sys
from pathlib import Path

_PAGE_RE = re.compile(r"\\xdef\\lastpage@lastpage\{(\d+)\}")
_COV_RE = re.compile(r"\*\*(\d+)%\*\*")
_LOG_HEADING_RE = re.compile(r"^## Log\s*\n", re.M)


def _page_count(out_dir: Path) -> int | None:
    aux = out_dir / "resume.aux"
    if not aux.is_file():
        return None
    m = _PAGE_RE.search(aux.read_text(encoding="utf-8", errors="replace"))
    return int(m.group(1)) if m else None


def _coverage_pct(out_dir: Path) -> int | None:
    md = out_dir / "coverage.md"
    if not md.is_file():
        return None
    m = _COV_RE.search(md.read_text(encoding="utf-8", errors="replace"))
    return int(m.group(1)) if m else None


def _cost_and_tier(out_dir: Path) -> tuple[float | None, str | None]:
    fp = out_dir / "cost.json"
    if not fp.is_file():
        return None, None
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None, None
    cost = data.get("cost_usd")
    models = list((data.get("models") or {}).keys())
    tier = "opus" if any("opus" in m for m in models) \
        else ("sonnet" if any("sonnet" in m for m in models) else None)
    return cost, tier


def _build_line(slug: str, out_dir: Path, kind: str, exit_code: int) -> str:
    today = dt.date.today().isoformat()
    pages = _page_count(out_dir)
    cov = _coverage_pct(out_dir)
    cost, tier = _cost_and_tier(out_dir)

    bits = []
    if exit_code != 0:
        bits.append(f"exit {exit_code}")
    elif pages is not None:
        bits.append(f"{pages} page(s)" + ("" if pages == 1 else " — overflow cap hit"))
    if cov is not None:
        bits.append(f"{cov}% coverage")
    if cost is not None:
        bits.append(f"~${cost:.2f}")
    if tier:
        bits.append(tier)
    detail = ", ".join(bits) if bits else "no metrics captured"

    return (f"- **{today}** — Automated {kind} run: `output/{slug}/` — {detail} "
            f"*(logged automatically by scripts/append_handoff_log.py)*\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="append-handoff-log")
    ap.add_argument("--slug", required=True, help="the run's output/<slug> folder name")
    ap.add_argument("--kind", default="tailor", choices=("tailor", "cover-letter"))
    ap.add_argument("--exit-code", type=int, default=0)
    ap.add_argument("--handoff", default="SESSION_HANDOFF.md",
                     help="path to the handoff file (relative to --cwd)")
    ap.add_argument("--cwd", default=os.getcwd())
    args = ap.parse_args(argv)

    root = Path(args.cwd)
    out_dir = root / "output" / args.slug
    handoff = root / args.handoff
    lock_path = root / ".session_handoff.lock"

    try:
        if not handoff.is_file():
            print(f"  resume-gen │ (no {handoff.name} found; skipping handoff log)",
                  file=sys.stderr)
            return 0

        line = _build_line(args.slug, out_dir, args.kind, args.exit_code)

        # A real OS lock, not a convention: concurrent invocations block here
        # and each sees the CURRENT file when it wakes up, not a stale read
        # from before it waited -- that's what makes this safe with more than
        # one resume-gen run finishing at the same moment.
        lock_path.touch(exist_ok=True)
        with open(lock_path, "r+") as lock_fh:
            fcntl.flock(lock_fh, fcntl.LOCK_EX)
            try:
                text = handoff.read_text(encoding="utf-8")
                if f"output/{args.slug}/" in text:
                    # Already logged (e.g. a retried/duplicate call) -- an
                    # idempotency check, not a race check; the lock above is
                    # what prevents the race itself.
                    print(f"  resume-gen │ (handoff already has an entry for "
                          f"{args.slug}; not duplicating)", file=sys.stderr)
                    return 0
                m = _LOG_HEADING_RE.search(text)
                if not m:
                    print(f"  resume-gen │ ({handoff.name} has no '## Log' heading; "
                          "skipping handoff log)", file=sys.stderr)
                    return 0
                insert_at = m.end()
                # Skip a single following blank line so the new entry sits
                # directly under the heading, "newest on top", matching the
                # file's documented convention.
                if text[insert_at:insert_at + 1] == "\n":
                    insert_at += 1
                new_text = text[:insert_at] + line + text[insert_at:]

                # Write-to-temp + atomic rename: no reader (including another
                # agent's Read tool call mid-run) can ever observe a partially
                # written file.
                tmp = handoff.with_suffix(handoff.suffix + ".tmp")
                tmp.write_text(new_text, encoding="utf-8")
                os.replace(tmp, handoff)
                print(f"  resume-gen │ 📋 logged this run to {handoff.name}",
                      file=sys.stderr)
                return 0
            finally:
                fcntl.flock(lock_fh, fcntl.LOCK_UN)
    except Exception as e:  # never fail the surrounding run
        print(f"  resume-gen │ (handoff logging skipped: {e})", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
