"""Contract checks for the WP-058 operator review UI.

Keeps the static dashboard wired to the existing review API without introducing
remote URLs, client-side token storage or message-sending actions.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "app/operator_ui/index.html").read_text()
JS = (ROOT / "app/operator_ui/app.js").read_text()


def test_review_queue_form_present():
    for element_id in ("rq-form", "rq-event", "rq-message", "rq-channel",
                       "rq-list", "rq-count", "rq-refresh"):
        assert f'id="{element_id}"' in HTML


def test_review_queue_uses_authenticated_internal_api():
    assert '"/review-queue/"' in JS
    assert '"/review-queue/synthetic-trigger"' in JS
    assert '"/decision"' in JS
    assert 'Authorization: "Bearer " + bearer' in JS
    assert 'credentials: "omit"' in JS
    assert 'redirect: "error"' in JS


def test_review_queue_cannot_send_external_messages():
    assert "Nenhuma mensagem enviada." in JS
    assert "Simular entrada" in HTML
    assert "Aprovar internamente" in JS
    assert "window.open" not in JS
    assert "localStorage" not in JS
    assert "sessionStorage" not in JS


def test_review_queue_escapes_external_text():
    assert "heading.textContent =" in JS
    assert "message.textContent =" in JS
    assert "draft.textContent =" in JS
    assert "innerHTML" not in JS
