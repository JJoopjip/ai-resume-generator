import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import render_pdf as r  # noqa: E402


def test_tex_escape_special_chars():
    assert r.tex_escape("R&D") == r"R\&D"
    assert r.tex_escape("90%") == r"90\%"
    assert r.tex_escape("a_b") == r"a\_b"


def test_tex_escape_unicode_chars_used_in_master_yaml():
    # These render as blank/mojibake under plain T1 fontenc + XeTeX unless
    # explicitly mapped to a LaTeX text command (found via visual PDF review,
    # not by any compiler warning — Tectonic emits none for these).
    assert r.tex_escape("A · B") == r"A \textperiodcentered{} B"
    assert r.tex_escape("A — B") == r"A \textemdash{} B"


def test_tex_escape_non_string_passthrough():
    assert r.tex_escape(True) is True
    assert r.tex_escape(None) is None
