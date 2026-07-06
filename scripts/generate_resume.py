#!/usr/bin/env python3
"""CLI entrypoint: `resume-gen render` / `resume-gen validate`.

Per TECH_SPEC.md §1-2: always emits exactly one JSON object to stdout
(nothing else on stdout), with a stable exit-code contract so a calling
Claude Code session can branch on the exit code alone:

  0  success (validate: schema+verbatim valid; render: valid AND 1 page)
  1  validation failure (schema, locked-field, bullet-verbatim, or layout
     out-of-range mismatch)
  2  render/compile error (Tectonic failure, template error, docx-write error)
  3  page overflow (validated and rendered fine, but page count > 1)
  4  usage error (missing/unreadable file, bad arguments)
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import validate as validate_mod  # noqa: E402
import render_pdf  # noqa: E402
import render_docx  # noqa: E402

DEFAULT_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema" / "instance.schema.json"
DEFAULT_LAYOUT_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema" / "layout.schema.json"

EXIT_SUCCESS = 0
EXIT_VALIDATION_FAILURE = 1
EXIT_RENDER_ERROR = 2
EXIT_OVERFLOW = 3
EXIT_USAGE_ERROR = 4


def _emit(command: str, valid: bool, errors: list[dict], page_count, output_files) -> None:
    payload = {
        "command": command,
        "valid": valid,
        "errors": errors,
        "page_count": page_count,
        "output_files": output_files,
    }
    print(json.dumps(payload), flush=True)


def _log(msg: str) -> None:
    """Human-readable progress to stderr. stdout stays a single JSON object
    (the machine contract), so all of this is safe to interleave — a caller
    parsing stdout never sees it, a human watching the terminal always does."""
    print(f"  resume-gen │ {msg}", file=sys.stderr, flush=True)


def _usage_error(command: str, message: str) -> int:
    _log(f"✗ usage error: {message}")
    _emit(
        command,
        False,
        [{"code": "usage_error", "id": None, "field": None, "expected": None,
          "actual": None, "message": message}],
        None,
        None,
    )
    return EXIT_USAGE_ERROR


def _load_inputs(instance_path: str, master_path: str, schema_path: str):
    instance = validate_mod.load_yaml(instance_path)
    master = validate_mod.load_yaml(master_path)
    schema = validate_mod.load_json(schema_path)
    return instance, master, schema


def cmd_validate(args: argparse.Namespace) -> int:
    _log(f"▶ validate  ·  instance: {args.instance}")
    _log(f"      loading master ({args.master}) + instance …")
    try:
        instance, master, schema = _load_inputs(args.instance, args.master, args.schema)
    except (FileNotFoundError, OSError) as e:
        return _usage_error("validate", f"Could not read input file: {e}")
    except Exception as e:  # yaml/json parse errors, etc.
        return _usage_error("validate", f"Could not parse input file: {e}")

    _log("      checking locked fields + verbatim bullets …")
    errors = validate_mod.validate(instance, master, schema)
    valid = not errors
    if valid:
        _log("✓ valid")
    else:
        _log(f"✗ {len(errors)} error(s); see JSON on stdout")
    _emit("validate", valid, errors, None, None)
    return EXIT_SUCCESS if valid else EXIT_VALIDATION_FAILURE


def _resolve_instance(path: str | None) -> tuple[str | None, str | None]:
    """--instance is optional: when omitted, use the most recently modified
    output/*/instance.yaml (i.e. the resume you just tailored), else a plain
    ./instance.yaml. Returns (path, error_message)."""
    if path:
        return path, None
    out_dir = Path("output")
    if out_dir.is_dir():
        candidates = sorted(
            out_dir.glob("*/instance.yaml"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        if candidates:
            return str(candidates[0]), None
    if Path("instance.yaml").is_file():
        return "instance.yaml", None
    return None, (
        "No --instance given and nothing to default to "
        "(looked for output/*/instance.yaml and ./instance.yaml)."
    )


