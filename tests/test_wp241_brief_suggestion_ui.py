"""WP-241/242 — AI-assisted brief suggestion UI.

The operator panel has a button to suggest brief content via AI
(POST /opportunities/{id}/suggest-brief, WP-240 backend).
When the operator clicks "Preencher brief", the form fields are
auto-filled with the suggestion.
"""

import pytest


@pytest.fixture
def js():
    with open("app/operator_ui/app.js") as f:
        return f.read()


@pytest.fixture
def html():
    with open("app/operator_ui/index.html") as f:
        return f.read()


# --- HTML structure ---


def test_suggest_brief_button_exists(html):
    """Button to suggest brief exists in opportunity detail actions."""
    assert 'id="suggest-brief-button"' in html


def test_suggest_brief_button_is_secondary(html):
    """The button uses secondary style."""
    assert 'id="suggest-brief-button" type="button" class="secondary"' in html


def test_brief_suggestion_panel_exists(html):
    """Panel for displaying brief suggestion exists."""
    assert 'id="brief-suggestion-panel"' in html


def test_brief_suggestion_panel_hidden_by_default(html):
    """The panel is hidden until suggestion is generated."""
    assert 'id="brief-suggestion-panel" class="triage-suggestion-panel" hidden' in html


def test_brief_suggestion_content_div_exists(html):
    """Content div for brief suggestion fields."""
    assert 'id="brief-suggestion-content"' in html


def test_apply_brief_suggestion_button_exists(html):
    """Button to apply brief suggestion to form."""
    assert 'id="apply-brief-suggestion-button"' in html


def test_dismiss_brief_suggestion_button_exists(html):
    """Button to dismiss brief suggestion."""
    assert 'id="dismiss-brief-suggestion-button"' in html


# --- JavaScript handlers ---


def test_suggest_brief_button_handler(js):
    """Click handler for suggest-brief-button calls the backend endpoint."""
    assert '"/opportunities/" + selectedId + "/suggest-brief"' in js
    assert '"POST"' in js


def test_brief_suggestion_state_variable(js):
    """briefSuggestion state variable exists."""
    assert "let briefSuggestion = null" in js


def test_brief_suggestion_panel_shown_on_success(js):
    """Panel is shown and scrolled into view on successful suggestion."""
    assert '"brief-suggestion-panel").hidden = false' in js


def test_brief_suggestion_503_handling(js):
    """503 error shows agent unavailable message."""
    assert "Serviço de agente indisponível" in js


def test_apply_brief_fills_offer_reference(js):
    """Apply button fills offer_reference field."""
    assert 'briefSuggestion.offer_reference' in js


def test_apply_brief_fills_diagnosis(js):
    """Apply button fills diagnosis field."""
    assert 'briefSuggestion.diagnosis' in js


def test_apply_brief_fills_scope(js):
    """Apply button fills scope field."""
    assert 'briefSuggestion.scope' in js


def test_apply_brief_fills_deliverables(js):
    """Apply button fills deliverables field."""
    assert 'briefSuggestion.deliverables' in js


def test_apply_brief_fills_acceptance_criteria(js):
    """Apply button fills acceptance_criteria field."""
    assert 'briefSuggestion.acceptance_criteria' in js


def test_apply_brief_fills_assumptions(js):
    """Apply button fills assumptions field."""
    assert 'briefSuggestion.assumptions' in js


def test_apply_brief_fills_risks(js):
    """Apply button fills risks field."""
    assert 'briefSuggestion.risks' in js


def test_apply_brief_shows_form(js):
    """Apply button shows the brief form."""
    assert '"brief-form").hidden = false' in js


def test_apply_brief_scrolls_to_panel(js):
    """Apply button scrolls to brief panel."""
    assert '"brief-panel").scrollIntoView' in js


def test_dismiss_brief_hides_panel(js):
    """Dismiss button hides the suggestion panel."""
    assert '"dismiss-brief-suggestion-button")' in js


def test_render_brief_suggestion_function_exists(js):
    """renderBriefSuggestion function renders all fields."""
    assert "function renderBriefSuggestion()" in js


def test_render_brief_uses_text_content(js):
    """Brief suggestion uses textContent/appendChild (XSS rule)."""
    assert "content.textContent = \"\"" in js


def test_clear_selection_resets_brief_suggestion(js):
    """clearSelection hides brief suggestion panel."""
    assert 'briefSuggestion = null' in js


def test_allowlist_includes_suggest_brief(js):
    """Allowlist regex includes suggest-brief endpoint."""
    assert "suggest-brief" in js


def test_no_opportunity_notification(js):
    """Notification when no opportunity is selected."""
    assert "Selecione uma oportunidade" in js


def test_brief_suggestion_notify_on_apply(js):
    """Notification when brief is filled from suggestion."""
    assert "Brief preenchido com a sugestão" in js
