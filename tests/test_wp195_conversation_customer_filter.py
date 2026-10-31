"""WP-195 — Filter conversations by customer in operator UI.

Tests that the conversation section has a customer filter dropdown
that connects to the existing backend ?customer_id= parameter.
"""


class TestCustomerFilterHTML:
    """Test customer filter dropdown exists in HTML."""

    def test_customer_filter_dropdown_exists(self):
        """conv-filter-customer dropdown exists in conversation filters."""
        with open("app/operator_ui/index.html") as f:
            html = f.read()
        assert 'id="conv-filter-customer"' in html

    def test_customer_filter_has_default_option(self):
        """Dropdown has 'Todos os customers' default option."""
        with open("app/operator_ui/index.html") as f:
            html = f.read()
        select_start = html.index('id="conv-filter-customer"')
        select_end = html.index("</select>", select_start)
        select_content = html[select_start:select_end]
        assert 'value=""' in select_content
        assert "Todos os customers" in select_content

    def test_customer_filter_in_conv_filters_section(self):
        """Customer filter is inside conv-filters section."""
        with open("app/operator_ui/index.html") as f:
            html = f.read()
        filters_start = html.index('class="conv-filters"')
        filters_end = html.index("</div>", html.index("conv-filters", filters_start) + 20)
        # Find the closing div of conv-filters
        conv_filter_pos = html.index('id="conv-filter-customer"')
        assert filters_start < conv_filter_pos


class TestCustomerFilterJavaScript:
    """Test JavaScript customer filter functionality."""

    def test_conv_filter_customer_id_state_variable(self):
        """convFilterCustomerId state variable exists."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        assert "convFilterCustomerId" in js

    def test_build_conversation_url_includes_customer_id(self):
        """buildConversationUrl adds customer_id param when set."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        url_func_start = js.index("function buildConversationUrl")
        url_func_end = js.index("}", url_func_start + 500)
        url_func = js[url_func_start:url_func_end]
        assert "customer_id" in url_func
        assert "convFilterCustomerId" in url_func

    def test_build_conversation_count_url_includes_customer_id(self):
        """buildConversationCountUrl adds customer_id param when set."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        count_func_start = js.index("function buildConversationCountUrl")
        count_func_end = js.index("}", count_func_start + 500)
        count_func = js[count_func_start:count_func_end]
        assert "customer_id" in count_func
        assert "convFilterCustomerId" in count_func

    def test_customer_filter_change_listener(self):
        """conv-filter-customer change event updates state and refreshes."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        # Find the event listener for conv-filter-customer by pattern
        # It should be: $("conv-filter-customer").addEventListener("change", ...)
        assert 'conv-filter-customer' in js
        # Search the entire file for the listener pattern
        lines = js.split("\n")
        found_listener = False
        for i, line in enumerate(lines):
            if "conv-filter-customer" in line and "addEventListener" in line:
                found_listener = True
                break
            if "conv-filter-customer" in line and i + 1 < len(lines):
                if "addEventListener" in lines[i + 1]:
                    found_listener = True
                    break
        assert found_listener, "No addEventListener found for conv-filter-customer"

    def test_clear_filters_resets_customer_filter(self):
        """clearConversationFilters resets convFilterCustomerId."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        clear_start = js.index("function clearConversationFilters")
        clear_end = js.index("}", clear_start + 800)
        clear_func = js[clear_start:clear_end]
        assert 'convFilterCustomerId = ""' in clear_func
        assert 'conv-filter-customer' in clear_func

    def test_populate_customer_filter_function(self):
        """populateCustomerFilter function loads customers for dropdown."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        assert "populateCustomerFilter" in js
        func_start = js.index("function populateCustomerFilter")
        func_end = js.index("}", func_start + 800)
        func = js[func_start:func_end]
        assert "conv-filter-customer" in func
        assert "customerApi" in func or "/customers" in func

    def test_customer_filter_populated_flag_reset_on_disconnect(self):
        """convCustomerFilterPopulated is reset on disconnect."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        assert "convCustomerFilterPopulated = false" in js

    def test_customer_filter_populated_in_refresh_conversations(self):
        """populateCustomerFilter is called in refreshConversations."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        refresh_start = js.index("async function refreshConversations")
        refresh_end = js.index("}", refresh_start + 1500)
        refresh_func = js[refresh_start:refresh_end]
        assert "populateCustomerFilter" in refresh_func

    def test_customer_filter_option_creation(self):
        """Dropdown options are created with customer id and name."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        func_start = js.index("function populateCustomerFilter")
        func_end = js.index("}", func_start + 800)
        func = js[func_start:func_end]
        assert "createElement" in func and "option" in func
        assert ".value" in func
        assert ".textContent" in func

    def test_customer_filter_uses_text_content_not_inner_html(self):
        """Customer filter uses textContent for security (XSS rule)."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        func_start = js.index("function populateCustomerFilter")
        func_end = js.index("}", func_start + 800)
        func = js[func_start:func_end]
        assert "textContent" in func
        assert "innerHTML" not in func
