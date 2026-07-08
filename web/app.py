#!/usr/bin/env python3
"""web/app.py — a tiny, local, single-user front end for ./resume-gen.

Phase 2 (fully additive): this file and its siblings under web/ are the ENTIRE
footprint. Nothing outside web/ is touched, and nothing new is installed — this
uses only the Python standard library. Delete web/ to go back to basics.

What it does: serves one page where you paste a job description and click
Generate. On submit it writes your text to a temp file and runs the EXISTING
`./resume-gen <file>` pipeline (same command you run by hand), streaming the
pipeline's console output live into the browser. When the run finishes it
detects the new output/<slug>/ folder and offers the on-disk resume.pdf /
resume.docx — and the matching cover_letter.pdf / cover_letter.docx when the
run produced them — for download.

Note: the resume files are written to output/<slug>/ by the pipeline itself,
exactly as today — the "Download" buttons just copy those existing files out to
your browser's downloads. Nothing here changes where or whether files are saved.

Run:  python3 web/app.py       then open http://127.0.0.1:5000
"""

import json
import os
import re
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# ---- Locations ---------------------------------------------------------------
WEB_DIR = Path(__file__).resolve().parent
ROOT = WEB_DIR.parent                      # the resume_generator project root
OUTPUT = ROOT / "output"
RESUME_GEN = ROOT / "resume-gen"           # reused verbatim; never modified

# Localhost only by default. In the Docker setup this is set to 0.0.0.0 so the
# container can publish the port — but compose maps it to 127.0.0.1 on the host,
# so it still never faces the network. See web/docker-compose.yml.
HOST = os.environ.get("RESUME_WEB_HOST", "127.0.0.1")
PORT = int(os.environ.get("RESUME_WEB_PORT", "5000"))

# Only these on-disk artifacts may ever be downloaded (path-traversal guard).
_DOCX_CTYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
DOWNLOADABLE = {
    "resume.pdf": "application/pdf",
    "resume.docx": _DOCX_CTYPE,
    "cover_letter.pdf": "application/pdf",
    "cover_letter.docx": _DOCX_CTYPE,
    "omitted.md": "text/markdown; charset=utf-8",
    "instance.yaml": "text/yaml; charset=utf-8",
}
SLUG_RE = re.compile(r"^[A-Za-z0-9._-]+$")  # output folder names only

# One generation at a time. The pipeline drives Docker + a headless Claude
# session and detects "the new output folder" by diffing output/; two concurrent
# runs would race that diff. A non-blocking acquire lets a second request fail
# fast with a friendly "busy" instead of queuing or corrupting detection.
_run_lock = threading.Lock()


def _dirs():
    """Current set of output/<slug> folder names (empty if output/ absent)."""
    if not OUTPUT.exists():
        return set()
    return {p.name for p in OUTPUT.iterdir() if p.is_dir()}


# ---- Progress narration ------------------------------------------------------
# We run the pipeline's `claude` in stream-json mode (see RESUME_GEN_CLAUDE_FLAGS
# below), which emits one JSON event per action. make_narrator() turns that
# firehose into a few human-readable phase lines. It keeps a little state (how
# many render attempts so far) so it can say "attempt 2" during the overflow
# trim loop. Non-JSON lines (the launcher's own banners) pass through unchanged.

def _tool_phase(block, state):
    name = block.get("name", "")
    inp = block.get("input", {}) or {}
    if name == "Read":
        fp = str(inp.get("file_path", ""))
        low = fp.lower()
        if "master.yaml" in low:
            return "  📖  reading your career history"
        if "job_description" in low or low.endswith(".txt"):
            return "  📖  reading the job description"
        if "tailor_resume" in low or "/prompts/" in low:
            return "  📖  reading the tailoring instructions"
        return f"  📖  reading {os.path.basename(fp) or 'a file'}"
    if name in ("Write", "Edit"):
        fp = str(inp.get("file_path", "")).lower()
        if "instance.yaml" in fp:
            return "  ✍️  choosing and writing your tailored content"
        if "omitted" in fp:
            return "  📝  writing the omissions report (what was left out)"
        if "job_description" in fp:
            return "  🗂️  saving a copy of the job description"
        return f"  ✍️  writing {os.path.basename(fp) or 'a file'}"
    if name == "Bash":
        cmd = str(inp.get("command", ""))
        if "resume-gen render" in cmd or "render --instance" in cmd:
            state["render"] += 1
            if state["render"] == 1:
                return "  🖨️  rendering the PDF …"
            return f"  🖨️  re-rendering after trimming (attempt {state['render']}) …"
        if "validate" in cmd:
            return "  🔎  validating the draft …"
        if cmd.startswith("mkdir") or " mkdir " in cmd:
            return "  📁  creating the output folder"
        return None  # other shell commands: keep quiet
    return None


def make_narrator():
    state = {"render": 0}

    def narrate(line):
        text = line.rstrip("\n")
        if not text.strip():
            return None
        try:
            ev = json.loads(text)
        except (ValueError, TypeError):
            return text  # not JSON (e.g. the launcher's banner) — show as-is
        etype = ev.get("type")
        if etype == "system" and ev.get("subtype") == "init":
            return "  ⚙️  starting the tailoring engine …"
        if etype == "assistant":
            out = []
            for block in ev.get("message", {}).get("content", []):
                bt = block.get("type")
                if bt == "tool_use":
                    phase = _tool_phase(block, state)
                    if phase:
                        out.append(phase)
                elif bt == "text":
                    first = block.get("text", "").strip().splitlines()
                    if first:
                        out.append("  💬  " + first[0][:180])
                # 'thinking' blocks are intentionally not surfaced
            return "\n".join(out) if out else None
        if etype == "user":
            # Tool results — surface the page-fit outcome of a render. The
            # render's JSON is nested (and thus quote-escaped) inside the event,
            # so match the number loosely rather than by exact substring.
            m = re.search(r"page_count\D{0,4}(\d+)", text)
            if m:
                pages = int(m.group(1))
                if pages <= 1:
                    return "  ✅  it fits on one page"
                return f"  ✂️  {pages} pages — trimming to fit one page …"
            return None
        return None  # result/rate-limit/thinking-token events: skip

    return narrate


