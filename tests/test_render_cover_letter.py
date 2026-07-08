import sys
from pathlib import Path

import yaml

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import render_cover_letter as rcl  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load(name):
    return yaml.safe_load((FIXTURES / name).read_text(encoding="utf-8"))


def _letter():
    return _load("cover_letter.example.yaml")


def _meta():
    return _load("instance.example.yaml")["meta"]


# ---- validate_letter --------------------------------------------------------

def test_validate_letter_accepts_example():
    assert rcl.validate_letter(_letter()) == []


def test_validate_letter_flags_each_missing_required_field():
    for field in ("date", "salutation", "paragraphs", "signoff"):
        letter = _letter()
        del letter[field]
        errors = rcl.validate_letter(letter)
        assert any(field in e for e in errors), field


def test_validate_letter_rejects_too_many_paragraphs():
    letter = _letter()
    letter["paragraphs"] = ["p"] * 6
    errors = rcl.validate_letter(letter)
    assert any("paragraph" in e for e in errors)


# ---- render_tex -------------------------------------------------------------

def test_render_tex_letterhead_comes_from_meta(tmp_path):
    tex = rcl.render_tex(_letter(), _meta(), tmp_path,
                         rcl.DEFAULT_LETTER_LAYOUT).read_text(encoding="utf-8")
    # Letterhead is built from instance meta, not from the letter body.
    assert "Jordan Sample" in tex
    assert "jordan@example.com" in tex
    assert "linkedin.com/in/jordansample" in tex


def test_render_tex_includes_body_and_recipient(tmp_path):
    tex = rcl.render_tex(_letter(), _meta(), tmp_path,
                         rcl.DEFAULT_LETTER_LAYOUT).read_text(encoding="utf-8")
    assert "Example Analyst opening" in tex     # a body paragraph
    assert "Example Corp" in tex                 # recipient company
    assert "Dear Hiring Team," in tex            # salutation
    assert "Sincerely," in tex                   # signoff


def test_render_tex_escapes_latex_special_chars(tmp_path):
    tex = rcl.render_tex(_letter(), _meta(), tmp_path,
                         rcl.DEFAULT_LETTER_LAYOUT).read_text(encoding="utf-8")
    # Raw "100%" / "R&D" would break the LaTeX compile; they must be escaped.
    assert r"100\%" in tex and "100%" not in tex.replace(r"100\%", "")
    assert r"R\&D" in tex


# ---- page-count parsing -----------------------------------------------------

def test_extract_page_count_reads_lastpage_macro(tmp_path):
    (tmp_path / "cover_letter.aux").write_text(
        r"\xdef\lastpage@lastpage{1}", encoding="utf-8")
    assert rcl._extract_page_count(tmp_path) == 1


def test_extract_page_count_none_when_absent(tmp_path):
    assert rcl._extract_page_count(tmp_path) is None
