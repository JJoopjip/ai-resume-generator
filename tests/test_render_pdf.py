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


# --- experience grouping + ordering (deterministic, no LaTeX needed) --------

def _role(id_, start, end, **extra):
    return {"id": id_, "start": start, "end": end, **extra}


def test_roles_are_reverse_chronological_regardless_of_input_order():
    # The 2026-09-28 Lilly render put a May 2026 role below a 2017 one because
    # part-time roles were forced after full-time ones. Order is by date now.
    roles = [
        _role("otsuka", "Jul 2017", "Mar 2019"),
        _role("festival", "May 2026", "Present", part_time=True),
        _role("winnergy", "Aug 2022", "Oct 2023"),
        _role("lgchem", "Apr 2019", "Oct 2021"),
    ]
    ordered = r.order_reverse_chronological(roles)
    assert [e["id"] for e in ordered] == ["festival", "winnergy", "lgchem", "otsuka"]


def test_ongoing_role_sorts_first_and_ties_break_on_start():
    roles = [
        _role("older_start", "Jan 2020", None),
        _role("ended", "Jan 2024", "Dec 2025"),
        _role("newer_start", "Jan 2023", "Present"),
    ]
    ordered = r.order_reverse_chronological(roles)
    assert [e["id"] for e in ordered] == ["newer_start", "older_start", "ended"]


def test_year_only_and_unparseable_dates_never_raise():
    roles = [_role("weird", "sometime", "later"), _role("year", "2024", "2026")]
    assert [e["id"] for e in r.order_reverse_chronological(roles)] == ["year", "weird"]


def test_group_experience_follows_section_list_and_drops_empty_sections():
    instance = {
        "experience_sections": [
            {"id": "industry", "heading": "Industry"},
            {"id": "pharmacy", "heading": "Pharmacy"},
            {"id": "volunteer", "heading": "Volunteer"},
        ],
        "experience": [
            _role("boots", "Sep 2021", "Aug 2024", section="pharmacy"),
            _role("otsuka", "Jul 2017", "Mar 2019", section="industry"),
            _role("winnergy", "Aug 2022", "Oct 2023", section="industry"),
        ],
    }
    groups = r.group_experience(instance)
    assert [g["heading"] for g in groups] == ["Industry", "Pharmacy"]
    assert [e["id"] for e in groups[0]["roles"]] == ["winnergy", "otsuka"]


def test_group_experience_legacy_instance_uses_default_sections():
    # Instances written before sections existed still render as before:
    # "Experience", then "Additional Experience" for additional: true roles.
    instance = {"experience": [
        _role("server", "Jan 2025", "Jun 2026", additional=True),
        _role("winnergy", "Aug 2022", "Oct 2023"),
    ]}
    groups = r.group_experience(instance)
    assert [(g["heading"], [e["id"] for e in g["roles"]]) for g in groups] == [
        ("Experience", ["winnergy"]),
        ("Additional Experience", ["server"]),
    ]
