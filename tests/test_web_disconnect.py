"""A dropped web client must not hang the run it started.

Regression: emit() re-raised BrokenPipeError, which aborted the read loop over
the child's stdout. Nobody drained the pipe, so the child blocked on write
forever (runs stuck for days, no cost.json, no handoff log line).
"""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("web_app", ROOT / "web" / "app.py")
web_app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(web_app)


class _DeadPipe:
    def __init__(self):
        self.writes = 0

    def write(self, _data):
        self.writes += 1
        raise BrokenPipeError

    def flush(self):
        pass


class _FakeHandler:
    """Just enough of Handler for _open_stream / _run_narrated."""

    def __init__(self):
        self.wfile = _DeadPipe()

    def send_response(self, _code):
        pass

    def send_header(self, *_a):
        pass

    def end_headers(self):
        pass


def test_emit_goes_quiet_after_client_disconnect():
    h = _FakeHandler()
    emit = web_app.Handler._open_stream(h)
    emit("first\n")          # client is gone: must not raise
    emit("second\n")
    assert h.wfile.writes == 1   # stops writing after the first failure


def test_run_drains_child_output_after_disconnect():
    h = _FakeHandler()
    emit = web_app.Handler._open_stream(h)
    emit("hello\n")
    # ~1 MB of stream-json-ish output: far beyond a 64 KB pipe buffer, so the
    # child would block forever if the parent stopped reading.
    cmd = [sys.executable, "-c",
           "import sys\n"
           "for i in range(20000):\n"
           "    sys.stdout.write('{\"type\":\"x\",\"pad\":\"' + 'a'*40 + '\"}\\n')\n"
           "sys.exit(7)\n"]
    code, _state = web_app.Handler._run_narrated(h, cmd, None, emit)
    assert code == 7
