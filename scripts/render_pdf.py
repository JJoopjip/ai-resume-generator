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


def render_pdf(instance: dict, out_dir: Path, layout: dict) -> dict:
    """Full pipeline: render .tex, compile, extract page count.

    Returns {"success": bool, "page_count": int | None, "pdf_path": Path | None,
    "log": str}.
    """
    tex_path = render_tex(instance, out_dir, layout)
    success, log = compile_tex(tex_path)
    pdf_path = out_dir / "resume.pdf"
    page_count = extract_page_count(out_dir) if success else None
    return {
        "success": success and pdf_path.exists(),
        "page_count": page_count,
        "pdf_path": pdf_path if pdf_path.exists() else None,
        "log": log,
    }
