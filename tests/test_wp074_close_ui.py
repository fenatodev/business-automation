"""Contract checks for the WP-074 opportunity close UI options.

Validates that done and lost options are properly wired in the triage form.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "app/operator_ui/index.html").read_text()
JS = (ROOT / "app/operator_ui/app.js").read_text()


def test_triage_select_has_done_option():
    """The triage select includes done as an option."""
    assert '<option value="done">' in HTML


def test_triage_select_has_lost_option():
    """The triage select includes lost as an option."""
    assert '<option value="lost">' in HTML


def test_done_label():
    """The done option has the correct Portuguese label."""
    assert 'Concluída' in HTML


def test_lost_label():
    """The lost option has the correct Portuguese label."""
    assert 'Perdida' in HTML


def test_done_comes_after_in_progress():
    """done appears after in_progress in the select."""
    in_progress_idx = HTML.index('value="in_progress"')
    done_idx = HTML.index('value="done"')
    assert done_idx > in_progress_idx


def test_lost_comes_after_done():
    """lost appears after done in the select."""
    done_idx = HTML.index('value="done"')
    lost_idx = HTML.index('value="lost"')
    assert lost_idx > done_idx


def test_done_in_action_labels():
    """done is included in actionLabels for display."""
    assert 'done: "Concluída"' in JS


def test_lost_in_action_labels():
    """lost is included in actionLabels for display."""
    assert 'lost: "Perdida"' in JS
