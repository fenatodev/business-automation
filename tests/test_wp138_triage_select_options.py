"""WP-138 — Individual triage select options UI contract tests.

Verifies that the individual triage form select includes all seven options
from OpportunityTriageUpdate: pending, follow, ignore, prepare_proposal,
in_progress, done, lost.
"""

import pytest


class TestTriageSelectOptions:
    """Verify the triage select has all backend options."""

    def _get_index_html(self):
        with open("app/operator_ui/index.html") as f:
            return f.read()

    def _get_app_js(self):
        with open("app/operator_ui/app.js") as f:
            return f.read()

    # --- HTML: individual triage select ---

    def test_triage_select_exists(self):
        """HTML should have next-action select."""
        html = self._get_index_html()
        assert 'id="next-action"' in html

    def test_triage_select_has_pending(self):
        html = self._get_index_html()
        assert 'value="pending"' in html

    def test_triage_select_has_follow(self):
        html = self._get_index_html()
        assert 'value="follow"' in html

    def test_triage_select_has_ignore(self):
        html = self._get_index_html()
        assert 'value="ignore"' in html

    def test_triage_select_has_prepare_proposal(self):
        html = self._get_index_html()
        assert 'value="prepare_proposal"' in html

    def test_triage_select_has_in_progress(self):
        """The critical fix — in_progress must be in the individual triage select."""
        html = self._get_index_html()
        assert 'value="in_progress"' in html

    def test_triage_select_has_done(self):
        """The critical fix — done must be in the individual triage select."""
        html = self._get_index_html()
        assert 'value="done"' in html

    def test_triage_select_has_lost(self):
        """The critical fix — lost must be in the individual triage select."""
        html = self._get_index_html()
        assert 'value="lost"' in html

    # --- HTML: bulk triage select (should already have all options) ---

    def test_bulk_triage_select_has_in_progress(self):
        html = self._get_index_html()
        assert 'id="bulk-triage-action"' in html
        assert 'value="in_progress"' in html

    def test_bulk_triage_select_has_done(self):
        html = self._get_index_html()
        assert 'value="done"' in html

    def test_bulk_triage_select_has_lost(self):
        html = self._get_index_html()
        assert 'value="lost"' in html

    # --- JavaScript: actionLabels must cover all options ---

    def test_action_labels_has_in_progress(self):
        js = self._get_app_js()
        assert 'in_progress' in js
        assert '"Em andamento"' in js or "'Em andamento'" in js

    def test_action_labels_has_done(self):
        js = self._get_app_js()
        assert 'done' in js
        assert '"Concluída"' in js or "'Concluída'" in js

    def test_action_labels_has_lost(self):
        js = self._get_app_js()
        assert 'lost' in js
        assert '"Perdida"' in js or "'Perdida'" in js

    # --- Consistency: individual and bulk selects match ---

    def test_individual_and_bulk_selects_have_same_options(self):
        """Both selects should have the same 7 options."""
        html = self._get_index_html()
        # Find individual triage select
        individual_start = html.find('id="next-action"')
        individual_end = html.find('</select>', individual_start)
        individual_block = html[individual_start:individual_end]

        # Find bulk triage select
        bulk_start = html.find('id="bulk-triage-action"')
        bulk_end = html.find('</select>', bulk_start)
        bulk_block = html[bulk_start:bulk_end]

        # Extract values
        import re
        individual_values = set(re.findall(r'value="([^"]+)"', individual_block))
        bulk_values = set(re.findall(r'value="([^"]+)"', bulk_block))

        assert individual_values == bulk_values, (
            f"Individual triage and bulk triage selects have different options. "
            f"Individual: {individual_values}, Bulk: {bulk_values}"
        )
        assert len(individual_values) == 7, (
            f"Expected 7 options, found {len(individual_values)}"
        )
