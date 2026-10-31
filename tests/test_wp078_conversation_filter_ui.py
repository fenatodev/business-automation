"""Contract checks for WP-078: conversation search and filter UI.

Validates that the filter controls and search functionality are properly
integrated in the operator panel.
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


def test_conversation_messages_container():
    """The messages container exists inside conv-detail."""
    assert 'id="conv-messages"' in HTML
    assert 'class="conv-messages"' in HTML


def test_conversation_refresh_button():
    """The refresh button for conversations exists."""
    assert 'id="conv-refresh"' in HTML


# --- Filter controls ---

def test_filter_container_exists():
    """The filter container exists."""
    assert 'class="conv-filters"' in HTML


def test_channel_filter_dropdown():
    """The channel filter dropdown exists."""
    assert 'id="conv-filter-channel"' in HTML


def test_channel_filter_options():
    """The channel filter has the expected options."""
    assert '<option value="">Todos os canais</option>' in HTML
    assert '<option value="whatsapp">WhatsApp</option>' in HTML
    assert '<option value="web">Web</option>' in HTML
    assert '<option value="email">E-mail</option>' in HTML


def test_status_filter_dropdown():
    """The status filter dropdown exists."""
    assert 'id="conv-filter-status"' in HTML


def test_status_filter_options():
    """The status filter has the expected options."""
    assert '<option value="">Todos os status</option>' in HTML
    assert '<option value="open">Aberta</option>' in HTML
    assert '<option value="closed">Fechada</option>' in HTML


def test_search_input_exists():
    """The search input exists."""
    assert 'id="conv-search-q"' in HTML
    assert 'type="search"' in HTML


def test_search_button_exists():
    """The search button exists."""
    assert 'id="conv-search-btn"' in HTML


def test_clear_filter_button_exists():
    """The clear filter button exists."""
    assert 'id="conv-clear-filter"' in HTML


def test_search_inline_container():
    """The search inline container exists."""
    assert 'class="conv-search-inline"' in HTML


# --- Human reply form ---

def test_human_reply_form_exists():
    """The human reply form exists inside conv-detail."""
    assert 'id="human-reply-form"' in HTML


def test_reply_conv_id_is_hidden_input():
    """The conversation ID input is hidden and readonly."""
    assert 'id="reply-conv-id"' in HTML
    assert 'type="hidden"' in HTML
    assert 'readonly' in HTML


def test_reply_message_textarea():
    """The reply message textarea exists."""
    assert 'id="reply-message"' in HTML


def test_reply_toggle_button():
    """The reply toggle button exists."""
    assert 'id="conv-reply-toggle"' in HTML


# --- JavaScript functions ---

def test_conversationApi_exists():
    """The conversationApi function exists."""
    assert "async function conversationApi(" in JS


def test_replyApi_exists():
    """The replyApi function exists."""
    assert "async function replyApi(" in JS


def test_conversationApi_allowlist():
    """The conversationApi has strict path allowlisting."""
    assert "/companies/" in JS
    assert "/conversations" in JS
    assert "Rota de conversas não permitida" in JS


def test_replyApi_allowlist():
    """The replyApi has strict path allowlisting."""
    assert "Rota de resposta não permitida" in JS


def test_buildConversationUrl_exists():
    """The buildConversationUrl function exists."""
    assert "function buildConversationUrl(" in JS


def test_buildConversationUrl_uses_URLSearchParams():
    """The buildConversationUrl uses URLSearchParams for query params."""
    assert "URLSearchParams" in JS


def test_showConversationList_exists():
    """The showConversationList function exists."""
    assert "function showConversationList(" in JS


def test_selectConversation_exists():
    """The selectConversation function exists."""
    assert "async function selectConversation(" in JS


def test_refreshConversations_exists():
    """The refreshConversations function exists."""
    assert "async function refreshConversations(" in JS


def test_clearConversationFilters_exists():
    """The clearConversationFilters function exists."""
    assert "function clearConversationFilters(" in JS


def test_channel_labels_exists():
    """The channelLabels mapping exists."""
    assert "channelLabels" in JS
    assert "whatsapp" in JS
    assert "WhatsApp" in JS


def test_sender_labels_exists():
    """The senderLabels mapping exists."""
    assert "senderLabels" in JS
    assert "customer" in JS
    assert "Cliente" in JS


# --- Filter state variables ---

def test_conv_filter_channel_state():
    """The convFilterChannel state variable exists."""
    assert "convFilterChannel" in JS


def test_conv_filter_status_state():
    """The convFilterStatus state variable exists."""
    assert "convFilterStatus" in JS


def test_conv_filter_query_state():
    """The convFilterQuery state variable exists."""
    assert "convFilterQuery" in JS


# --- Event listeners ---

def test_channel_filter_change_listener():
    """The channel filter change listener exists."""
    assert 'conv-filter-channel' in JS
    assert 'addEventListener("change"' in JS


def test_status_filter_change_listener():
    """The status filter change listener exists."""
    assert 'conv-filter-status' in JS


def test_search_button_listener():
    """The search button click listener exists."""
    assert 'conv-search-btn' in JS
    assert 'addEventListener("click"' in JS


def test_clear_filter_listener():
    """The clear filter click listener exists."""
    assert 'conv-clear-filter' in JS


def test_search_keydown_listener():
    """The search input keydown listener exists."""
    assert 'conv-search-q' in JS
    assert 'addEventListener("keydown"' in JS


# --- CSS styles ---

def test_conv_filters_style():
    """The conv-filters container style exists."""
    assert ".conv-filters" in CSS


def test_conv_filter_group_style():
    """The conv-filter-group style exists."""
    assert ".conv-filter-group" in CSS


def test_conv_search_inline_style():
    """The conv-search-inline style exists."""
    assert ".conv-search-inline" in CSS


def test_conversation_item_style():
    """The conversation-item style exists."""
    assert ".conversation-item" in CSS


def test_message_bubble_style():
    """The message-bubble style exists."""
    assert ".message-bubble" in CSS


def test_message_bubble_customer_variant():
    """The message-bubble customer variant exists."""
    assert ".message-bubble.customer" in CSS


def test_message_bubble_agent_variant():
    """The message-bubble agent variant exists."""
    assert ".message-bubble.agent" in CSS


def test_message_bubble_human_variant():
    """The message-bubble human variant exists."""
    assert ".message-bubble.human" in CSS


def test_conv_detail_style():
    """The conv-detail style exists."""
    assert ".conv-detail" in CSS


def test_conv_detail_header_row_style():
    """The conv-detail-header-row style exists."""
    assert ".conv-detail-header-row" in CSS


def test_human_reply_form_style():
    """The human-reply-form style exists."""
    assert "#human-reply-form" in CSS


# --- Disconnect cleanup ---

def test_disconnect_clears_conversations():
    """The disconnect function clears conversations state."""
    assert "conversations = []" in JS


def test_disconnect_clears_selectedConvId():
    """The disconnect function clears selectedConvId."""
    assert "selectedConvId = null" in JS


# --- Integration ---

def test_workspace_observer_exists():
    """The workspace MutationObserver exists."""
    assert "workspaceObserver" in JS
    assert "MutationObserver" in JS


def test_conv_detail_hidden_by_default():
    """The conv-detail is hidden by default in JS initialization."""
    assert '$("conv-detail").hidden = true' in JS


def test_conv_list_cleared_on_init():
    """The conv-list is cleared on initialization."""
    assert '$("conv-list").replaceChildren()' in JS


def test_filter_empty_message():
    """The empty message distinguishes between no conversations and no filter matches."""
    assert "Nenhuma conversa corresponde aos filtros" in JS
    assert "Nenhuma conversa registrada" in JS
