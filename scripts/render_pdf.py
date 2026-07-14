"""Jinja2 render -> Tectonic compile -> page-count extraction.

Per TECH_SPEC.md §4: Jake's-resume-style LaTeX, Latin Modern fonts, bounded
font-size/margin overrides (schema/layout.schema.json), full-time roles
before part-time/concurrent roles, multinational_note appended after company
name, dates rendered verbatim with an en dash.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

import jinja2

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
TEMPLATE_NAME = "resume.tex.j2"

# Characters LaTeX treats specially; escaped before any instance-derived
# string reaches the template so content authors never have to think about
# LaTeX syntax in master.yaml/instance.yaml.
_TEX_SPECIAL_CHARS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    "·": r"\textperiodcentered{}",
    "—": r"\textemdash{}",
}
_TEX_ESCAPE_RE = re.compile(
    "|".join(re.escape(c) for c in sorted(_TEX_SPECIAL_CHARS, key=len, reverse=True))
)


def tex_escape(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return _TEX_ESCAPE_RE.sub(lambda m: _TEX_SPECIAL_CHARS[m.group()], value)


def _escape_recursive(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _escape_recursive(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_escape_recursive(v) for v in obj]
    return tex_escape(obj)


def _order_experience(experience: list[dict]) -> list[dict]:
    """Full-time roles first (given order preserved), then part_time/concurrent
    roles (given order preserved) — TECH_SPEC.md §4 experience-ordering rule."""
    full_time = [e for e in experience if not (e.get("part_time") or e.get("concurrent"))]
    other = [e for e in experience if e.get("part_time") or e.get("concurrent")]
    return full_time + other


def _format_language(lang: dict) -> str:
    return f"{lang['name']} ({lang['level']})"


def _jinja_env() -> jinja2.Environment:
    # LaTeX uses {} and % constantly, so this uses the standard LaTeX+Jinja2
    # delimiter remap instead of Jinja's defaults ({{ }}, {% %}, {# #}).
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATE_DIR)),
        block_start_string=r"\BLOCK{",
        block_end_string="}",
        variable_start_string=r"\VAR{",
        variable_end_string="}",
        comment_start_string=r"\#{",
        comment_end_string="}",
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
    )
    env.filters["format_language"] = _format_language
    return env


def render_tex(instance: dict, out_dir: Path, layout: dict) -> Path:
    """Render resume.tex.j2 with an escaped, ordered copy of instance plus the
    bounded `layout` overrides (font_size_pt, margin_h_in, margin_v_in — see
    schema/layout.schema.json) into out_dir/resume.tex. Returns the path
    written."""
    safe_instance = _escape_recursive(instance)
    safe_instance["experience"] = _order_experience(safe_instance["experience"])
    safe_instance["layout"] = layout

    env = _jinja_env()
    template = env.get_template(TEMPLATE_NAME)
    tex_source = template.render(**safe_instance)

    out_dir.mkdir(parents=True, exist_ok=True)
    tex_path = out_dir / "resume.tex"
    tex_path.write_text(tex_source, encoding="utf-8")
    return tex_path


def compile_tex(tex_path: Path) -> tuple[bool, str]:
    """Shells out to Tectonic. Returns (success, combined stdout+stderr)."""
    try:
        result = subprocess.run(
            [
                "tectonic",
                "--keep-intermediates",
                "--keep-logs",
                "--outdir",
                str(tex_path.parent),
                str(tex_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return False, "tectonic binary not found on PATH"
    output = result.stdout + result.stderr
    return result.returncode == 0, output


def extract_page_count(out_dir: Path) -> int | None:
    """Parses the LastPage \\newlabel out of resume.aux (TECH_SPEC.md §4)."""
    aux_path = out_dir / "resume.aux"
    if not aux_path.exists():
        return None
    aux_text = aux_path.read_text(encoding="utf-8", errors="replace")
    # The `lastpage` package always defines this macro regardless of whether
    # hyperref remaps \newlabel's shape, so prefer it over parsing \newlabel.
    match = re.search(r"\\xdef\\lastpage@lastpage\{(\d+)\}", aux_text)
    if not match:
        return None
    return int(match.group(1))


# US Letter is 11in tall; TeX measures 1in as 72.27pt and 1pt as 65536sp, so
# \posy (in sp, measured from the page bottom) converts back to points this way.
_PT_PER_IN = 72.27
_SP_PER_PT = 65536
_PAGE_HEIGHT_PT = 11 * _PT_PER_IN


def extract_content_end_sp(out_dir: Path) -> int | None:
    """Read the `contentend` \\posy (sp, from the page bottom) that zref-savepos
    wrote into resume.aux. None if the marker is absent (older template, a
    compile that never reached a second pass, etc.) — callers treat that as
    'no estimate' and proceed unchanged."""
    aux_path = out_dir / "resume.aux"
    if not aux_path.exists():
        return None
    aux_text = aux_path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"\\zref@newlabel\{contentend\}\{.*?\\posy\{(\d+)\}", aux_text)
    return int(match.group(1)) if match else None


def compute_fill(out_dir: Path, layout: dict, page_count: int | None) -> dict | None:
    """Turn the end-of-content \\posy into an actionable one-page fit estimate.

    On a 1-page render: how many blank lines are left below the content
    (`lines_free`) — room the tailoring loop can backfill (ties into JD
    coverage). On overflow: roughly how many lines spilled past one page
    (`lines_over`) — how much to cut, in one pass instead of binary-searching.
    Returns None when the marker or page count is unavailable (fail-open)."""
    posy_sp = extract_content_end_sp(out_dir)
    if posy_sp is None or not page_count:
        return None
    posy_pt = posy_sp / _SP_PER_PT
    margin_pt = float(layout["margin_v_in"]) * _PT_PER_IN
    baseline_pt = float(layout["font_size_pt"]) * 1.2  # matches the template's \fontsize
    text_top_pt = _PAGE_HEIGHT_PT - margin_pt
    text_height_pt = _PAGE_HEIGHT_PT - 2 * margin_pt

    if page_count == 1:
        slack_pt = max(0.0, posy_pt - margin_pt)
        return {
            "page_count": 1,
            "lines_free": int(slack_pt // baseline_pt),
            "slack_pt": round(slack_pt, 1),
        }
    # Content on the final page runs from the text top down to the marker; each
    # earlier overflow page is ~a full text column. Approximate — \raggedbottom
    # means intermediate pages aren't exactly full — but good enough to size a cut.
    overflow_pt = (page_count - 2) * text_height_pt + (text_top_pt - posy_pt)
    overflow_pt = max(0.0, overflow_pt)
    return {
        "page_count": page_count,
        "lines_over": max(1, -(-int(overflow_pt) // int(baseline_pt))),  # ceil
        "overflow_pt": round(overflow_pt, 1),
    }


def render_pdf(instance: dict, out_dir: Path, layout: dict) -> dict:
    """Full pipeline: render .tex, compile, extract page count + fit estimate.

    Returns {"success": bool, "page_count": int | None, "pdf_path": Path | None,
    "fill": dict | None, "log": str}.
    """
    tex_path = render_tex(instance, out_dir, layout)
    success, log = compile_tex(tex_path)
    pdf_path = out_dir / "resume.pdf"
    page_count = extract_page_count(out_dir) if success else None
    fill = compute_fill(out_dir, layout, page_count) if success else None
    return {
        "success": success and pdf_path.exists(),
        "page_count": page_count,
        "fill": fill,
        "pdf_path": pdf_path if pdf_path.exists() else None,
        "log": log,
    }
