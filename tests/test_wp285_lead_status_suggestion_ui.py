"""WP-285: AI-assisted lead status suggestion in operator UI."""

import pytest
from unittest.mock import patch


class TestLeadStatusSuggestionUI:
    """Verify the operator UI exposes lead status suggestion."""

    def test_lead_api_allows_suggest_status(self):
        """leadApi allowlist includes /leads/{id}/suggest-status."""
        with open("app/operator_ui/app.js") as f:
            content = f.read()
        assert "suggest-status" in content
        assert "suggestLeadStatus" in content

    def test_suggest_button_exists_in_render(self):
        """renderLeads creates suggest button for each lead."""
        with open("app/operator_ui/app.js") as f:
            content = f.read()
        assert "lead-suggest-status-btn" in content
        assert "🤖 Sugerir" in content

    def test_suggest_lead_status_function_exists(self):
        """suggestLeadStatus function calls /suggest-status endpoint."""
        with open("app/operator_ui/app.js") as f:
            content = f.read()
        assert "async function suggestLeadStatus" in content
        assert '/suggest-status' in content

    def test_suggest_button_stops_propagation(self):
        """Click handler stops propagation to avoid triggering lead detail."""
        with open("app/operator_ui/app.js") as f:
            content = f.read()
        assert "e.stopPropagation()" in content

    def test_css_lead_status_row_exists(self):
        """CSS has .lead-status-row for flex layout."""
        with open("app/operator_ui/styles.css") as f:
            content = f.read()
        assert ".lead-status-row" in content
        assert "display: flex" in content

    def test_css_suggest_button_exists(self):
        """CSS has .lead-suggest-status-btn styles."""
        with open("app/operator_ui/styles.css") as f:
            content = f.read()
        assert ".lead-suggest-status-btn" in content

    def test_suggest_uses_confirm_before_apply(self):
        """Suggestion asks user to confirm before applying status."""
        with open("app/operator_ui/app.js") as f:
            content = f.read()
        assert "confirm(" in content
        assert "suggested_status" in content

    def test_suggest_updates_select_on_apply(self):
        """On confirm, select value is updated to suggested status."""
        with open("app/operator_ui/app.js") as f:
            content = f.read()
        assert "select.value = res.suggested_status" in content

    def test_suggest_calls_update_lead_status(self):
        """After confirming, updateLeadStatus is called."""
        with open("app/operator_ui/app.js") as f:
            content = f.read()
        assert "updateLeadStatus(leadId, res.suggested_status)" in content

    def test_suggest_button_disabled_during_request(self):
        """Button is disabled while fetching suggestion."""
        with open("app/operator_ui/app.js") as f:
            content = f.read()
        assert "button.disabled = true" in content
        assert "button.disabled = false" in content

    def test_suggest_button_shows_loading(self):
        """Button text changes to loading indicator."""
        with open("app/operator_ui/app.js") as f:
            content = f.read()
        assert 'button.textContent = "⏳"' in content

    def test_suggest_error_handling(self):
        """Errors are caught and button is re-enabled."""
        with open("app/operator_ui/app.js") as f:
            content = f.read()
        assert "finally" in content
        assert "button.textContent = originalText" in content
