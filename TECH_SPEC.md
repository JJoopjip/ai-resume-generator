# TECH SPEC — Tailored Resume Generator

Implementation-level companion to `PRD.md`. The PRD says *what* and *why*;
this says *exactly how*, so Phase 3 can be implemented without re-deriving
decisions. Every open question in `TODO.md`'s Phase 1 checklist and "Gaps"
section is resolved below.

## 1. CLI Argument / Flag Definitions

Entry point: `scripts/generate_resume.py`, wrapped by the `resume-gen` shell
script (§7) that shells into the Docker image.

```
resume-gen render
    --instance PATH      (required) path to instance.yaml
    --master PATH         (required) path to master.yaml
    --out DIR             (required) output directory for resume.pdf/.docx
    --schema PATH          (optional, default schema/instance.schema.json)
    --layout PATH           (optional) path to a layout.json/.yaml overriding
                             font_size_pt / margin_in (see §4a). Omitted keys
                             fall back to schema/layout.schema.json's defaults;
                             omit the flag entirely for the tightened default
                             (10.5pt / 0.5in).
    --layout-schema PATH     (optional, default schema/layout.schema.json)

resume-gen validate
    --instance PATH       (required)
    --master PATH          (required)
    --schema PATH           (optional, default schema/instance.schema.json)
```

`validate` intentionally has no `--layout` — layout affects only how the PDF
is typeset, not whether `instance.yaml`'s content is valid, so it stays out
of the content-only validation path.

No `--json` flag: JSON is always the stdout contract (§2) since Claude is the
primary caller and a human can pipe through `jq` when running manually.

### Exit codes

| Code | Meaning                                                        |
|------|-----------------------------------------------------------------|
| 0    | Success — `validate`: schema+verbatim valid. `render`: valid AND 1 page. |
| 1    | Validation failure (schema, locked-field, bullet-verbatim, or layout out-of-range mismatch). |
| 2    | Render/compile error (Tectonic failure, template error, docx-write error). |
| 3    | Page overflow — validated and rendered fine, but page count > 1. |
| 4    | Usage error (missing/unreadable file, bad arguments).           |

Distinct codes let Claude's loop branch on exit code alone without parsing
stdout, per PRD §6.

## 2. Structured Output Contract

Both subcommands always emit exactly one JSON object to stdout, newline
terminated, nothing else on stdout (diagnostics/tracebacks go to stderr).

```json
{
  "command": "render",
  "valid": true,
  "errors": [
    {
      "code": "locked_field_mismatch",
      "id": "winnergy",
      "field": "title",
      "expected": "Business Development & Online Marketing Manager",
      "actual": "Business Development Manager",
      "message": "Locked field 'title' does not match master.yaml for id 'winnergy'."
    }
  ],
  "page_count": 1,
  "output_files": {
    "pdf": "output/acme-pm-2026-07-05/resume.pdf",
    "docx": "output/acme-pm-2026-07-05/resume.docx"
  }
}
```

- `errors` is always present (empty array on success).
- `error.code` is a stable machine-readable enum: `schema_error`,
  `locked_field_mismatch`, `bullet_not_verbatim`, `unknown_id`,
  `render_error`, `overflow`, `layout_invalid`.
- `page_count` / `output_files` are `null` for `validate` or on failure before
  those steps ran.
- On overflow (exit 3), `valid` is `true` and `errors` is empty — overflow is
  not a validation failure, it's reported via `page_count` > 1 and the exit
  code; Claude reads `page_count` to decide what to trim next.

## 3. `instance.schema.json` — Structural Requirements

(File itself is written in Phase 3; this section is the spec it must satisfy.)

Draft 2020-12 JSON Schema, top-level `object`, `required`: `schema_version`,
`profile`, `job_description_ref`, `meta`, `summary`, `experience`,
`education`, `certifications`, `skills`, `languages`, `priority_order`.

