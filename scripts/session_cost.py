#!/usr/bin/env python3
"""Record what a headless `claude -p` run cost, into output/<slug>/cost.json.

The tailor/cover stages are a headless Claude Code session, so token spend isn't
visible to the pipeline itself — Claude Code writes it to a per-session JSONL
transcript under ~/.claude/projects/<mangled-cwd>/. This reads the transcript for
the run that just finished (newest, or newest modified after --since), sums the
per-message `usage`, prices it, and writes a small cost.json next to the resume.

Best-effort by contract: any failure prints a note to stderr and exits 0 so it
can never fail the surrounding run. Costs are an estimate (transcript usage +
public list prices), clearly labelled as such.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

# Per-million-token list prices ($). Cache write = 1.25× input (5-min TTL),
# cache read = 0.1× input. Keyed by a substring of the model id; first match
# wins, so order most-specific first. Unknown models fall back to Sonnet 5.
_PRICING = [
    ("claude-opus-4-8", 5.0, 25.0),
    ("claude-opus-4-7", 5.0, 25.0),
    ("claude-opus-4-6", 5.0, 25.0),
    ("claude-haiku-4-5", 1.0, 5.0),
    ("claude-sonnet-5", 3.0, 15.0),   # standard; intro override applied below
    ("claude-sonnet-4", 3.0, 15.0),
]
# Sonnet 5 introductory pricing runs through this date (Claude API skill).
_SONNET5_INTRO_UNTIL = dt.date(2026, 8, 31)
_SONNET5_INTRO = (2.0, 10.0)


def _rates(model: str, today: dt.date) -> tuple[float, float, str]:
    """(input $/M, output $/M, note) for a model id."""
    for key, in_m, out_m in _PRICING:
        if key in model:
            if key == "claude-sonnet-5" and today <= _SONNET5_INTRO_UNTIL:
                return (*_SONNET5_INTRO, "sonnet-5 introductory pricing")
            return in_m, out_m, "list pricing"
    return (*_SONNET5_INTRO, "unknown model — priced as sonnet-5 intro") \
        if today <= _SONNET5_INTRO_UNTIL else (3.0, 15.0, "unknown model — priced as sonnet-5")


def _project_dir(cwd: str) -> Path:
    """Claude Code mangles the absolute cwd (every non-alnum char → '-') to name
    the per-project transcript directory."""
    mangled = re.sub(r"[^a-zA-Z0-9]", "-", os.path.abspath(cwd))
    return Path.home() / ".claude" / "projects" / mangled


def _pick_transcript(project_dir: Path, since: float | None) -> Path | None:
    if not project_dir.is_dir():
        return None
    files = [p for p in project_dir.glob("*.jsonl")
             if since is None or p.stat().st_mtime >= since]
    return max(files, key=lambda p: p.stat().st_mtime) if files else None


def _sum_usage(transcript: Path) -> tuple[dict, int, str | None]:
    """Per-model token buckets + assistant-turn count + session id."""
    models: dict[str, dict] = {}
    turns = 0
    session_id = None
    with transcript.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            session_id = session_id or rec.get("sessionId")
            if rec.get("type") != "assistant":
                continue
            msg = rec.get("message", {})
            u = msg.get("usage")
            if not u:
                continue
            turns += 1
            model = msg.get("model") or "unknown"
            b = models.setdefault(model, {"input_tokens": 0, "output_tokens": 0,
                                          "cache_read_input_tokens": 0,
                                          "cache_creation_input_tokens": 0})
            b["input_tokens"] += u.get("input_tokens", 0)
            b["output_tokens"] += u.get("output_tokens", 0)
            b["cache_read_input_tokens"] += u.get("cache_read_input_tokens", 0)
            b["cache_creation_input_tokens"] += u.get("cache_creation_input_tokens", 0)
    return models, turns, session_id


def _cost(models: dict, today: dt.date) -> tuple[float, list[str]]:
    total = 0.0
    notes = []
    for model, b in models.items():
        in_m, out_m, note = _rates(model, today)
        c = (b["input_tokens"] * in_m
             + b["cache_creation_input_tokens"] * in_m * 1.25
             + b["cache_read_input_tokens"] * in_m * 0.10
             + b["output_tokens"] * out_m) / 1e6
        total += c
        notes.append(f"{model}: {note}")
    return total, notes


def _coverage_pct(out_dir: Path) -> int | None:
    """Pull the leading JD-coverage % out of coverage.md if the render wrote one,
    so each run's cost record also carries its final coverage (ties #2 to #3)."""
    md = out_dir / "coverage.md"
    if not md.is_file():
        return None
    m = re.search(r"\*\*(\d+)%\*\*", md.read_text(encoding="utf-8", errors="replace"))
    return int(m.group(1)) if m else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="session-cost")
    ap.add_argument("--out", required=True, help="resume output folder to write cost.json into")
    ap.add_argument("--since", type=float, default=None,
                    help="only accept a transcript modified at/after this epoch time")
    ap.add_argument("--project-dir", default=None, help="override the transcripts dir")
    ap.add_argument("--cwd", default=os.getcwd(), help="cwd used to locate the transcripts dir")
    args = ap.parse_args(argv)

    out_dir = Path(args.out)
    try:
        project_dir = Path(args.project_dir) if args.project_dir else _project_dir(args.cwd)
        transcript = _pick_transcript(project_dir, args.since)
        if transcript is None:
            print(f"  resume-gen │ (no session transcript found in {project_dir}; skipping cost.json)",
                  file=sys.stderr)
            return 0
        models, turns, session_id = _sum_usage(transcript)
        if not models:
            print("  resume-gen │ (transcript had no usage yet; skipping cost.json)", file=sys.stderr)
            return 0
        today = dt.date.today()
        cost, notes = _cost(models, today)
        totals = {k: sum(b[k] for b in models.values())
                  for k in ("input_tokens", "output_tokens",
                            "cache_read_input_tokens", "cache_creation_input_tokens")}
        totals["total_tokens"] = sum(totals.values())
        record = {
            "session_id": session_id,
            "transcript": transcript.name,
            "generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "assistant_turns": turns,
            "models": models,
            "totals": totals,
            "cost_usd": round(cost, 4),
            "jd_coverage_pct": _coverage_pct(out_dir),
            "pricing_note": "estimate from transcript usage + public list prices; "
                            + "; ".join(notes),
        }
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "cost.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print(f"  resume-gen │ 💰 ~${cost:.2f}  ({totals['total_tokens']//1000}k tokens, "
              f"{turns} turns) → {out_dir}/cost.json", file=sys.stderr)
        return 0
    except Exception as e:  # never fail the surrounding run
        print(f"  resume-gen │ (cost logging skipped: {e})", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
