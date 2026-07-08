"""Deterministic, no-LLM validation of instance.yaml against master.yaml.

Implements PRD.md §7 and TECH_SPEC.md §3:
  1. schema_version match (checked before anything else)
  2. JSON Schema structural check (instance.schema.json)
  3. Locked-field verbatim check (experience/education/certifications)
  4. Bullet-verbatim check (instance bullet text must equal some
     variants[*] value for that bullet id in master.yaml)
  5. Skills subset check
  6. priority_order cross-field check (same bullet-id set as `bullets`)

Returns a list of error dicts matching the stdout contract in TECH_SPEC.md §2:
  {code, id, field, expected, actual, message}
`code` is one of: schema_error, locked_field_mismatch, bullet_not_verbatim,
unknown_id, layout_invalid.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import jsonschema
import yaml


# Cosmetic character folds and collapsed whitespace. Applied to BOTH sides of a
# string comparison so that a bullet the model copied with a smart quote, an
# em-dash swapped for a hyphen, an NBSP, or a doubled space still matches its
# master.yaml source. This only forgives *typographic* drift — every letter,
# digit, and word is preserved, so a genuinely rewritten fact ("supported" →
# "led", "90%" → "95%") still fails. The point is to spend overflow-loop
# attempts on real trims, not on invisible whitespace/quote diffs.
_COSMETIC_MAP = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "…": "...", " ": " ",
}
_WS_RE = re.compile(r"\s+")


def _normalize(value: Any) -> Any:
    """Fold cosmetic typography and collapse whitespace for comparison only.
    Non-strings pass through untouched (so None/bool/number compares stay exact)."""
    if not isinstance(value, str):
        return value
    value = unicodedata.normalize("NFC", value)
    value = value.translate(str.maketrans(_COSMETIC_MAP))
    return _WS_RE.sub(" ", value).strip()


def load_yaml(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_json(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _error(code: str, message: str, **kwargs: Any) -> dict:
    err = {"code": code, "id": None, "field": None, "expected": None, "actual": None}
    err.update(kwargs)
    err["message"] = message
    return err


# Fields on an experience entry that must string-match master.yaml verbatim
# when present (company/location/title/start/end are required; the rest are
# optional passthrough fields per TECH_SPEC §3).
EXPERIENCE_LOCKED_FIELDS = [
    "company",
    "location",
    "title",
    "start",
    "end",
    "multinational",
    "multinational_note",
    "part_time",
    "concurrent",
    "additional",
]

EDUCATION_LOCKED_FIELDS = ["institution", "location", "degree", "detail", "start", "end", "anchor"]

CERTIFICATION_LOCKED_FIELDS = ["name"]


def _index_by_id(entries: list[dict]) -> dict[str, dict]:
    return {entry["id"]: entry for entry in entries}


def validate_schema_version(instance: dict, master: dict) -> list[dict]:
    instance_version = instance.get("schema_version")
    master_version = master.get("schema_version")
    if instance_version != master_version:
        return [
            _error(
                "schema_error",
                f"instance schema_version {instance_version!r} does not match "
                f"master.yaml schema_version {master_version!r}.",
                field="schema_version",
                expected=master_version,
                actual=instance_version,
            )
        ]
    return []


def validate_structure(instance: dict, schema: dict) -> list[dict]:
    validator = jsonschema.Draft202012Validator(schema)
    errors = []
    for err in sorted(validator.iter_errors(instance), key=lambda e: list(e.path)):
        path = "/".join(str(p) for p in err.path) or "<root>"
        errors.append(
            _error(
                "schema_error",
                f"{path}: {err.message}",
                field=path,
            )
        )
    return errors


def _check_locked_fields(
    kind: str,
    entry_id: str,
    instance_entry: dict,
    master_entry: dict,
    fields: list[str],
) -> list[dict]:
    errors = []
    for field in fields:
        if field not in instance_entry:
            continue
        expected = master_entry.get(field)
        actual = instance_entry.get(field)
        if _normalize(actual) != _normalize(expected):
            errors.append(
                _error(
                    "locked_field_mismatch",
                    f"Locked field {field!r} on {kind} id {entry_id!r} does not "
                    f"match master.yaml.",
                    id=entry_id,
                    field=field,
                    expected=expected,
                    actual=actual,
                )
            )
    return errors


def validate_experience(instance: dict, master: dict) -> list[dict]:
    errors = []
    master_exp_by_id = _index_by_id(master.get("experience", []))

    for exp in instance.get("experience", []):
        exp_id = exp.get("id")
        master_exp = master_exp_by_id.get(exp_id)
        if master_exp is None:
            errors.append(
                _error(
                    "unknown_id",
                    f"Experience id {exp_id!r} is not present in master.yaml.",
                    id=exp_id,
                    field="experience.id",
                )
            )
            continue

        errors.extend(
            _check_locked_fields("experience", exp_id, exp, master_exp, EXPERIENCE_LOCKED_FIELDS)
        )

        master_bullets_by_id = _index_by_id(master_exp.get("bullets", []))
        for bullet in exp.get("bullets", []):
            bullet_id = bullet.get("id")
            master_bullet = master_bullets_by_id.get(bullet_id)
            if master_bullet is None:
                errors.append(
                    _error(
                        "unknown_id",
                        f"Bullet id {bullet_id!r} is not present under experience "
                        f"{exp_id!r} in master.yaml.",
                        id=bullet_id,
                        field="bullets.id",
                    )
                )
                continue

            valid_texts = set(master_bullet.get("variants", {}).values())
            actual_text = bullet.get("text")
            valid_normalized = {_normalize(t) for t in valid_texts}
            if _normalize(actual_text) not in valid_normalized:
                errors.append(
                    _error(
                        "bullet_not_verbatim",
                        f"Bullet {bullet_id!r} text on experience {exp_id!r} does not "
                        f"match any variant in master.yaml.",
                        id=bullet_id,
                        field="text",
                        expected=sorted(valid_texts),
                        actual=actual_text,
                    )
                )
    return errors


def validate_education(instance: dict, master: dict) -> list[dict]:
    errors = []
    master_edu_by_id = _index_by_id(master.get("education", []))
    for edu in instance.get("education", []):
        edu_id = edu.get("id")
        master_edu = master_edu_by_id.get(edu_id)
        if master_edu is None:
            errors.append(
                _error(
                    "unknown_id",
                    f"Education id {edu_id!r} is not present in master.yaml.",
                    id=edu_id,
                    field="education.id",
                )
            )
            continue
        errors.extend(
            _check_locked_fields("education", edu_id, edu, master_edu, EDUCATION_LOCKED_FIELDS)
        )
    return errors


def validate_certifications(instance: dict, master: dict) -> list[dict]:
    errors = []
    master_cert_by_id = _index_by_id(master.get("certifications", []))
    for cert in instance.get("certifications", []):
        cert_id = cert.get("id")
        master_cert = master_cert_by_id.get(cert_id)
        if master_cert is None:
            errors.append(
                _error(
                    "unknown_id",
                    f"Certification id {cert_id!r} is not present in master.yaml.",
                    id=cert_id,
                    field="certifications.id",
                )
            )
            continue
        errors.extend(
            _check_locked_fields(
                "certifications", cert_id, cert, master_cert, CERTIFICATION_LOCKED_FIELDS
            )
        )
    return errors


def validate_skills(instance: dict, master: dict) -> list[dict]:
    errors = []
    items_by_label: dict[str, set[str]] = {}
    for group in master.get("skills", {}).values():
        items_by_label.setdefault(_normalize(group["label"]), set()).update(
            _normalize(i) for i in group["items"]
        )

    for skill_block in instance.get("skills", []):
        label = skill_block.get("label")
        valid_items = items_by_label.get(_normalize(label))
        if valid_items is None:
            errors.append(
                _error(
                    "unknown_id",
                    f"Skill label {label!r} does not match any group in master.yaml.",
                    id=label,
                    field="skills.label",
                )
            )
            continue
        for item in skill_block.get("items", []):
            if _normalize(item) not in valid_items:
                errors.append(
                    _error(
                        "unknown_id",
                        f"Skill item {item!r} under label {label!r} is not present "
                        f"in master.yaml.",
                        id=label,
                        field="skills.items",
                        expected=sorted(valid_items),
                        actual=item,
                    )
                )
    return errors


def validate_highlights(instance: dict, master: dict) -> list[dict]:
    """Each selected highlight must reference a master.highlights id and carry
    that entry's locked `value` and `label` verbatim (mirrors the bullet-verbatim
    rule for the impact line)."""
    errors = []
    master_hl_by_id = _index_by_id(master.get("highlights", []))
    for hl in instance.get("highlights", []):
        hl_id = hl.get("id")
        master_hl = master_hl_by_id.get(hl_id)
        if master_hl is None:
            errors.append(
                _error(
                    "unknown_id",
                    f"Highlight id {hl_id!r} is not present in master.yaml.",
                    id=hl_id,
                    field="highlights.id",
                )
            )
            continue
        for field in ("value", "label"):
            if _normalize(hl.get(field)) != _normalize(master_hl.get(field)):
                errors.append(
                    _error(
                        "locked_field_mismatch",
                        f"Locked field {field!r} on highlight id {hl_id!r} does "
                        f"not match master.yaml.",
                        id=hl_id,
                        field=field,
                        expected=master_hl.get(field),
                        actual=hl.get(field),
                    )
                )
    return errors


def validate_priority_order(instance: dict) -> list[dict]:
    errors = []
    experience = instance.get("experience", [])
    priority_order = instance.get("priority_order", {})

    exp_ids = {exp.get("id") for exp in experience}
    priority_ids = set(priority_order.keys())

    for missing in exp_ids - priority_ids:
        errors.append(
            _error(
                "schema_error",
                f"priority_order is missing role {missing!r} present in experience.",
                id=missing,
                field="priority_order",
            )
        )
    for extra in priority_ids - exp_ids:
        errors.append(
            _error(
                "schema_error",
                f"priority_order has role {extra!r} not present in experience.",
                id=extra,
                field="priority_order",
            )
        )

    for exp in experience:
        exp_id = exp.get("id")
        if exp_id not in priority_order:
            continue
        bullet_ids = [b.get("id") for b in exp.get("bullets", [])]
        priority_bullet_ids = priority_order[exp_id]

        if sorted(bullet_ids) != sorted(priority_bullet_ids) or len(bullet_ids) != len(
            set(bullet_ids)
        ) or len(priority_bullet_ids) != len(set(priority_bullet_ids)):
            errors.append(
                _error(
                    "schema_error",
                    f"priority_order[{exp_id!r}] must contain exactly the same "
                    f"bullet ids (each once) as experience[{exp_id!r}].bullets.",
                    id=exp_id,
                    field="priority_order",
                    expected=sorted(bullet_ids),
                    actual=sorted(priority_bullet_ids),
                )
            )
    return errors


def validate(instance: dict, master: dict, schema: dict) -> list[dict]:
    """Run all validation rules in order; short-circuits after schema_version
    and structural checks since later checks assume a well-shaped instance."""
    errors = validate_schema_version(instance, master)
    if errors:
        return errors

    errors = validate_structure(instance, schema)
    if errors:
        return errors

    errors = []
    errors.extend(validate_experience(instance, master))
    errors.extend(validate_education(instance, master))
    errors.extend(validate_certifications(instance, master))
    errors.extend(validate_skills(instance, master))
    errors.extend(validate_highlights(instance, master))
    errors.extend(validate_priority_order(instance))

    meta_expected = master.get("meta")
    meta_actual = instance.get("meta")
    if meta_actual != meta_expected:
        errors.append(
            _error(
                "locked_field_mismatch",
                "instance.meta does not deep-equal master.yaml meta.",
                field="meta",
                expected=meta_expected,
                actual=meta_actual,
            )
        )

    return errors


def validate_paths(instance_path: str | Path, master_path: str | Path, schema_path: str | Path):
    instance = load_yaml(instance_path)
    master = load_yaml(master_path)
    schema = load_json(schema_path)
    errors = validate(instance, master, schema)
    return not errors, errors


def default_layout(layout_schema: dict) -> dict:
    """Extracts the {field: default} map from layout.schema.json so a caller
    that supplies no --layout file gets the tightened baseline (currently
    font_size_pt: 10.0, margin_h_in: 0.4, margin_v_in: 0.3) without duplicating
    those numbers."""
    return {
        name: prop["default"]
        for name, prop in layout_schema.get("properties", {}).items()
        if "default" in prop
    }


def validate_layout(layout: dict, layout_schema: dict) -> list[dict]:
    """Range-checks layout.json against layout.schema.json (font_size_pt /
    margin_h_in / margin_v_in bounds). A violation is `layout_invalid`, same
    exit-1 bucket as other validation failures."""
    validator = jsonschema.Draft202012Validator(layout_schema)
    errors = []
    for err in sorted(validator.iter_errors(layout), key=lambda e: list(e.path)):
        path = "/".join(str(p) for p in err.path) or "<root>"
        errors.append(
            _error(
                "layout_invalid",
                f"{path}: {err.message}",
                field=path,
            )
        )
    return errors
