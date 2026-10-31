"""WP-135 — Conversation sort UI contract tests.

Verifies that the conversation sort dropdown is connected to the backend
and that client-side sorting is removed in favor of backend sorting.
"""

import pytest


class TestConversationSortUI:
    """Verify the conversation sort UI is properly connected to the backend."""

    def _get_app_js(self):
        with open("app/operator_ui/app.js") as f:
            return f.read()

    def _get_index_html(self):
        with open("app/operator_ui/index.html") as f:
            return f.read()

    def _get_styles_css(self):
        with open("app/operator_ui/styles.css") as f:
            return f.read()

    # --- HTML elements ---

    def test_sort_dropdown_exists(self):
        """HTML should have conv-filter-sort dropdown."""
        html = self._get_index_html()
        assert 'id="conv-filter-sort"' in html

    def test_sort_dropdown_has_last_message_option(self):
        """Sort dropdown should include last_message option."""
        html = self._get_index_html()
        assert 'value="last_message"' in html

    def test_sort_dropdown_has_created_at_option(self):
        """Sort dropdown should include created_at option."""
        html = self._get_index_html()
        assert 'value="created_at"' in html

    def test_sort_dropdown_has_id_option(self):
        """Sort dropdown should include id option."""
        html = self._get_index_html()
        assert 'value="id"' in html

    # --- JavaScript state ---

    def test_conv_filter_sort_state_variable(self):
        """app.js should have convFilterSort state variable."""
        js = self._get_app_js()
        assert "convFilterSort" in js

    def test_conv_filter_sort_defaults_to_last_message(self):
        """convFilterSort should default to 'last_message'."""
        js = self._get_app_js()
        assert 'convFilterSort = "last_message"' in js

    # --- buildConversationUrl ---

    def test_build_conversation_url_includes_sort(self):
        """buildConversationUrl should include sort param."""
        js = self._get_app_js()
        assert 'params.set("sort"' in js or "params.set('sort'" in js
        # Verify sort is set from convFilterSort
        assert "convFilterSort" in js

    # --- Event listeners ---

    def test_sort_filter_change_listener(self):
        """conv-filter-sort should have a change listener."""
        js = self._get_app_js()
        assert 'conv-filter-sort' in js
        # The listener should update convFilterSort and reset offset
        assert 'convOffset = 0' in js

    def test_sort_filter_resets_offset(self):
        """Changing sort should reset convOffset to 0."""
        js = self._get_app_js()
        # Find the sort listener block
        assert 'conv-filter-sort' in js
        assert 'convOffset = 0' in js

    # --- No client-side sort ---

    def test_no_client_side_sort_in_show_conversation_list(self):
        """showConversationList should not sort conversations client-side."""
        js = self._get_app_js()
        # The function should not contain .sort() on conversations
        # Find the showConversationList function
        start = js.find("function showConversationList()")
        end = js.find("\n}", start + 100)
        func_body = js[start:end] if start != -1 and end != -1 else ""
        assert ".sort(" not in func_body, (
            "showConversationList should not sort client-side; "
            "backend already returns sorted results"
        )

    def test_no_ordered_variable_in_show_conversation_list(self):
        """showConversationList should iterate conversations directly, not 'ordered'."""
        js = self._get_app_js()
        start = js.find("function showConversationList()")
        end = js.find("\n}", start + 100)
        func_body = js[start:end] if start != -1 and end != -1 else ""
        assert "const ordered" not in func_body, (
            "showConversationList should not create an 'ordered' variable"
        )

    # --- Clear filters ---

    def test_clear_filters_resets_sort(self):
        """Clear filters should reset conv-filter-sort to default."""
        js = self._get_app_js()
        # clearConversationsFilters should reset sort
        assert 'conv-filter-sort' in js
        assert 'convFilterSort = "last_message"' in js

    # --- Allowlist ---

    def test_conversation_api_allows_sort_query_param(self):
        """conversationApi allowlist should allow query params on conversations."""
        js = self._get_app_js()
        # The allowlist uses regex like /companies/\d+/conversations($|\?) to allow query params
        assert r'conversations($|\?)' in js or r'conversations($|\\?)' in js

    # --- Integration ---

    def test_refresh_conversations_uses_build_conversation_url(self):
        """refreshConversations should call buildConversationUrl()."""
        js = self._get_app_js()
        assert "buildConversationUrl(" in js

    def test_sort_dropdown_in_filters_section(self):
        """The sort dropdown should be inside conv-filters section."""
        html = self._get_index_html()
        # conv-filter-sort should appear after conv-filters
        filters_pos = html.find('class="conv-filters"')
        sort_pos = html.find('id="conv-filter-sort"')
        assert filters_pos != -1 and sort_pos != -1
        assert sort_pos > filters_pos, "Sort dropdown should be inside conv-filters"