def cmd_render(args: argparse.Namespace) -> int:
    instance_path, resolve_err = _resolve_instance(args.instance)
    if resolve_err:
        return _usage_error("render", resolve_err)
    args.instance = instance_path
    _log(f"▶ render  ·  instance: {instance_path}")
    _log(f"[1/4] loading master ({args.master}) + instance …")
    try:
        instance, master, schema = _load_inputs(args.instance, args.master, args.schema)
        layout_schema = validate_mod.load_json(args.layout_schema)
        layout_overrides = validate_mod.load_yaml(args.layout) if args.layout else {}
    except (FileNotFoundError, OSError) as e:
        return _usage_error("render", f"Could not read input file: {e}")
    except Exception as e:
        return _usage_error("render", f"Could not parse input file: {e}")

    layout_errors = validate_mod.validate_layout(layout_overrides, layout_schema)
    if layout_errors:
        _log(f"✗ layout out of bounds ({len(layout_errors)} issue(s))")
        _emit("render", False, layout_errors, None, None)
        return EXIT_VALIDATION_FAILURE
    layout = {**validate_mod.default_layout(layout_schema), **layout_overrides}

    _log("[2/4] validating instance against master (locked fields, verbatim bullets) …")
    errors = validate_mod.validate(instance, master, schema)
    if errors:
        _log(f"✗ validation failed — {len(errors)} error(s); see JSON on stdout")
        _emit("render", False, errors, None, None)
        return EXIT_VALIDATION_FAILURE
    _log("      ✓ valid")

    # --out defaults to the instance file's own directory (the normal
    # output/<company>-<role>-<date>/ folder), so a plain
    # `render --instance <path>` writes the PDF/DOCX right beside it.
    out_dir = Path(args.out) if args.out else Path(args.instance).resolve().parent
    _log(f"[3/4] rendering + compiling PDF ({layout['font_size_pt']}pt / "
         f"{layout['margin_in']}in) → {out_dir}/ …")
    try:
        pdf_result = render_pdf.render_pdf(instance, out_dir, layout)
    except Exception:
        _emit(
            "render",
            True,
            [{"code": "render_error", "id": None, "field": None, "expected": None,
              "actual": None, "message": f"PDF render raised an exception:\n{traceback.format_exc()}"}],
            None,
            None,
        )
        return EXIT_RENDER_ERROR

    if not pdf_result["success"] or pdf_result["page_count"] is None:
        _log("✗ PDF compile failed (Tectonic); see JSON on stdout for the log tail")
        _emit(
            "render",
            True,
            [{"code": "render_error", "id": None, "field": None, "expected": None,
              "actual": None, "message": pdf_result["log"][-4000:]}],
            None,
            None,
        )
        return EXIT_RENDER_ERROR

    _log(f"      ✓ PDF compiled — {pdf_result['page_count']} page(s)")
    _log("[4/4] writing DOCX …")
    try:
        docx_path = render_docx.render_docx(instance, out_dir)
    except Exception:
        _emit(
            "render",
            True,
            [{"code": "render_error", "id": None, "field": None, "expected": None,
              "actual": None, "message": f"DOCX render raised an exception:\n{traceback.format_exc()}"}],
            None,
            None,
        )
        return EXIT_RENDER_ERROR

    output_files = {"pdf": str(pdf_result["pdf_path"]), "docx": str(docx_path)}
    page_count = pdf_result["page_count"]

    if page_count > 1:
        _log(f"⚠ OVERFLOW — {page_count} pages (exit 3). Drop the lowest-priority "
             "bullet and re-run.")
        _emit("render", True, [], page_count, output_files)
        return EXIT_OVERFLOW

    _log(f"✓ done — 1 page.  PDF: {output_files['pdf']}")
    _log(f"                  DOCX: {output_files['docx']}")
    _emit("render", True, [], page_count, output_files)
    return EXIT_SUCCESS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="resume-gen")
    # Bare `resume-gen` (no subcommand) defaults to render with all defaults, so
    # the minimal invocation is just `resume-gen`.
    parser.set_defaults(
        func=cmd_render,
        subcommand="render",
        instance=None,
        master="master.yaml",
        out=None,
        schema=str(DEFAULT_SCHEMA_PATH),
        layout=None,
        layout_schema=str(DEFAULT_LAYOUT_SCHEMA_PATH),
    )
    subparsers = parser.add_subparsers(dest="subcommand")

    render_p = subparsers.add_parser("render")
    render_p.add_argument("--instance", default=None,
                          help="path to instance.yaml (default: newest output/*/instance.yaml)")
    render_p.add_argument("--master", default="master.yaml",
                          help="path to master.yaml (default: ./master.yaml)")
    render_p.add_argument("--out", default=None,
                          help="output directory (default: the instance file's own folder)")
    render_p.add_argument("--schema", default=str(DEFAULT_SCHEMA_PATH))
    render_p.add_argument(
        "--layout",
        default=None,
        help="Optional path to a layout.json/.yaml overriding font_size_pt/margin_in "
        "within schema/layout.schema.json's bounds. Omit for the tightened default "
        "(10.5pt / 0.5in).",
    )
    render_p.add_argument("--layout-schema", default=str(DEFAULT_LAYOUT_SCHEMA_PATH))
    render_p.set_defaults(func=cmd_render)

    validate_p = subparsers.add_parser("validate")
    validate_p.add_argument("--instance", required=True)
    validate_p.add_argument("--master", default="master.yaml",
                            help="path to master.yaml (default: ./master.yaml)")
    validate_p.add_argument("--schema", default=str(DEFAULT_SCHEMA_PATH))
    validate_p.set_defaults(func=cmd_validate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        # argparse writes its own usage message to stderr; normalize the exit
        # code to the contract's usage-error code (4) instead of argparse's 2.
        return EXIT_USAGE_ERROR if e.code not in (0, None) else EXIT_SUCCESS
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
