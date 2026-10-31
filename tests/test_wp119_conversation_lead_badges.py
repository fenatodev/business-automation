"""WP-119 — Status badges for conversations and leads in the operator UI."""

import pytest
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "app" / "operator_ui"
JS = (BASE / "app.js").read_text()
CSS = (BASE / "styles.css").read_text()


# --- Conversation badges ---

def test_js_adds_conversation_status_badge_class():
    """The conversation list must assign a status badge class."""
    assert 'conv-status-badge' in JS
    assert 'conv-status-' in JS


@pytest.mark.parametrize(
    ("status", "color"),
    [
        ("open", "#40d080"),
        ("closed", "#808080"),
    ],
)
def test_css_conversation_status_colors(status, color):
    """Each conversation status must have a distinct color."""
    section = CSS.split(f".conv-status-{status}")[1]
    assert color in section, f"Missing color {color} for conversation status {status}"


def test_css_conversation_unknown_fallback():
    """Unknown conversation statuses should have a fallback gray style."""
    assert ".conv-status-unknown" in CSS


def test_css_has_conversation_badge_base_style():
    """The base conversation badge class must define visual properties."""
    assert ".conv-status-badge" in CSS
    assert "border-radius" in CSS.split(".conv-status-badge")[1].split("}")[0]


# --- Lead badges ---

def test_js_adds_lead_status_badge_class():
    """The lead list must assign a status badge class."""
    assert 'lead-status-badge' in JS
    assert 'lead-status-' in JS


@pytest.mark.parametrize(
    ("status", "color"),
    [
        ("new", "#60b0f0"),
        ("contacted", "#f0c040"),
        ("qualified", "#b080f0"),
        ("lost", "#f06060"),
        ("won", "#40f060"),
    ],
)
def test_css_lead_status_colors(status, color):
    """Each lead status must have a distinct color."""
    section = CSS.split(f".lead-status-{status}")[1]
    assert color in section, f"Missing color {color} for lead status {status}"


def test_css_lead_unknown_fallback():
    """Unknown lead statuses should have a fallback gray style."""
    assert ".lead-status-unknown" in CSS


def test_css_has_lead_badge_base_style():
    """The base lead badge class must define visual properties."""
    assert ".lead-status-badge" in CSS
    assert "border-radius" in CSS.split(".lead-status-badge")[1].split("}")[0]


# --- Opportunity badges (WP-118 included for completeness) ---

def test_css_has_opportunity_badge_base_style():
    """The base opportunity badge class must define visual properties."""
    assert ".opp-status-badge" in CSS


@pytest.mark.parametrize(
    ("status", "color"),
    [
        ("pending", "#f0c040"),
        ("in_progress", "#40d080"),
        ("done", "#40f060"),
        ("lost", "#f06060"),
    ],
)
def test_css_opportunity_status_colors(status, color):
    """Each opportunity status must have a distinct color."""
    section = CSS.split(f".opp-status-{status}")[1]
    assert color in section, f"Missing color {color} for opportunity status {status}"
