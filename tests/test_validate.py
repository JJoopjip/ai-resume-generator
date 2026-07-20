import copy
import json
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import validate as v  # noqa: E402

MASTER_PATH = REPO_ROOT / "master.yaml"
SCHEMA_PATH = REPO_ROOT / "schema" / "instance.schema.json"


@pytest.fixture(scope="module")
def master():
    if not MASTER_PATH.exists():
        pytest.skip("master.yaml is private and not checked in (fresh/CI checkout)")
    return v.load_yaml(MASTER_PATH)


@pytest.fixture(scope="module")
def schema():
    return v.load_json(SCHEMA_PATH)


def _valid_instance(master):
    """Build a minimal but fully valid instance.yaml from real master.yaml
    ids/strings so tests exercise the real content bank, not synthetic data."""
    winnergy = next(e for e in master["experience"] if e["id"] == "winnergy")
    lgchem = next(e for e in master["experience"] if e["id"] == "lgchem")

    def bullet(exp, bullet_id, profile):
        b = next(x for x in exp["bullets"] if x["id"] == bullet_id)
        return {"id": bullet_id, "text": b["variants"][profile]}

    winnergy_bullets = [
        bullet(winnergy, "win_b2c", "bd"),
        bullet(winnergy, "win_retention", "bd"),
    ]
    lgchem_bullets = [
        bullet(lgchem, "lg_sourcing", "bd"),
    ]

    instance_exp = [
        {
            "id": "winnergy",
            "company": winnergy["company"],
            "location": winnergy["location"],
            "title": winnergy["title"],
            "start": winnergy["start"],
            "end": winnergy["end"],
            "bullets": winnergy_bullets,
        },
        {
            "id": "lgchem",
            "company": lgchem["company"],
            "location": lgchem["location"],
            "title": lgchem["title"],
            "start": lgchem["start"],
            "end": lgchem["end"],
            "multinational": lgchem["multinational"],
            "multinational_note": lgchem["multinational_note"],
            "bullets": lgchem_bullets,
        },
    ]

    northeastern = next(e for e in master["education"] if e["id"] == "northeastern")
    pmp = next(e for e in master["certifications"] if e["id"] == "pmp")

    return {
        "schema_version": master["schema_version"] if "schema_version" in master else 1.0,
        "profile": "bd",
        "job_description_ref": "job_description.txt",
        "meta": master["meta"],
        "summary": "A tailored summary paragraph for this application.",
        "experience": instance_exp,
        "education": [
            {
                "id": "northeastern",
                "institution": northeastern["institution"],
                "location": northeastern["location"],
                "degree": northeastern["degree"],
                "detail": northeastern["detail"],
                "start": northeastern["start"],
                "end": northeastern["end"],
                "anchor": northeastern["anchor"],
            }
        ],
        "certifications": [{"id": "pmp", "name": pmp["name"]}],
        "skills": [
            {
                "label": "Business Development & Partnerships",
                "items": ["Partner sourcing & negotiation", "Channel development"],
            }
        ],
        "languages": [{"name": "Thai", "level": "native"}],
        "priority_order": {
            "winnergy": ["win_retention", "win_b2c"],
            "lgchem": ["lg_sourcing"],
        },
    }


@pytest.fixture
def valid_instance(master):
    # master.yaml has no top-level schema_version key at parse time in this
    # repo revision beyond the header comment; instance must match whatever
    # master provides (None==None passes) or the real key if present.
    return _valid_instance(master)


def test_valid_instance_passes(valid_instance, master, schema):
    errors = v.validate(valid_instance, master, schema)
    assert errors == []


def test_schema_version_mismatch(valid_instance, master, schema):
    instance = copy.deepcopy(valid_instance)
    instance["schema_version"] = 999.0
    errors = v.validate(instance, master, schema)
    assert len(errors) == 1
    assert errors[0]["code"] == "schema_error"
    assert errors[0]["field"] == "schema_version"


def test_locked_field_mismatch_on_title(valid_instance, master, schema):
    instance = copy.deepcopy(valid_instance)
    instance["experience"][0]["title"] = "Business Development Manager"
    errors = v.validate(instance, master, schema)
    codes = {e["code"] for e in errors}
    assert "locked_field_mismatch" in codes
    err = next(e for e in errors if e["code"] == "locked_field_mismatch")
    assert err["id"] == "winnergy"
    assert err["field"] == "title"


def test_bullet_not_verbatim(valid_instance, master, schema):
    instance = copy.deepcopy(valid_instance)
    instance["experience"][0]["bullets"][0]["text"] = "Rewrote this bullet entirely."
    errors = v.validate(instance, master, schema)
    assert any(e["code"] == "bullet_not_verbatim" for e in errors)


