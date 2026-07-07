# web/ — local browser front end (Phase 2, optional)

A tiny paste-and-generate web page in front of the existing `./resume-gen`
pipeline. **Fully additive:** everything lives in this folder, nothing outside
`web/` is modified, and no packages are installed — it uses only the Python
standard library. To go back to basics, ignore or delete this folder; every
resume you generated is still in `output/` where it has always been.

## Run it — the easy way (one click)

Double-click **“Resume Generator”** on your Windows Desktop. That's it — it
starts the server if it isn't already running and opens the page in your
browser. No terminal, no Python. Close the tab when you're done; the little
server keeps running quietly in the background (or just leave it).

Under the hood that icon is a Windows shortcut (`Resume Generator.lnk`, with a
custom icon at `C:\Users\User\resume-icon.ico`) that runs `web/start.sh`, which
is idempotent — safe to click any number of times.

## Run it — the manual way

From the project root:

```sh
python3 web/app.py       # or: bash web/start.sh  (also opens the browser)
```

Then open <http://127.0.0.1:5000> in your browser.

1. Paste the full job posting into the box.
2. Click **Generate résumé**.
3. Watch the live log (the run takes a few minutes — same pipeline as the CLI).
4. When it finishes, use the **Download PDF / Word** buttons.

Stop the server with `Ctrl-C`.

## What it actually does

- Writes your pasted text to a temp file, then runs the **unmodified**
  `./resume-gen <tempfile>` — the exact command you'd run by hand.
- Streams that command's console output straight into the page.
- The pipeline writes `resume.pdf`, `resume.docx`, `omitted.md`, etc. to
  `output/<company>-<role>-<date>/` **on disk automatically**, exactly as
  before. The download buttons just copy those existing files out to your
  browser's download location — they are a convenience, not the thing that
  saves them.

## Run it — inside Docker (optional, "local container now")

If you'd rather run the web app as a container (a stepping stone toward hosting):

```sh
cd ~/resume_generator
docker compose -f web/docker-compose.yml up --build   # add -d to run in background
# → open http://127.0.0.1:5000
docker compose -f web/docker-compose.yml down          # stop it
```

This is **local only, not public.** The container deliberately reuses your own
machine: it renders PDFs through the **host Docker daemon** (via the mounted
`/var/run/docker.sock`, so no Docker-in-Docker) and signs in with your existing
**`claude` subscription login** (mounted read-only). The project is mounted at
the same absolute path it has on the host, which is what lets the renderer's
`docker run -v $(pwd):/work` resolve correctly. Nothing personal is baked into
the image — it's all mounts — so `docker compose down` plus deleting `web/`
reverts everything.

Because it leans on your machine's Docker socket and subscription login, this
exact image only runs here. Turning it into a genuinely public site is the
separate "deployable image" project (bake the renderer in, switch to an
Anthropic API key, deploy to a rented host).

The container and the plain `python3 web/app.py` both listen on port 5000, so
run one at a time. The Desktop icon is smart about this — if the container is
already serving on 5000, clicking the icon just opens the browser to it.

## Tests

The web front end has its own automated tests (`tests/test_web.py`), run
alongside the rest of the suite:

```sh
python3 -m pytest tests/test_web.py    # just the web tests
python3 -m pytest                      # the whole project
```

They cover the parts that can break without a full generation run: the
progress narrator (turning the engine's event stream into readable steps), the
download **path-traversal guard** (so only whitelisted files in `output/` can
ever be served — never `master.yaml`), and HTTP routing / empty-input handling.
They spin the server up in-process on a throwaway port and **never** invoke the
real Docker + Claude pipeline, so they run in a few seconds and cost nothing.

## Notes

- Binds to `127.0.0.1` only, so it is not reachable from your network. This
  matters because `master.yaml` holds personal contact info.
- Uses whatever model the CLI uses. To dial the AI up for a high-stakes
  application, launch with the same env var the CLI honours:
  ```sh
  RESUME_GEN_CLAUDE_FLAGS="--model claude-opus-4-8 --effort high \
    --permission-mode acceptEdits --allowedTools Bash Read Edit Write" \
    python3 web/app.py
  ```
- Change the port with `RESUME_WEB_PORT=8000 python3 web/app.py`.
