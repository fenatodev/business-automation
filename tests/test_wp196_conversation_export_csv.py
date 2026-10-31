"""WP-196 — Conversation export CSV handler with filters.

The conv-export-csv button existed in HTML but had no JavaScript handler.
Added handler that builds URL with all current filters (channel, status,
query, customer_id, dates) and calls downloadCsv.
"""


class TestConversationExportCsvHandler:
    """Test export CSV handler exists and uses filters."""

    def test_conv_export_csv_handler_exists(self):
        """conv-export-csv click handler exists in app.js."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        assert 'conv-export-csv' in js
        # Find the handler
        handler_pos = js.index('conv-export-csv')
        section = js[handler_pos:handler_pos + 1000]
        assert "addEventListener" in section
        assert "click" in section

    def test_export_uses_channel_filter(self):
        """Export includes channel filter."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        handler_pos = js.index('conv-export-csv')
        section = js[handler_pos:handler_pos + 1000]
        assert "convFilterChannel" in section
        assert "channel=" in section

    def test_export_uses_status_filter(self):
        """Export includes status filter."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        handler_pos = js.index('conv-export-csv')
        section = js[handler_pos:handler_pos + 1000]
        assert "convFilterStatus" in section
        assert "status=" in section

    def test_export_uses_query_filter(self):
        """Export includes search query filter."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        handler_pos = js.index('conv-export-csv')
        section = js[handler_pos:handler_pos + 1000]
        assert "convFilterQuery" in section
        assert "q=" in section

    def test_export_uses_customer_id_filter(self):
        """Export includes customer_id filter (WP-195)."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        handler_pos = js.index('conv-export-csv')
        section = js[handler_pos:handler_pos + 1000]
        assert "convFilterCustomerId" in section
        assert "customer_id=" in section

    def test_export_uses_date_filters(self):
        """Export includes date range filters."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        handler_pos = js.index('conv-export-csv')
        section = js[handler_pos:handler_pos + 1000]
        assert "convFilterFromDate" in section
        assert "convFilterToDate" in section
        assert "from_date=" in section
        assert "to_date=" in section

    def test_export_calls_download_csv(self):
        """Export handler calls downloadCsv function."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        handler_pos = js.index('conv-export-csv')
        section = js[handler_pos:handler_pos + 1000]
        assert "downloadCsv" in section
        assert "conversations.csv" in section

    def test_export_uses_correct_endpoint(self):
        """Export uses /companies/{id}/conversations/export.csv."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        handler_pos = js.index('conv-export-csv')
        section = js[handler_pos:handler_pos + 1000]
        assert "conversations/export.csv" in section

    def test_export_button_exists_in_html(self):
        """conv-export-csv button exists in HTML."""
        with open("app/operator_ui/index.html") as f:
            html = f.read()
        assert 'id="conv-export-csv"' in html

    def test_export_handler_has_wp_comment(self):
        """Handler is marked with WP-196 comment."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        assert "WP-196" in js