- `schema_version`: `number`, must equal `master.yaml`'s `schema_version`
  (currently `1.0`) — script asserts this before any other check and fails
  with `schema_error` on mismatch (resolves TODO's versioning-discipline gap).
- `profile`: `string`, one of the profile keys in `master.yaml`'s `profiles`
  map (`bd`/`pm`/`dm`/`general`) — free text is not allowed even though
  bullets may blend profiles; this field is a label only (PRD §5).
- `meta`: object, must deep-equal `master.yaml.meta` verbatim (locked).
- `summary`: non-empty `string`, exempt from verbatim matching (§7 rule 3).
- `experience`: array of objects. Each requires: `id`, `company`, `location`,
  `title`, `start`, `end`, `bullets`. Optional passthrough fields copied
  verbatim when present in `master.yaml` for that id: `multinational`,
  `multinational_note`, `part_time`, `concurrent` — the renderer needs these
  to append notes and to place part-time/concurrent roles after full-time
  ones (PRD's experience-ordering note). `id` must reference an id present in
  `master.yaml.experience`.
  - `bullets`: array of `{id, text}`. `id` must be a bullet id under that
    experience id in `master.yaml`; `text` checked verbatim in §7 rule 2, not
    by the JSON Schema itself (schema only checks shape/type — string
    matching is `validate.py`'s job, not `instance.schema.json`'s).
- `education` / `certifications`: arrays, each entry's non-`id` fields
  checked verbatim against `master.yaml` by id (order may differ from
  master — reordering is allowed, rewriting is not).
- `skills`: array of `{label, items: [string]}`. `items` must be a subset of
  some `master.yaml` skill group's `items` for that `label`; `validate.py`
  enforces this (not pure JSON Schema — needs the master.yaml lookup).
- `languages`: copied verbatim, array of `{name, level}`.
- `priority_order`: object, one key per experience `id` present in
  `experience`, value = array of bullet-id strings, ascending priority
  (lowest-priority-to-cut first). Every bullet id under that role in
  `bullets` must appear exactly once in the corresponding `priority_order`
  array (schema-checkable via a cross-field check in `validate.py`, since
  JSON Schema alone can't express "same set as sibling field").

## 4. LaTeX Layout Decisions (Jake's-Resume Style)

- **Document**: `article`, `10pt` base (`documentclass` option is fixed at
  the lowest allowed size; actual body size is an explicit `\fontsize`
  override — see §4a, since standard LaTeX classes only offer discrete
  10/11/12pt and the allowed range includes fractional sizes like 10.5pt),
  `letterpaper`.
- **Margins**: uniform on all four sides via `geometry`'s `margin=` option,
  value supplied by `layout.margin_in` (§4a) — replaces the original fixed
  asymmetric `0.5in`/`0.6in` top-bottom/left-right split with a single bounded
  knob.
- **Fonts**: default Latin Modern (Computer Modern) via `lmodern` — no custom
  font install needed in the Docker image, keeps Tectonic's font resolution
  simple and reproducible.
- **Section order** (top to bottom): Header (name, location, phone, email,
  LinkedIn) → Summary → Experience → Education → Skills → Certifications →
  Languages. Certifications is folded into a single line under Skills rather
  than its own headed section (it's one line: PMP) to save vertical space
  for the one-page constraint.
- **Section headings**: small caps, bold, full-width bottom rule (`titlesec`),
  matching Jake's-resume convention.
- **Experience ordering**: within `experience`, full-time roles render in the
  order given in `instance.yaml`; entries with `part_time: true` or
  `concurrent: true` render after all non-part-time/non-concurrent entries,
  preserving relative order within each group (PRD's placement rule).
- **`multinational_note` rendering**: when `multinational: true` and
  `multinational_note` is present on an experience entry, append
  `" (" + multinational_note + ")"` in smaller/italic text immediately after
  the company name on that entry's header line.
- **Date formatting**: dates are pre-formatted strings in `master.yaml`
  (e.g. `"Aug 2022"`); the template renders `"{start} – {end}"` using an
  en dash (`--` in LaTeX), no reparsing. No `end` value is not expected in
  v1 (no current role marked ongoing) — if it appears empty/null, render
  `"Present"`.
- **Skills rendering**: one line per skill group — `**{label}:** {items
  joined by ", "}`. Multi-profile blending is already resolved by the time
  `instance.yaml` reaches the renderer (Claude picked/merged the group list),
  so the template does no profile logic itself.
- **Page count**: template includes `\usepackage{lastpage}` and a hidden
  `\label{LastPage}`; `render_pdf.py` parses the compiled `.aux`/`.log` (or
  shells `pdfinfo`) for the page count rather than trusting a LaTeX counter
  printed into the PDF itself.

## 4a. Layout Overrides & the Overflow Ladder

`master.yaml`'s original hard rule was "never shrink fonts, margins, or
facts to make room" — treating layout knobs and content as one undifferentiated
thing not to touch. In practice this meant every overflow, however small,
was resolved by deleting a real achievement, even when the actual fix was
that the initial layout constants (chosen ad hoc, not tuned) were simply
looser than they needed to be. This section replaces that all-or-nothing
rule with a bounded, ordered set of levers — content is the *last* one, not
the first.

**`schema/layout.schema.json`** defines the only two tunable knobs, each with
a `minimum`, `maximum`, and `default`:

| Field           | Min  | Max  | Default | Notes |
|-----------------|------|------|---------|-------|
| `font_size_pt`  | 10.0 | 11.0 | 10.5    | Below 10.0 reads as visibly crammed to a human skimmer; ATS itself is agnostic to font size entirely. |
| `margin_in`     | 0.4  | 0.6  | 0.5     | Uniform on all sides. Below 0.4 risks unprintable-edge issues on real printers and starts reading as cramped. |

An optional `output/<slug>/layout.json` (or `.yaml`) supplies overrides;
missing keys fall back to the schema's `default`. `validate_layout()` in
`validate.py` range-checks whatever is supplied against the schema
(`additionalProperties: false`, so typos are caught) — an out-of-range value
is `layout_invalid`, same exit-1 bucket as any other validation failure, not
a separate error class.

Everything *not* in `layout.schema.json` — section/item/role spacing,
itemize tightness, header spacing — is a **fixed constant** baked into
`resume.tex.j2`, tuned once as the new tightened baseline (`\titlespacing`
before/after went from 8pt/4pt to 6pt/3pt, itemize `topsep` from 2pt to 1pt,
inter-role `\vspace` from 2pt to 3pt net after other tightening). These
aren't exposed as knobs because they should just be *correct* — there's no
scenario where loosening them helps rather than just wasting space.

**Font size beyond the documentclass option.** Standard LaTeX classes only
support discrete 10/11/12pt via `\documentclass[Npt]`, but the allowed range
includes fractional steps (10.5pt). The template fixes the class at `10pt`
and overrides the actually-applied size everywhere via explicit
`\fontsize{size}{leading}\selectfont` calls (leading computed as
`size * 1.2`, standard single-spaced typesetting ratio) — for body text, the
section-heading size (`font_size_pt + 1.5`), the name header
(`font_size_pt + 3.5`), and small text like `multinational_note`/education
detail/the page-number footer (`font_size_pt - 1` / `- 1.5`). This keeps
every text element's size consistently derived from the one
`layout.font_size_pt` value rather than relying on the class's built-in
`\Large`/`\small`/etc., whose absolute point sizes are pinned to whichever
discrete class size was declared.

**The overflow ladder** (what a caller — currently a human, eventually
Claude per §6 — should try, in order, before dropping a bullet):

1. Render at the default layout (10.5pt / 0.5in). If ≤1 page, done.
2. If overflow: re-render once at the floor (`font_size_pt: 10.0,
   margin_in: 0.4`) in a single jump — not gradual stepping, since the
   allowed range is narrow enough that incremental steps just waste retry
   budget. If ≤1 page, done; **no content was touched.**
3. Only if still >1 page at the floor: fall back to dropping the next
   lowest-`priority_order` bullet (TECH_SPEC's original Tier-4 mechanism,
   unchanged), re-rendering at the floor layout each time. Capped at 5 total
   render attempts (PRD §8) as before.

In practice (validated against a real job application during the Phase 3
dry run), step 2 alone recovered a full page's worth of overflow on an
11-bullet, 3-role resume with zero bullets dropped — confirming the layout
constants in step 1 had real slack, not that the content was genuinely too
long.

**Scope**: layout overrides apply to the PDF path only. `render_docx.py`
keeps its own fixed Calibri sizing (§5) regardless of `layout.json` — DOCX
has no page-count gate to satisfy in the first place (§5), so there's
nothing for the ladder to fix there.

## 5. DOCX Styling Decisions (python-docx)

**Decision: visually consistent, not pixel-identical to the PDF.** Word/LibreOffice
can't reproduce Latin Modern's metrics or LaTeX's rule/spacing model exactly;
chasing pixel parity would burden `render_docx.py` for no real benefit since
the PDF is the canonical "one true rendering" (used for page-count truth) and
the DOCX exists so recruiters/ATS systems that require `.docx` have an
editable copy.

Match on: same section order, same heading text/hierarchy, same bullet
content and order, same one-page target (docx has no hard page-count
enforcement — only the PDF's Tectonic count gates the overflow loop).

Concrete styling:
- Font: Calibri, 10.5pt body / 11pt name header (widely available, ATS-safe
  substitute for Latin Modern).
- Margins: 0.5in all sides (`docx` section properties).
- Section headings: bold, 11pt, single bottom border (`WD_LINE_SPACING`
  + a bottom-border XML tweak on the paragraph), matching the PDF's rule
  style without needing LaTeX.
- Bullets: native Word bulleted list style, one `add_paragraph(style="List
  Bullet")` per bullet text.
- No live page-count check — `render_docx.py` does not attempt Tectonic-style
  pagination measurement; if the PDF fits one page after the overflow loop,
  the DOCX (built from the same trimmed `instance.yaml`) is assumed to fit
  too, given matched content and comparable font sizing.

## 6. Claude CLI Invocation Spec

The "Claude CLI" in the PRD is a **Claude Code agent session**, not a raw
Anthropic Messages-API call — this keeps auth on the user's existing Claude
Code login (no separate `ANTHROPIC_API_KEY` plumbing needed for v1) and lets
the agent use its normal file-reading tools instead of a bespoke prompt-
assembly script.

- **Invocation**: user runs Claude Code in this repo (interactively, or
  `claude -p "<task>"` for a scripted one-shot) with a prompt that points at
  `prompts/tailor_resume.md`, `master.yaml`, and the job description file by
  path — Claude reads all three with its own Read tool. No file content is
  pre-concatenated into the prompt string by a wrapper script.
- **Model**: pinned in the `resume-gen` launcher to `--model claude-opus-4-8
  --effort high` for reproducibility — JD→bullet selection and overflow
  trade-offs reward the strongest model at high effort on this infrequent,
  high-stakes task. Overridable via `RESUME_GEN_CLAUDE_FLAGS` (e.g.
  `--model claude-sonnet-5 --effort medium` for cheaper/faster runs). Interactive
  sessions still use whatever the invoking session is configured for.
- **Job description input**: plain text file, `job_description.txt`, path
  passed to Claude in the prompt; Claude copies it into
  `output/<slug>/job_description.txt` as part of writing `instance.yaml`
  (PRD's audit-trail requirement).
- **Loop mechanics**: Claude shells `resume-gen render ...` itself (it has
  Bash access in a normal Claude Code session), reads the JSON off stdout
  and the exit code, and on exit code 3 edits `instance.yaml` to drop the
  next id from the relevant role's `priority_order`, then retries — capped
  at 5 attempts (PRD §8), after which it reports "cannot fit one page
  without further human trimming" instead of looping forever.
- **No separate script drives this loop.** `generate_resume.py` never calls
  Claude; the direction of control is Claude calling the script, per PRD's
  architecture split.

## 7. Dockerfile / Packaging Decisions

- **Base image**: `python:3.12-slim` (Debian-based, small, glibc — Tectonic's
  static binary needs glibc, ruling out `-alpine`).
- **Tectonic install**: download the pinned static-binary release directly
  from Tectonic's GitHub releases (`tectonic-<version>-x86_64-unknown-linux-
  musl.tar.gz`) in the `Dockerfile`, verify checksum, place at
  `/usr/local/bin/tectonic`. Pin an explicit version (not `latest`) so builds
  are reproducible; bump deliberately.
- **Python deps**: `requirements.txt` (§8) installed via `pip install
  --no-cache-dir -r requirements.txt` in the image.
- **Non-root user**: create `appuser` (`useradd -m appuser`), `USER appuser`
  after installs, `WORKDIR /work`.
- **Volume mount convention**: host project directory mounted at `/work`;
  all `--instance`/`--master`/`--out` paths in CLI invocations are relative
  to `/work` (i.e. relative to the host cwd the user ran `docker run` from).
- **Wrapper script** (`resume-gen`, plain shell, checked into repo root):
  ```sh
  #!/usr/bin/env sh
  exec docker run --rm -v "$(pwd)":/work resume-gen "$@"
  ```
  so `resume-gen render --instance ... ` reads as a native CLI call.

## 8. Dependency Manifest

`requirements.txt` (pinned, resolved during Phase 3 setup, versions TBD at
install time but capped to a major version to avoid silent breaking changes):

```
pyyaml>=6,<7
jinja2>=3,<4
python-docx>=1,<2
jsonschema>=4,<5
```

No `pyproject.toml` in v1 — this is a single-purpose script collection run
inside Docker, not a published package; a flat `requirements.txt` is the
lower-ceremony fit documented in PRD §10.

## 9. Repo Hygiene

- **`.gitignore`**: add one covering `output/` — resolved as **gitignored,
  not committed**. Rationale: `output/` contains per-application PDFs/DOCXs
  and `instance.yaml` files with the same PII as `master.yaml`
  (phone/email), multiplied across every company applied to; keeping the
  repo's committed history clean and PII surface minimal outweighs having a
  built-in audit trail in git — the audit trail already lives on disk in
  `output/` locally, which is sufficient. Also ignore standard Python/Tex
  cruft: `__pycache__/`, `*.pyc`, `*.aux`, `*.log`, `*.out` (LaTeX build
  byproducts if ever compiled outside the container).
- **Repo privacy**: confirm before any push to a remote that the remote is
  private, since `master.yaml` contains phone/email in plaintext regardless
  of `.gitignore` on `output/`.
- **`README.md`**: deferred to Phase 3 once the CLI is real, so it documents
  the actual interface instead of drifting from this spec.
- **Test job descriptions**: deferred to Phase 3/6 — add 2-3 sample JDs
  under `tests/fixtures/` when validate.py's unit tests are written, one per
  profile (bd/pm/dm) so the dry run in PRD Milestone 6 has fixtures ready
  rather than needing fresh JDs hunted down at that point.

## 10. Versioning Discipline

- `instance.yaml`'s `schema_version` must equal `master.yaml`'s
  `schema_version` at validation time (§3) — hard fail with `schema_error`
  otherwise. This is the enforcement mechanism for the TODO gap: if
  `master.yaml`'s shape changes and its `schema_version` bumps, any
  `instance.yaml` written against the old shape is caught immediately
  instead of silently validating against a mismatched bank.
- `instance.schema.json` itself should carry a `"$id"`/version comment tied
  to the same `schema_version` number, bumped in lockstep whenever the
  instance shape changes, so schema and data version drift is visible in
  diffs.
