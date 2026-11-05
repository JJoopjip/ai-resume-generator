"""Screenshot -> job-description text (scripts/jd_from_image.py).

`claude` is faked; these pin the plumbing (input validation, scratch-dir copy,
sentinel/empty handling), not the model's OCR.
"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import jd_from_image as jfi  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 16


def _fake_run(stdout="", returncode=0, seen=None):
    def run(cmd, **kw):
        if seen is not None:
            seen.update(cmd=cmd, cwd=kw["cwd"], files=sorted(p.name for p in Path(kw["cwd"]).iterdir()))
        return subprocess.CompletedProcess(cmd, returncode, stdout, "boom")
    return run


@pytest.fixture
def shots(tmp_path):
    out = []
    for n in ("a.png", "b.JPG"):
        (tmp_path / n).write_bytes(PNG)
        out.append(tmp_path / n)
    return out


def test_returns_text_and_reads_only_scratch_copies(monkeypatch, shots):
    seen = {}
    monkeypatch.setattr(jfi.subprocess, "run", _fake_run("  Acme\n- Role  \n", seen=seen))
    assert jfi.transcribe(shots) == "Acme\n- Role"
    assert seen["files"] == ["page1.png", "page2.jpg"]            # ordered, renamed copies
    assert seen["cwd"] not in {str(p.parent) for p in shots}      # not the user's folder
    assert seen["cmd"][seen["cmd"].index("--allowedTools") + 1] == "Read"  # Read only


@pytest.mark.parametrize("stdout", ["", "NO_JOB_POSTING"])
def test_no_posting_is_exit_1(monkeypatch, shots, stdout):
    monkeypatch.setattr(jfi.subprocess, "run", _fake_run(stdout))
    with pytest.raises(jfi.TranscribeError) as e:
        jfi.transcribe(shots)
    assert e.value.code == 1


def test_claude_failure_is_exit_3(monkeypatch, shots):
    monkeypatch.setattr(jfi.subprocess, "run", _fake_run("", returncode=2))
    with pytest.raises(jfi.TranscribeError) as e:
        jfi.transcribe(shots)
    assert e.value.code == 3


def test_rejects_bad_input(tmp_path):
    txt = tmp_path / "jd.txt"
    txt.write_text("hi")
    for bad in ([], [txt], [tmp_path / "missing.png"], [tmp_path / "x.png"] * (jfi.MAX_IMAGES + 1)):
        with pytest.raises(jfi.TranscribeError) as e:
            jfi.transcribe(bad)
        assert e.value.code == 2
