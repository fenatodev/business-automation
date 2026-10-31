"""Contract checks for WP-077: unified conversations with connected reply form.

Validates that the conversations section and human reply form are properly
integrated in the operator panel, with auto-filled conversation ID.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "app/operator_ui/index.html").read_text()
JS = (ROOT / "app/operator_ui/app.js").read_text()
CSS = (ROOT / "app/operator_ui/styles.css").read_text()


# --- HTML structure ---

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
    detail_pos = HTML.index('id="conv-detail"')
    assert 'hidden' in HTML[detail_pos:detail_pos + 200]


def test_conversation_messages_container():
    """The messages container exists inside conv-detail."""
    assert 'id="conv-messages"' in HTML
    assert 'class="conv-messages"' in HTML


def test_conversation_refresh_button():
    """The refresh button for conversations exists."""
    assert 'id="conv-refresh"' in HTML


def test_conversation_detail_header():
    """The conversation detail header element exists."""
    assert 'id="conv-detail-header"' in HTML


def test_conversation_detail_header_row():
    """The header row flex container exists for the reply toggle button."""
    assert 'class="conv-detail-header-row"' in HTML


def test_reply_toggle_button():
    """The reply toggle button exists and is hidden by default."""
    assert 'id="conv-reply-toggle"' in HTML
    toggle_pos = HTML.index('id="conv-reply-toggle"')
    assert 'hidden' in HTML[toggle_pos:toggle_pos + 150]


# --- Human reply form integration ---

def test_human_reply_form_exists():
    """The human reply form exists inside conv-detail."""
    assert 'id="human-reply-form"' in HTML


def test_human_reply_form_hidden_by_default():
    """The human reply form is hidden by default."""
    form_pos = HTML.index('id="human-reply-form"')
    assert 'hidden' in HTML[form_pos:form_pos + 200]


def test_reply_conv_id_is_hidden_input():
    """The conversation ID input is hidden and readonly."""
    assert 'id="reply-conv-id"' in HTML
    # Find the input element
    input_pos = HTML.index('id="reply-conv-id"')
    input_context = HTML[input_pos:input_pos + 200]
    assert 'type="hidden"' in input_context
    assert 'readonly' in input_context


def test_reply_message_textarea():
    """The reply message textarea exists with proper attributes."""
    assert 'id="reply-message"' in HTML
    assert 'maxlength="4000"' in HTML


def test_send_button():
    """The send button exists with correct label."""
    assert "Enviar mensagem" in HTML


# --- JavaScript functions ---

def test_conversation_api_function_exists():
    """The conversationApi function is defined in app.js."""
    assert "async function conversationApi(" in JS


def test_conversation_api_allowlist():
    """The conversationApi allowlist includes the required routes."""
    assert "/companies/" in JS and "/conversations" in JS
    assert "/conversations/" in JS and "messages" in JS


def test_conversation_api_rejects_invalid_routes():
    """The conversationApi rejects routes not in the allowlist."""
    assert "Rota de conversas não permitida" in JS


def test_reply_api_function_exists():
    """The replyApi function is defined in app.js."""
    assert "async function replyApi(" in JS


def test_reply_api_allowlist():
    """The replyApi allowlist only allows conversation messages."""
    assert "replyApi" in JS
    assert "conversations/" in JS and "messages" in JS


def test_reply_api_rejects_invalid_routes():
    """The replyApi rejects routes not in the allowlist."""
    assert "Rota de resposta não permitida" in JS


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
    assert 'human: "Humano"' in JS


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


def test_reply_toggle_event_listener():
    """The conv-reply-toggle button has a click handler."""
    assert '$("conv-reply-toggle").addEventListener("click"' in JS


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


def test_reply_success_notification():
    """A success notification is shown after sending."""
    assert "Mensagem enviada" in JS


# --- Connection integration ---

def test_select_conversation_fills_reply_id():
    """selectConversation fills the reply-conv-id field."""
    assert '$("reply-conv-id").value = id' in JS


def test_select_conversation_shows_reply_toggle():
    """selectConversation shows the reply toggle button."""
    assert '$("conv-reply-toggle").hidden = false' in JS


def test_conversations_state_in_disconnect():
    """Disconnect clears conversations state."""
    assert "conversations = []" in JS
    assert "selectedConvId = null" in JS


def test_workspace_observer_for_conversations():
    """A MutationObserver loads conversations when workspace becomes visible."""
    assert "workspaceObserver" in JS
    assert "refreshConversations" in JS


# --- CSS styles ---

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
    assert ".message-bubble.human" in CSS
    assert ".message-sender" in CSS


def test_conv_detail_header_row_style():
    """CSS contains flex layout for the header row."""
    assert ".conv-detail-header-row" in CSS


def test_human_reply_form_style():
    """CSS contains styles for the human reply form."""
    assert "#human-reply-form" in CSS
