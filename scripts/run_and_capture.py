#!/usr/bin/env python3
"""run_and_capture.py -- run a command, mirror its stdout live, and pull the
per-run session id + chosen output slug straight out of its own JSON stream.

Why this exists: with more than one tailor run in flight at once, "the newest
file in ~/.claude/projects/<cwd>/" and "the newest output/*/ folder" are both
races -- two concurrent `claude -p --output-format stream-json` sessions can
finish close enough together that either heuristic picks the wrong one. This
process only ever looks at the stdout of the ONE child it launched, so what it
extracts is correct for THIS run regardless of what else is running alongside
it.

Extracts, best-effort (either can end up empty; callers treat that as "skip"):
- session_id: the `sessionId` field Claude Code stamps on every stream-json
  event.
- slug: the tailor task's output/<slug>/ folder name, read off the first tool
  call (Read/Write/Edit file_path, or a Bash command) that mentions one --
  the agent picks its slug in step 2 of TASK (see resume-gen) and every
  artifact after that lives under it.

Writes {"session_id": ..., "slug": ...} as JSON to --info-file (whatever was
found; missing keys are omitted). Exits with the child's exit code. Never
raises past a parse hiccup on one line -- a bad line just means that line
didn't teach us anything.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys

_SLUG_RE = re.compile(r"\boutput/([A-Za-z0-9._-]+)/")


def _hunt_slug(obj) -> str | None:
    """Depth-first search for the first output/<slug>/ mention in any string
    value of a decoded stream-json event (tool_use inputs, bash commands,
    assistant text all show up as nested strings here)."""
    if isinstance(obj, str):
        m = _SLUG_RE.search(obj)
        return m.group(1) if m else None
    if isinstance(obj, dict):
        for v in obj.values():
            found = _hunt_slug(v)
            if found:
                return found
        return None
    if isinstance(obj, list):
        for v in obj:
            found = _hunt_slug(v)
            if found:
                return found
        return None
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="run-and-capture")
    ap.add_argument("--info-file", required=True,
                     help="path to write the captured {session_id, slug} JSON to")
    ap.add_argument("cmd", nargs=argparse.REMAINDER,
                     help="the command to run, e.g. -- claude -p ... --output-format stream-json")
    args = ap.parse_args(argv)
    cmd = args.cmd[1:] if args.cmd[:1] == ["--"] else args.cmd
    if not cmd:
        print("run_and_capture: no command given", file=sys.stderr)
        return 2

    session_id = None
    slug = None
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, bufsize=1)
    for line in proc.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        text = line.strip()
        if not text.startswith("{"):
            continue
        try:
            ev = json.loads(text)
        except (ValueError, TypeError):
            continue
        if session_id is None:
            sid = ev.get("sessionId")
            if isinstance(sid, str) and sid:
                session_id = sid
        if slug is None:
            found = _hunt_slug(ev)
            if found:
                slug = found
    code = proc.wait()

    info = {}
    if session_id:
        info["session_id"] = session_id
    if slug:
        info["slug"] = slug
    try:
        with open(args.info_file, "w", encoding="utf-8") as f:
            json.dump(info, f)
    except OSError as e:
        print(f"run_and_capture: couldn't write --info-file: {e}", file=sys.stderr)

    return code


if __name__ == "__main__":
    sys.exit(main())