def test_bullet_verbatim_allows_any_profile_variant(valid_instance, master, schema):
    # win_engagement has bd/dm/pm/general variants; picking the dm wording for
    # a bd-labeled instance is allowed (profiles blend per-bullet).
    instance = copy.deepcopy(valid_instance)
    winnergy = next(e for e in master["experience"] if e["id"] == "winnergy")
    win_engagement = next(b for b in winnergy["bullets"] if b["id"] == "win_engagement")
    instance["experience"][0]["bullets"].append(
        {"id": "win_engagement", "text": win_engagement["variants"]["dm"]}
    )
    instance["priority_order"]["winnergy"].append("win_engagement")
    errors = v.validate(instance, master, schema)
    assert errors == []


def test_unknown_experience_id(valid_instance, master, schema):
    instance = copy.deepcopy(valid_instance)
    instance["experience"][0]["id"] = "not_a_real_company"
    instance["priority_order"] = {
        "not_a_real_company": ["win_retention", "win_b2c"],
        "lgchem": ["lg_sourcing"],
    }
    errors = v.validate(instance, master, schema)
    assert any(e["code"] == "unknown_id" and e["id"] == "not_a_real_company" for e in errors)


def test_unknown_bullet_id(valid_instance, master, schema):
    instance = copy.deepcopy(valid_instance)
    instance["experience"][0]["bullets"][0]["id"] = "win_does_not_exist"
    instance["priority_order"]["winnergy"] = ["win_does_not_exist", "win_retention"]
    errors = v.validate(instance, master, schema)
    assert any(e["code"] == "unknown_id" and e["id"] == "win_does_not_exist" for e in errors)


def test_skills_item_not_in_master(valid_instance, master, schema):
    instance = copy.deepcopy(valid_instance)
    instance["skills"][0]["items"].append("Made-up skill nobody has")
    errors = v.validate(instance, master, schema)
    assert any(e["code"] == "unknown_id" and e["field"] == "skills.items" for e in errors)


def test_priority_order_missing_bullet(valid_instance, master, schema):
    instance = copy.deepcopy(valid_instance)
    instance["priority_order"]["winnergy"] = ["win_retention"]  # drops win_b2c
    errors = v.validate(instance, master, schema)
    assert any(e["code"] == "schema_error" and e["id"] == "winnergy" for e in errors)


def test_priority_order_missing_role_key(valid_instance, master, schema):
    instance = copy.deepcopy(valid_instance)
    del instance["priority_order"]["lgchem"]
    errors = v.validate(instance, master, schema)
    assert any(e["code"] == "schema_error" and e["id"] == "lgchem" for e in errors)


def test_meta_mismatch(valid_instance, master, schema):
    instance = copy.deepcopy(valid_instance)
    instance["meta"] = copy.deepcopy(instance["meta"])
    instance["meta"]["email"] = "wrong@example.com"
    errors = v.validate(instance, master, schema)
    assert any(e["code"] == "locked_field_mismatch" and e["field"] == "meta" for e in errors)


def test_missing_required_field_fails_structure(valid_instance, master, schema):
    instance = copy.deepcopy(valid_instance)
    del instance["summary"]
    errors = v.validate(instance, master, schema)
    assert len(errors) == 1
    assert errors[0]["code"] == "schema_error"


# --- normalization: cosmetic typography must NOT trip verbatim checks ---------
def test_bullet_verbatim_tolerates_cosmetic_typography(valid_instance, master, schema):
    """A bullet copied with a smart apostrophe, an en-dash for a hyphen, and a
    doubled space is still the same fact — it must pass, not burn a render loop
    on invisible drift."""
    instance = copy.deepcopy(valid_instance)
    original = instance["experience"][0]["bullets"][0]["text"]
    mangled = (
        original.replace("'", "’")      # straight -> smart apostrophe
        .replace("modern-trade", "modern–trade")  # hyphen -> en dash
        .replace(", ", ",  ")                 # doubled space
        + " "                                  # trailing space
    )
    assert mangled != original
    instance["experience"][0]["bullets"][0]["text"] = mangled
    errors = v.validate(instance, master, schema)
    assert not any(e["code"] == "bullet_not_verbatim" for e in errors)


def test_bullet_real_rewrite_still_fails(valid_instance, master, schema):
    """Normalization only forgives typography — a changed word/number must still
    fail, or the guard is worthless."""
    instance = copy.deepcopy(valid_instance)
    original = instance["experience"][0]["bullets"][0]["text"]
    instance["experience"][0]["bullets"][0]["text"] = original.replace("four", "five")
    errors = v.validate(instance, master, schema)
    assert any(e["code"] == "bullet_not_verbatim" for e in errors)


def test_locked_field_tolerates_trailing_whitespace(valid_instance, master, schema):
    instance = copy.deepcopy(valid_instance)
    instance["experience"][0]["title"] = instance["experience"][0]["title"] + "  "
    errors = v.validate(instance, master, schema)
    assert not any(e["code"] == "locked_field_mismatch" for e in errors)
