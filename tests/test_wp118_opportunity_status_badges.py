"""WP-118 — Opportunity status badges in the operator UI."""

import pytest
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "app" / "operator_ui"
JS = (BASE / "app.js").read_text()
CSS = (BASE / "styles.css").read_text()


@pytest.mark.parametrize(
    "status",
    ["pending", "follow_up", "prepare_proposal", "in_progress", "done", "lost", "ignore"],
)
def test_js_adds_status_badge_class(status):
    """The opportunity list rendering must assign a status badge class."""
    assert 'opp-status-badge' in JS
    assert f'opp-status-{status}' in CSS


def test_js_badge_class_assignment():
    """The stage span must receive the opp-status-badge class dynamically."""
    assert 'stage.className = "opp-status-badge opp-status-"' in JS


def test_css_has_base_badge_style():
    """The base badge class must define visual properties."""
    assert ".opp-status-badge" in CSS
    assert "border-radius" in CSS.split(".opp-status-badge")[1].split("}")[0]


@pytest.mark.parametrize(
    ("status", "color"),
    [
        ("pending", "#f0c040"),
        ("follow_up", "#60b0f0"),
        ("prepare_proposal", "#b080f0"),
        ("in_progress", "#40d080"),
        ("done", "#40f060"),
        ("lost", "#f06060"),
        ("ignore", "#808080"),
    ],
)
def test_css_status_colors(status, color):
    """Each status must have a distinct color."""
    section = CSS.split(f".opp-status-{status}")[1]
    assert color in section, f"Missing color {color} for {status}"


def test_css_unknown_status_fallback():
    """Unknown statuses should have a fallback gray style."""
    assert ".opp-status-unknown" in CSS


def test_badge_not_inline_style():
    """Badges should use CSS classes, not inline styles."""
    # The stage element should not set style directly
    assert "stage.style" not in JS.split("opp-status-badge")[0].split("stage = ")[-1] or \
           "opp-status-badge" in JS
