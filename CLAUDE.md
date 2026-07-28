# CLAUDE.md — Agent Instructions for this Repo

This repo (`ai-resume-generator`) builds a headless Claude agent that turns a
job posting into a one-page tailored resume, wrapped in deterministic
guardrails. Full product/technical context lives in `README.md`, `PRD.md`,
and `TECH_SPEC.md` — read those before making non-trivial changes.

## Mandatory hygiene: update the session handoff after every task

**Every agent that touches this repo must update `SESSION_HANDOFF.md` before
ending its turn**, whether the task was a fix, a feature, an investigation,
or a "no changes needed" conclusion. This is not optional. The handoff file
is the only thing a fresh agent reads to understand what's been done and
what's next — if it goes stale, the next agent re-derives context that
already exists, or worse, repeats work or reverts a deliberate decision.

When you finish a task (or a meaningful chunk of one):

1. Move/update the relevant line(s) in **"What's done"**.
2. Update **"What's next"** — if you didn't finish the top item, say so and
   why; if you finished it, promote the next one.
3. Add a dated one-line entry to **"Log"** (newest on top) — what changed and
   why, not a diff dump.
4. If you touched `TODO.md`'s checklist, keep it in sync — `SESSION_HANDOFF.md`
   points to it rather than duplicating it.

Keep entries terse. This file is a relay baton, not a changelog for humans —
optimize for "a cold agent can pick up the next task in under a minute."

## Working rules specific to this repo

- **`master.yaml` (repo root) is private and must never be committed.** It
  holds the user's real name, phone, email, and full work history. It's
  git-ignored (`/master.yaml`, anchored to root only — `tests/fixtures/**`
  fixtures named `master.yaml` are intentionally synthetic and tracked).
  Never `git add -f` it, never paste its contents into a commit message, PR
  description, or issue. If you ever find it staged or committed, stop and
  flag it — do not push.
- **NEVER delete, truncate, or overwrite `master.yaml` destructively.** It is
  the user's irreplaceable career data and there is no copy in git (by design).
  Standing user instruction (2026-07-28): "do not ever delete my master
  template." Treat it as read-mostly; edits only to *add* real content the user
  supplies.
- **An out-of-repo backup exists and is auto-synced — keep both in step.** The
  canonical file is `resume_generator/master.yaml`; it is mirrored to
  `~/.local/share/resume-gen/master.yaml` with versioned snapshots in
  `~/.local/share/resume-gen/master-backups/`. A systemd user path-unit +
  timer (`resume-master-backup.{path,timer,service}` → `~/.local/bin/resume-master-sync`)
  copy the repo file to the backup on every change (the sync script refuses to
  overwrite the backup with an empty/broken master). If you ever restore
  `master.yaml`, prefer the backup/snapshots; if you edit it, the backup
  updates itself, but a manual `resume-master-sync` confirms it.
- **`output/` is git-ignored** — generated resumes contain personal contact
  details pulled from `master.yaml`.
- Rebuild the Docker image (`docker build -t resume-gen .`) after changing
  anything under `templates/` or `scripts/` — the image bakes in a copy, and
  stale images silently run old code.
- Full test suite: `python3 -m pytest tests/ -q` (works without Docker or the
  private `master.yaml` — tests that need it skip on a fresh checkout).
- `TODO.md` is the authoritative task/phase checklist against `PRD.md`. Check
  items off there as you complete them; don't recreate a parallel list.

## History note (2026-07-24)

The real `master.yaml` was previously force-added (`git add -f`) and pushed
to this **public** GitHub repo across 4 commits, exposing the user's phone,
email, and career history. It was remediated same-day: history was rewritten
to strip `master.yaml` from every commit and force-pushed clean; the
`.gitignore` rule was also anchored to `/master.yaml` to stop it from
accidentally masking synthetic test fixtures of the same name (the anchor
does *not* stop a deliberate `-f` add — see the working rule above). See
`SESSION_HANDOFF.md` log for details. **Never force-add `master.yaml` for
any reason**, including "just to test something locally."
