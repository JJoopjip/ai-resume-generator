"""Tests for the pure parts of the eval harness (label derivation and report
building). The live A/B path launches paid Claude sessions, so it is exercised
only via --dry-run manually, never in tests."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import eval_run  # noqa: E402


def test_derive_label_from_flags():
    assert eval_run.derive_label("--model claude-sonnet-5 --effort medium", "a") == "sonnet-5-medium"
    assert eval_run.derive_label("--model claude-opus-4-8 --effort high", "b") == "opus-4-8-high"
    assert eval_run.derive_label("--effort low", "a") == "low"
    assert eval_run.derive_label("", "b") == "b"


def _stub_arm(label: str) -> eval_run.Arm:
    arm = eval_run.Arm(label, f"--model {label}")
    arm.run_dir = Path(f"output/acme-{label}")
    arm.seconds = 125.0
    arm.render = {
        "page_count": 1,
        "fit": {"lines_free": 3},
        "coverage": {
            "score": 0.4, "terms_covered": 10, "terms_total": 25,
            "selection_gap": ["x"], "content_gap": ["y", "z"],
            "profile": {"suggested": "bd"},
            "depth": {"bullets_selected": 9, "bullets_available": 20,
                      "roles_selected": 3, "roles_available": 4},
        },
    }
    arm.cost = {"cost_usd": 1.234, "totals": {"total_tokens": 456_000}, "assistant_turns": 42}
    return arm


def test_report_renders_all_metrics():
    arms = [_stub_arm("fast"), _stub_arm("slow")]
    md = eval_run.render_report(arms, Path("jd.txt"), judge_note=None)
    assert "| metric | fast | slow |" in md
    assert "40% (10/25)" in md
    assert "1.23" in md          # cost
    assert "456k" in md          # tokens
    assert "2m05s" in md         # wall time
    assert "⚠" not in md         # no error rows for healthy arms


def test_report_survives_missing_data():
    """A failed arm (no render JSON, no cost.json) must yield n/a cells and an
    error callout, never a crash — the report is how failures get seen."""
    ok, broken = _stub_arm("ok"), eval_run.Arm("broken", "--model x")
    broken.error = "tailor run exited 1 and no output appeared"
    md = eval_run.render_report([ok, broken], Path("jd.txt"), judge_note=None)
    assert "n/a" in md
    assert "⚠ arm **broken**" in md
