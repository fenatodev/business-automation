"""Contract checks for WP-075: conversation history in the operator UI.

Validates that the conversations section is properly wired in the operator panel.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "app/operator_ui/index.html").read_text()
JS = (ROOT / "app/operator_ui/app.js").read_text()
CSS = (ROOT / "app/operator_ui/styles.css").read_text()


def test_conversations_section_exists():
    """The operator UI contains a conversations section."""
    assert 'id="conversations-title"' in HTML


def test_conversations_section_index():
    """The conversations section has the correct section index."""
    assert "06 / COMUNICAÇÃO" in HTML


def test_conversation_list_container():
    """The conversation list container exists."""
    assert 'id="conv-list"' in HTML
    assert 'class="conversation-list"' in HTML


def test_conversation_detail_container():
    """The conversation detail viewer exists and is hidden by default."""
    assert 'id="conv-detail"' in HTML
    assert 'class="conv-detail"' in HTML
    assert 'hidden' in HTML[HTML.index('id="conv-detail"'):HTML.index('id="conv-detail"') + 200]


def test_conversation_messages_container():
    """The messages container exists inside conv-detail."""
    assert 'id="conv-messages"' in HTML
    assert 'class="conv-messages"' in HTML


def test_conversation_refresh_button():
    """The refresh button for conversations exists."""
    assert 'id="conv-refresh"' in HTML


def test_conversation_api_function_exists():
    """The conversationApi function is defined in app.js."""
    assert "async function conversationApi(" in JS


def test_conversation_api_allowlist():
    """The conversationApi allowlist includes the required routes."""
    assert "/conversations/" in JS
    # The JS file contains literal \d+ in regex patterns
    assert "conversations/" in JS and "messages" in JS
    assert "companies/" in JS and "/conversations" in JS
    # Verify the regex pattern exists by checking for key parts
    assert "/conversations/\\d+/messages" in JS or "conversations\\/\\d+\\/messages" in JS


def test_conversation_api_rejects_invalid_routes():
    """The conversationApi rejects routes not in the allowlist."""
    assert "Rota de conversas não permitida" in JS


def test_channel_labels_defined():
    """Channel labels are defined for display."""
    assert 'channelLabels' in JS
    assert 'whatsapp: "WhatsApp"' in JS
    assert 'web: "Web"' in JS


def test_sender_labels_defined():
    """Sender labels are defined for message bubbles."""
    assert 'senderLabels' in JS
    assert 'customer: "Cliente"' in JS
    assert 'agent: "Agente"' in JS


def test_show_conversation_list_function():
    """The showConversationList function exists."""
    assert "function showConversationList()" in JS


def test_select_conversation_function():
    """The selectConversation function exists."""
    assert "async function selectConversation(" in JS


def test_refresh_conversations_function():
    """The refreshConversations function exists."""
    assert "async function refreshConversations()" in JS


def test_conversation_refresh_event_listener():
    """The conv-refresh button has a click handler."""
    assert '$("conv-refresh").addEventListener("click"' in JS


def test_conversation_css_styles():
    """CSS contains styles for conversation components."""
    assert ".conversation-list" in CSS
    assert ".conversation-item" in CSS
    assert ".conv-detail" in CSS
    assert ".conv-messages" in CSS
    assert ".message-bubble" in CSS


def test_message_bubble_sender_styles():
    """CSS distinguishes message bubbles by sender type."""
    assert ".message-bubble.customer" in CSS
    assert ".message-bubble.agent" in CSS
    assert ".message-sender" in CSS


def test_conversations_state_in_disconnect():
    """Disconnect clears conversations state."""
    assert "conversations = []" in JS
    assert "selectedConvId = null" in JS


def test_conversation_detail_header():
    """The conversation detail header element exists."""
    assert 'id="conv-detail-header"' in HTML
