# Tailored Resume Generator

Turns a job description + `master.yaml` (the single source-of-truth content
bank) into a one-page `resume.pdf` + `resume.docx`. Content selection is a
Claude Code agent's job (`prompts/tailor_resume.md`); rendering, validation,
and page-count enforcement are a deterministic script's job — no LLM call
happens inside the renderer itself. See `PRD.md` for the full design and
`TECH_SPEC.md` for implementation-level decisions.

## One-shot: job description → resume

```sh
./resume-gen path/to/job_description.txt
```

This launches a scripted, headless Claude Code session (`TECH_SPEC.md` §6) that
reads `prompts/tailor_resume.md` + `master.yaml` + the JD, writes
`output/<company>-<role>-<date>/instance.yaml`, then drives the render/overflow
loop itself until it produces a one-page `resume.pdf` + `resume.docx`. Requires
the `claude` CLI on `PATH` (uses your existing Claude Code login — no API key).
The result is always a **draft for human review**.

The tailor stage defaults to `--model claude-sonnet-5 --effort medium` (a strong,
cost-effective default; the validator guards correctness regardless of model).
Bump to Opus 4.8 / high for the sharpest selection on a high-stakes application:

```sh
RESUME_GEN_CLAUDE_FLAGS="--model claude-opus-4-8 --effort high \
  --permission-mode acceptEdits --allowedTools Bash Read Edit Write" ./resume-gen jd.txt
```

Everything below is the deterministic render half that the tailor stage (and you)
call — no LLM involved.

## Quick start (Docker — no local Python/LaTeX needed)

```sh
docker build -t resume-gen .

./resume-gen validate --instance output/acme-pm-2026-07-05/instance.yaml \
                       --master master.yaml

./resume-gen render --instance output/acme-pm-2026-07-05/instance.yaml \
                     --master master.yaml \
                     --out output/acme-pm-2026-07-05/
```

`resume-gen` is a thin wrapper (`./resume-gen`) that mounts your current
directory into the container at `/work` and runs the image's entrypoint —
so all `--instance`/`--master`/`--out` paths above are relative to wherever
you run it from, not to the repo checkout inside the image.

## Normal workflow

1. Save the job posting as `job_description.txt` somewhere (e.g.
   `output/<company>-<role>-<date>/job_description.txt`).
2. Run Claude Code in this repo and point it at `prompts/tailor_resume.md`,
   `master.yaml`, and the job description. Claude reads all three and
   writes `output/<company>-<role>-<date>/instance.yaml`.
3. Claude shells out to `resume-gen render` itself, reads the JSON off
   stdout and the exit code, and on overflow (exit 3) trims the
   lowest-priority bullet from `instance.yaml`'s `priority_order` and
   retries — capped at 5 attempts.
4. You end up with:
   ```
   output/<company>-<role>-<date>/
     ├── job_description.txt
     ├── instance.yaml
     ├── resume.pdf
     └── resume.docx
   ```
   Review before sending — output is always a draft, never auto-submitted.

## CLI reference

```
resume-gen render
    --instance PATH   (required) path to instance.yaml
    --master PATH      (optional, default: ./master.yaml)
    --out DIR          (optional, default: the instance file's own folder)
    --layout PATH        (optional, default: 10.0pt / 0.4in tight one-page baseline)
    --schema PATH        (optional, default: schema/instance.schema.json
                          bundled in the image)

resume-gen validate
    --instance PATH   (required)
    --master PATH      (optional, default: ./master.yaml)
    --schema PATH        (optional, same default as above)
```

With the defaults, a render is just:

```sh
./resume-gen render --instance output/acme-pm-2026-07-05/instance.yaml
```

Both subcommands print exactly one JSON object to stdout and nothing else
(tracebacks/diagnostics go to stderr):

```json
{
  "command": "render",
  "valid": true,
  "errors": [],
  "page_count": 1,
  "output_files": {
    "pdf": "output/acme-pm-2026-07-05/resume.pdf",
    "docx": "output/acme-pm-2026-07-05/resume.docx"
  }
}
```

### Exit codes

| Code | Meaning                                                          |
|------|-------------------------------------------------------------------|
| 0    | Success — `validate`: schema+verbatim valid. `render`: valid AND 1 page. |
| 1    | Validation failure (schema, locked-field, or bullet-verbatim mismatch). |
| 2    | Render/compile error (Tectonic failure, template error, docx-write error). |
| 3    | Page overflow — validated and rendered fine, but page count > 1.  |
| 4    | Usage error (missing/unreadable file, bad arguments).              |

Full contract (error codes, field meanings): `TECH_SPEC.md` §1-2.

## Running without Docker

Needs Python 3.12+, the packages in `requirements.txt`, and a
[Tectonic](https://tectonic-typesetting.github.io/) binary on `PATH`:

```sh
pip install -r requirements.txt
python3 scripts/generate_resume.py validate --instance instance.yaml --master master.yaml
python3 scripts/generate_resume.py render --instance instance.yaml --master master.yaml --out output/
```

## Repository layout

```
master.yaml                    # content bank: facts, bullet variants, themes
prompts/tailor_resume.md       # master prompt driving Claude's selection step
schema/instance.schema.json    # structural schema for instance.yaml
scripts/
  generate_resume.py           # CLI entrypoint (render / validate)
  validate.py                  # locked-field / bullet-verbatim / schema checks
  render_pdf.py                # Jinja2 -> .tex -> Tectonic -> .pdf + page count
  render_docx.py               # instance.yaml -> .docx via python-docx
templates/
  resume.tex.j2                # Jake's-style LaTeX template
  resume_docx_style.py         # DOCX styling constants
tests/test_validate.py         # unit tests against master.yaml's real content
Dockerfile, resume-gen         # packaging (see TECH_SPEC.md §7)
output/                        # gitignored — per-application PDFs/DOCXs/instance.yaml
```

## Development

```sh
pip install -r requirements.txt pytest
python3 -m pytest tests/ -q
```

`output/` is gitignored (it holds PII-bearing generated files per
application) — see `TECH_SPEC.md` §9 before pushing this repo anywhere,
since `master.yaml` itself has plaintext phone/email regardless.
