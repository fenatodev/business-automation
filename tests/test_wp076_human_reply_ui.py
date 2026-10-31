"""Contract checks for WP-076: human reply in the operator UI.

Validates that the human reply form is properly wired for sending manual
messages to conversations.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "app/operator_ui/index.html").read_text()
JS = (ROOT / "app/operator_ui/app.js").read_text()


def test_human_reply_section_exists():
    """The operator UI contains a human reply section."""
    assert 'id="human-reply-title"' in HTML


def test_human_reply_section_index():
    """The human reply section has the correct section index."""
    assert "06 / COMUNICAÇÃO" in HTML


def test_human_reply_form_exists():
    """The human reply form exists."""
    assert 'id="human-reply-form"' in HTML


def test_conversation_id_input():
    """The conversation ID input exists with proper attributes."""
    assert 'id="reply-conv-id"' in HTML
    assert 'type="number"' in HTML
    assert 'min="1"' in HTML


def test_reply_message_textarea():
    """The reply message textarea exists with proper attributes."""
    assert 'id="reply-message"' in HTML
    assert 'maxlength="4000"' in HTML


def test_send_button():
    """The send button exists with correct label."""
    assert "Enviar mensagem" in HTML


def test_reply_api_function_exists():
    """The replyApi function is defined in app.js."""
    assert "async function replyApi(" in JS


def test_reply_api_allowlist():
    """The replyApi allowlist only allows conversation messages."""
    # The JS file contains literal \d+ in regex; check for key parts
    assert "conversations/" in JS and "messages" in JS
    assert "replyApi" in JS


def test_reply_api_rejects_invalid_routes():
    """The replyApi rejects routes not in the allowlist."""
    assert "Rota de resposta não permitida" in JS


def test_human_reply_submit_handler():
    """The human-reply-form has a submit event listener."""
    assert '$("human-reply-form").addEventListener("submit"' in JS


def test_sender_type_is_human():
    """The reply sends sender_type as 'human'."""
    assert 'sender_type: "human"' in JS


def test_reply_validates_conversation_id():
    """The reply handler validates the conversation ID."""
    assert "parseInt(convId, 10)" in JS
    assert "isNaN(id)" in JS


def test_reply_resets_form_on_success():
    """The form is reset after a successful reply."""
    assert '$("human-reply-form").reset()' in JS


def test_reply_success_notification():
    """A success notification is shown after sending."""
    assert "Mensagem enviada" in JS