class Handler(BaseHTTPRequestHandler):
    # HTTP/1.0 (the default) closes the connection at end-of-response, so we can
    # stream the pipeline log by writing+flushing chunks without chunked-encoding
    # bookkeeping; the browser's fetch reader receives each flush as it lands.
    server_version = "resume-web/1"

    def log_message(self, *args):  # quieter console; the pipeline log is the point
        pass

    # -- routing ---------------------------------------------------------------
    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            return self._send_file(WEB_DIR / "templates" / "index.html",
                                   "text/html; charset=utf-8")
        if path == "/download":
            return self._download()
        self._send_text(404, "Not found")

    def do_POST(self):
        if urlparse(self.path).path == "/generate":
            return self._generate()
        self._send_text(404, "Not found")

    # -- helpers ---------------------------------------------------------------
    def _send_text(self, code, text):
        body = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, fp: Path, ctype: str):
        if not fp.is_file():
            return self._send_text(404, "Not found")
        body = fp.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _download(self):
        q = parse_qs(urlparse(self.path).query)
        slug = (q.get("slug") or [""])[0]
        fname = (q.get("file") or [""])[0]
        if not SLUG_RE.match(slug) or fname not in DOWNLOADABLE:
            return self._send_text(400, "Bad request")
        fp = (OUTPUT / slug / fname).resolve()
        # Ensure the resolved path really is inside output/<slug>/.
        if OUTPUT.resolve() not in fp.parents or not fp.is_file():
            return self._send_text(404, "Not found")
        body = fp.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", DOWNLOADABLE[fname])
        self.send_header("Content-Disposition",
                         f'attachment; filename="{slug}-{fname}"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _generate(self):
        length = int(self.headers.get("Content-Length", "0"))
        jd_text = self.rfile.read(length).decode("utf-8").strip() if length else ""
        if not jd_text:
            return self._send_text(400, "Paste a job description first.")

        # Refuse a second concurrent run rather than race output-folder detection.
        if not _run_lock.acquire(blocking=False):
            return self._send_text(
                409, "A résumé is already being generated. Please wait for it "
                     "to finish, then try again.")
        try:
            self._run_pipeline(jd_text)
        finally:
            _run_lock.release()

    def _run_pipeline(self, jd_text):
        # Open a streaming response. No Content-Length => body ends at close.
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        def emit(line: str):
            try:
                self.wfile.write(line.encode("utf-8"))
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                raise

        # Write the pasted JD to a temp file and run the UNMODIFIED pipeline.
        before = _dirs()
        with tempfile.NamedTemporaryFile(
            "w", suffix=".txt", prefix="jd-", delete=False, encoding="utf-8"
        ) as tf:
            tf.write(jd_text + "\n")
            jd_path = tf.name

        # Ask the pipeline's headless Claude for a streaming event log so we can
        # narrate progress. `--verbose` is required alongside stream-json. We
        # only set this when the user hasn't supplied their own flags, so a
        # custom RESUME_GEN_CLAUDE_FLAGS (e.g. Opus for a high-stakes run) still
        # wins — it just won't show step-by-step phases unless it, too, includes
        # `--output-format stream-json --verbose`.
        env = os.environ.copy()
        env.setdefault(
            "RESUME_GEN_CLAUDE_FLAGS",
            "--model claude-sonnet-5 --effort medium "
            "--permission-mode acceptEdits --allowedTools Bash Read Edit Write "
            "--output-format stream-json --verbose",
        )

        result = {"ok": False}
        try:
            emit("  web │ starting — this takes a few minutes; watch the steps below.\n\n")
            narrate = make_narrator()
            proc = subprocess.Popen(
                [str(RESUME_GEN), jd_path],
                cwd=str(ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
            )
            for line in proc.stdout:            # live stream, line by line
                phase = narrate(line)
                if phase:
                    emit(phase + "\n")
            code = proc.wait()

            new = sorted(_dirs() - before)
            slug = new[-1] if new else None
            if code == 0 and slug:
                have = [f for f in ("resume.pdf", "resume.docx",
                                    "cover_letter.pdf", "cover_letter.docx")
                        if (OUTPUT / slug / f).is_file()]
                result = {"ok": True, "slug": slug, "files": have,
                          "folder": str((OUTPUT / slug))}
            else:
                result = {"ok": False, "slug": slug, "code": code}
        except Exception as e:  # surface any launcher error into the log
            emit(f"\n  web │ error: {e}\n")
            result = {"ok": False, "error": str(e)}
        finally:
            try:
                os.unlink(jd_path)
            except OSError:
                pass

        # Sentinel line the page's JS watches for to render download buttons.
        try:
            emit("\n__RESULT__ " + json.dumps(result) + "\n")
        except (BrokenPipeError, ConnectionResetError):
            pass


def main():
    if not RESUME_GEN.is_file():
        raise SystemExit(f"cannot find {RESUME_GEN} — run from the project root")
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"  resume-web │ open  http://{HOST}:{PORT}   (Ctrl-C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  resume-web │ stopped")


if __name__ == "__main__":
    main()
