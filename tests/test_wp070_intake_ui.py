"""Contract checks for the WP-070 intake commercial UI.

Validates that the intake section is properly wired to the commercial intake
create endpoint without introducing remote URLs, client-side token storage
or message-sending actions.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "app/operator_ui/index.html").read_text()
JS = (ROOT / "app/operator_ui/app.js").read_text()


def test_intake_form_present():
    """Intake form elements exist in the HTML."""
    for element_id in ("intake-form", "intake-channel", "intake-message",
                       "intake-event-id", "intake-result", "intake-status"):
        assert f'id="{element_id}"' in HTML


def test_intake_decision_display_present():
    """Decision display elements exist in the HTML."""
    for element_id in ("intake-decision-intent", "intake-decision-next",
                       "intake-decision-human", "intake-decision-flags",
                       "intake-decision-note"):
        assert f'id="{element_id}"' in HTML


def test_intake_uses_authenticated_internal_api():
    """Intake API calls use authenticated internal endpoint only."""
    assert '"/internal/commercial-intake/create"' in JS
    assert 'Authorization: "Bearer " + bearer' in JS
    assert 'credentials: "omit"' in JS
    assert 'referrerPolicy: "no-referrer"' in JS


def test_intake_cannot_send_external_messages():
    """Intake UI does not open external windows or store tokens."""
    assert "window.open" not in JS
    assert "localStorage" not in JS
    assert "sessionStorage" not in JS


def test_intake_handles_duplicate_and_service_errors():
    """Intake handler covers 409 (duplicate) and 503 (service unavailable)."""
    assert "409" in JS
    assert "503" in JS
    assert "já foi registrado" in JS or "registrado anteriormente" in JS


def test_intake_clears_on_disconnect():
    """Disconnect clears intake form and result."""
    assert "clearIntakeResult" in JS
    assert '$("intake-form").reset()' in JS


def test_intake_auto_selects_opportunity():
    """Successful intake refreshes list and selects the created opportunity."""
    assert "opportunity_id" in JS
    assert "refreshList" in JS


def test_intake_form_has_submit_button():
    """Intake form has a submit button with proper label."""
    assert "Avaliar e registrar" in HTML


def test_intake_section_has_proper_labeling():
    """Intake section is properly labeled for accessibility."""
    assert 'aria-labelledby="intake-title"' in HTML
    assert 'id="intake-title"' in HTML


def test_intake_decision_uses_text_content_not_inner_html():
    """Decision display uses textContent to avoid XSS."""
    assert "textContent" in JS
    # intake decision elements should use textContent
    assert 'intake-decision-intent' in JS
    assert "innerHTML" not in JS


def test_intake_api_has_strict_allowlist():
    """Intake API function validates route before fetching."""
    assert "intakeApi" in JS
    assert "/internal/commercial-intake/create" in JS
    # Check that intakeApi has its own allowlist regex
    assert "Rota de intake não permitida" in JS
