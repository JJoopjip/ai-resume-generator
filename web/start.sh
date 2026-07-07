#!/usr/bin/env bash
# web/start.sh — one-click launcher for the local resume web app.
#
# Double-clicking the "Resume Generator" icon on your Windows Desktop runs this.
# It is idempotent and safe to run any number of times:
#   1. If the server is already running, it just opens the browser.
#   2. Otherwise it starts the server DETACHED (survives this script exiting and
#      the launching terminal closing), waits until it answers, then opens it.
#
# You never need to touch Python or a terminal — that's the whole point.
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# When launched from the Desktop icon, WSL gives us a slim *non-login* PATH that
# omits ~/.local/bin — where the `claude` CLI lives. Without this the pipeline's
# `claude` call fails with "command not found" (exit 127). Put it back so the
# double-clicked server has the same tools your interactive terminal does.
export PATH="$HOME/.local/bin:$PATH"

PORT="${RESUME_WEB_PORT:-5000}"
URL="http://127.0.0.1:${PORT}"
LOG="$ROOT/web/server.log"          # *.log is already gitignored
EXPLORER="/mnt/c/WINDOWS/explorer.exe"

is_up() { curl -s -o /dev/null --max-time 2 "$URL" 2>/dev/null; }

open_browser() {
  # Set RESUME_WEB_NO_OPEN=1 to skip (used by automated tests).
  [ -n "${RESUME_WEB_NO_OPEN:-}" ] && return 0
  # explorer.exe opens the Windows default browser; it exits non-zero even on
  # success, so never let it fail the script.
  "$EXPLORER" "$URL" >/dev/null 2>&1 || true
}

if is_up; then
  echo "resume-web is already running at $URL"
  open_browser
  exit 0
fi

echo "starting resume-web …"
cd "$ROOT"
# setsid + nohup + closed stdio fully detaches the server from this shell so it
# keeps running after the launcher (and the WSL terminal the .bat opened) exits.
setsid nohup python3 web/app.py </dev/null >"$LOG" 2>&1 &

# Wait up to ~15s for it to come up.
for _ in $(seq 1 30); do
  is_up && break
  sleep 0.5
done

if is_up; then
  echo "resume-web is running at $URL"
  open_browser
else
  echo "resume-web failed to start — see $LOG" >&2
  exit 1
fi
