"""Contract checks for the WP-073 triage in_progress UI option.

Validates that the in_progress option is properly wired in the triage form.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "app/operator_ui/index.html").read_text()
JS = (ROOT / "app/operator_ui/app.js").read_text()


def test_triage_select_has_in_progress_option():
    """The triage select includes in_progress as an option."""
    assert '<option value="in_progress">' in HTML


def test_triage_select_in_progress_label():
    """The in_progress option has the correct Portuguese label."""
    assert 'Em andamento' in HTML


def test_triage_select_order():
    """in_progress appears after prepare_proposal in the select."""
    prepare_idx = HTML.index('value="prepare_proposal"')
    in_progress_idx = HTML.index('value="in_progress"')
    assert in_progress_idx > prepare_idx


def test_in_progress_in_action_labels():
    """in_progress is included in actionLabels for display."""
    assert 'in_progress: "Em andamento"' in JS


def test_triage_form_submits_to_correct_endpoint():
    """Triage form submits to the opportunities triage endpoint."""
    assert '"/opportunities/' in JS
    assert '/triage' in JS


def test_triage_uses_next_action_field():
    """Triage uses the next_action value from the select."""
    assert 'next_action' in JS
    assert '$("next-action")' in JS
