"""Slug detection must pick the folder the run CREATED, not the first
output/ path it mentions (a re-run of a saved JD reads output/<old>/ first)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_and_capture  # noqa: E402


def _tool(name, **inp):
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": name, "input": inp}]}}


def _run(tmp_path, events):
    stream = tmp_path / "stream.jsonl"
    stream.write_text("".join(json.dumps(e) + "\n" for e in events))
    info = tmp_path / "info.json"
    rc = run_and_capture.main(["--info-file", str(info), "--",
                               "cat", str(stream)])
    return rc, json.loads(info.read_text())


def test_prefers_mkdir_folder_over_jd_source_folder(tmp_path, capsys):
    events = [
        _tool("Read", file_path="/repo/output/general-pm-2026-10-09/job_description.txt"),
        _tool("Bash", command="mkdir output/general-pm-2026-10-13"),
        _tool("Write", file_path="output/general-pm-2026-10-13/instance.yaml"),
    ]
    rc, info = _run(tmp_path, events)
    assert rc == 0
    assert info["slug"] == "general-pm-2026-10-13"


def test_falls_back_to_first_mention_without_mkdir(tmp_path, capsys):
    events = [_tool("Write", file_path="output/acme-analyst-2026-10-13/instance.yaml")]
    _rc, info = _run(tmp_path, events)
    assert info["slug"] == "acme-analyst-2026-10-13"


def test_mkdir_with_flags_and_trailing_slash():
    ev = _tool("Bash", command="cd /repo && mkdir -p output/x-y-2026-10-13/ && ls")
    assert run_and_capture._hunt_mkdir_slug(ev) == "x-y-2026-10-13"
