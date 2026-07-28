"""Guard the checked-in fictional example so it can never silently rot.

`master.example.yaml` + `docs/sample/instance.yaml` are what a fresh clone runs
to see the pipeline work without any private data, and what the README/portfolio
point at. If a schema or content change breaks them, these deterministic
(no-Docker) checks fail in CI. The actual one-page *render* is proven by the
checked-in `docs/sample/resume.pdf`; here we lock in that the example is
structurally sound and the sample instance validates verbatim against it.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import validate as v  # noqa: E402
import coverage as cov  # noqa: E402

MASTER = REPO_ROOT / "master.example.yaml"
INSTANCE = REPO_ROOT / "docs" / "sample" / "instance.yaml"
JD = REPO_ROOT / "docs" / "sample" / "job_description.txt"
SCHEMA = REPO_ROOT / "schema" / "instance.schema.json"


@pytest.fixture(scope="module")
def master():
    return v.load_yaml(MASTER)


@pytest.fixture(scope="module")
def instance():
    return v.load_yaml(INSTANCE)


def test_example_master_has_expected_shape(master):
    # The four profiles the tailor/prompt rely on.
    assert set(master["profiles"]) == {"bd", "pm", "dm", "general"}
    # A summaries bank keyed by profile, at least the neutral general one.
    profiles_with_summary = {s["profile"] for s in master["summaries"]}
    assert "general" in profiles_with_summary
    # Exactly one additional:true role (the overflow-first, lowest-priority one).
    additional = [e for e in master["experience"] if e.get("additional")]
    assert len(additional) == 1
    # Bullets carry per-profile variants (this is what makes tailoring possible).
    a_bullet = master["experience"][0]["bullets"][0]
    assert "variants" in a_bullet and a_bullet["variants"]


def test_example_master_carries_no_real_pii(master):
    # Cheap tripwire: the fictional persona must never accidentally inherit the
    # real bank's identity if someone copy-pastes into this file.
    blob = str(master).lower()
    assert "555" in master["meta"]["phone"]  # 555 = non-dialable, safe demo range
    assert master["meta"]["email"].endswith("@example.com")
    assert "chantamas" not in blob


def test_sample_instance_validates_against_example(master, instance):
    schema = v.load_json(SCHEMA)
    errors = v.validate(instance, master, schema)
    assert errors == [], f"sample instance failed validation: {errors}"


def test_sample_is_coherent_for_its_jd(master, instance):
    # The sample is a pm-profile selection; the deterministic screen should agree
    # the JD rewards pm, and the resume should cover a solid share of JD terms.
    jd_text = JD.read_text(encoding="utf-8")
    report = cov.coverage_report(jd_text, instance, master)
    assert report["profile"]["suggested"] == "pm"
    assert report["score"] >= 0.4
