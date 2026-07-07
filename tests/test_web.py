"""Tests for web/app.py — the local browser front end.

These exercise the three things that can break *without* running the real
(Docker + Claude) pipeline: (1) the stream-json → human-phase narrator, (2) the
download path-traversal guard, and (3) HTTP routing / input validation. The
actual résumé generation is intentionally NOT invoked here — it's slow, needs
Docker + a Claude session, and is covered by the manual end-to-end runs in
TODO.md. We drive the server in-process on an ephemeral port instead.
"""

import json
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "web"))

import app as web  # noqa: E402


# ---- Narrator: stream-json events → human phase lines ------------------------

def _assistant_tool_use(name, **inp):
    """Wrap a tool_use block in the assistant-event envelope the narrator sees."""
    return json.dumps({
        "type": "assistant",
        "message": {"content": [{"type": "tool_use", "name": name, "input": inp}]},
    })


def test_narrator_passes_through_non_json_banner():
    narrate = web.make_narrator()
    assert narrate("plain launcher banner\n") == "plain launcher banner"


def test_narrator_blank_line_is_silent():
    narrate = web.make_narrator()
    assert narrate("   \n") is None


def test_narrator_reads_master_and_jd():
    narrate = web.make_narrator()
    assert "career history" in narrate(
        _assistant_tool_use("Read", file_path="/x/master.yaml"))
    assert "job description" in narrate(
        _assistant_tool_use("Read", file_path="/x/job_description.txt"))


def test_narrator_writing_instance():
    narrate = web.make_narrator()
    assert "tailored content" in narrate(
        _assistant_tool_use("Write", file_path="/out/instance.yaml"))


def test_narrator_counts_render_attempts():
    """First render says 'rendering'; subsequent ones report the retry number."""
    narrate = web.make_narrator()
    first = narrate(_assistant_tool_use("Bash", command="resume-gen render --instance x"))
    second = narrate(_assistant_tool_use("Bash", command="resume-gen render --instance x"))
    assert "rendering the PDF" in first
    assert "attempt 2" in second


def test_narrator_reports_page_fit_outcome():
    narrate = web.make_narrator()
    fits = json.dumps({"type": "user", "message": {"content": [
        {"type": "tool_result", "content": '{"page_count": 1}'}]}})
    over = json.dumps({"type": "user", "message": {"content": [
        {"type": "tool_result", "content": '{"page_count": 2}'}]}})
    assert "fits on one page" in narrate(fits)
    assert "trimming to fit" in narrate(over)


def test_narrator_skips_thinking_and_result_events():
    narrate = web.make_narrator()
    assert narrate(json.dumps({"type": "result", "subtype": "success"})) is None


# ---- Download guard constants ------------------------------------------------

def test_slug_regex_rejects_traversal():
    assert web.SLUG_RE.match("csa-project-manager-2026-07-06")
    assert not web.SLUG_RE.match("../etc")
    assert not web.SLUG_RE.match("foo/bar")
    assert not web.SLUG_RE.match("")


def test_only_whitelisted_files_are_downloadable():
    assert "resume.pdf" in web.DOWNLOADABLE
    assert "resume.docx" in web.DOWNLOADABLE
    assert "master.yaml" not in web.DOWNLOADABLE  # PII must never be served


# ---- HTTP routing / validation (real server, ephemeral port, no pipeline) ----

@pytest.fixture()
def server(tmp_path, monkeypatch):
    """A live server bound to port 0, with OUTPUT redirected to a temp dir so a
    download test can create a fake resume without touching the real output/."""
    monkeypatch.setattr(web, "OUTPUT", tmp_path)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), web.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address
    try:
        yield f"http://{host}:{port}", tmp_path
    finally:
        httpd.shutdown()
        httpd.server_close()


def _get(url):
    try:
        with urlopen(url) as r:
            return r.status, r.read()
    except HTTPError as e:
        return e.code, e.read()


def test_index_page_served(server):
    base, _ = server
    status, body = _get(base + "/")
    assert status == 200
    assert b"Resume Generator" in body


def test_unknown_path_404(server):
    base, _ = server
    status, _ = _get(base + "/nope")
    assert status == 404


def test_download_rejects_traversal_slug(server):
    base, _ = server
    status, _ = _get(base + "/download?slug=../&file=resume.pdf")
    assert status == 400


def test_download_rejects_non_whitelisted_file(server):
    base, _ = server
    status, _ = _get(base + "/download?slug=job1&file=master.yaml")
    assert status == 400


def test_download_missing_file_404(server):
    base, _ = server
    status, _ = _get(base + "/download?slug=job1&file=resume.pdf")
    assert status == 404


def test_download_serves_real_file(server):
    base, out = server
    slug = "acme-engineer-2026-07-07"
    (out / slug).mkdir()
    (out / slug / "resume.pdf").write_bytes(b"%PDF-1.7 fake")
    status, body = _get(base + f"/download?slug={slug}&file=resume.pdf")
    assert status == 200
    assert body == b"%PDF-1.7 fake"


def test_generate_rejects_empty_body(server):
    base, _ = server
    req = Request(base + "/generate", data=b"", method="POST")
    try:
        with urlopen(req) as r:
            status = r.status
    except HTTPError as e:
        status = e.code
    assert status == 400
