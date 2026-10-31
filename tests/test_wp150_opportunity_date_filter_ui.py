"""WP-150 — Filtro de data em oportunidades na UI do operador.

Testa o contrato entre a UI (HTML/JS/CSS) e o backend para filtros de data.
Verifica elementos HTML, lógica JavaScript e integração com o backend.
"""
import re


class TestOpportunityDateFilterUI:
    """Test the opportunity date filter UI contract."""

    def setup_method(self):
        with open("app/operator_ui/index.html") as f:
            self.html = f.read()
        with open("app/operator_ui/app.js") as f:
            self.js = f.read()
        with open("app/operator_ui/styles.css") as f:
            self.css = f.read()

    # --- HTML elements ---

    def test_from_date_input_exists(self):
        """The from_date date input exists in the toolbar."""
        assert 'id="opp-from-date"' in self.html
        assert 'type="date"' in self.html

    def test_to_date_input_exists(self):
        """The to_date date input exists in thetoolbar."""
        assert 'id="opp-to-date"' in self.html

    def test_date_inputs_in_toolbar(self):
        """Date inputs are placed in the opp-toolbar-right div."""
        toolbar_match = re.search(
            r'<div class="opp-toolbar-right">(.*?)</div>',
            self.html,
            re.DOTALL,
        )
        assert toolbar_match, "opp-toolbar-right not found"
        toolbar = toolbar_match.group(1)
        assert "opp-from-date" in toolbar
        assert "opp-to-date" in toolbar

    def test_clear_filters_button_exists(self):
        """Clear filters button exists in the toolbar."""
        assert 'id="opp-clear-filters"' in self.html

    # --- CSS styles ---

    def test_date_filter_css_exists(self):
        """CSS class for date filter inputs exists."""
        assert ".opp-date-filter" in self.css

    def test_clear_filters_button_css_exists(self):
        """CSS class for clear filters button exists."""
        assert ".opp-clear-filters-btn" in self.css

    # --- JavaScript logic ---

    def test_refresh_list_reads_from_date(self):
        """refreshList reads from_date input value."""
        assert 'opp-from-date' in self.js
        assert "fromDate" in self.js or "from_date" in self.js

    def test_refresh_list_reads_to_date(self):
        """refreshList reads to_date input value."""
        assert 'opp-to-date' in self.js
        assert "toDate" in self.js or "to_date" in self.js

    def test_refresh_list_sends_from_date_param(self):
        """refreshList includes from_date in API params."""
        assert "from_date=" in self.js

    def test_refresh_list_sends_to_date_param(self):
        """refreshList includes to_date in API params."""
        assert "to_date=" in self.js

    def test_from_date_change_listener(self):
        """Event listener on from_date input resets offset and refreshes."""
        assert 'opp-from-date' in self.js
        # Check for change event listener
        assert re.search(
            r'opp-from-date.*addEventListener.*change',
            self.js,
            re.DOTALL,
        )

    def test_to_date_change_listener(self):
        """Event listener on to_date input resets offset and refreshes."""
        assert re.search(
            r'opp-to-date.*addEventListener.*change',
            self.js,
            re.DOTALL,
        )

    def test_clear_filters_resets_dates(self):
        """Clear filters button resets date inputs."""
        assert re.search(
            r'opp-clear-filters.*addEventListener',
            self.js,
            re.DOTALL,
        )
        # Verify it clears the date fields
        clear_section = re.search(
            r'opp-clear-filters.*?addEventListener.*?\{([^}]*\{[^}]*\}[^}]*)\}',
            self.js,
            re.DOTALL,
        )
        assert clear_section, "Clear filters listener not found"
        clear_handler = clear_section.group(0)
        assert "opp-from-date" in clear_handler
        assert "opp-to-date" in clear_handler

    def test_count_endpoint_includes_date_params(self):
        """Count endpoint also includes date filters."""
        # The countParams should include from_date and to_date
        assert re.search(
            r'countParams.*from_date',
            self.js,
            re.DOTALL,
        )
        assert re.search(
            r'countParams.*to_date',
            self.js,
            re.DOTALL,
        )

    def test_export_csv_includes_date_filters(self):
        """Export CSV includes date filters."""
        export_section = re.search(
            r'opp-export-csv.*?addEventListener.*?\{([^}]*(?:\{[^}]*\}[^}]*)*)\}',
            self.js,
            re.DOTALL,
        )
        assert export_section, "Export CSV listener not found"
        export_handler = export_section.group(0)
        assert "from_date" in export_handler or "fromDate" in export_handler
        assert "to_date" in export_handler or "toDate" in export_handler

    def test_date_filter_resets_offset(self):
        """Changing date filter resets offset to 0."""
        # Both date listeners should reset oppOffset
        date_section = re.search(
            r'// WP-150 — Date filter.*?(?=//|async function|\Z)',
            self.js,
            re.DOTALL,
        )
        assert date_section, "Date filter section not found"
        section = date_section.group(0)
        # Should contain oppOffset = 0
        assert "oppOffset = 0" in section

    def test_clear_filters_resets_all(self):
        """Clear filters resets search, sort, archived, pipeline, and dates."""
        clear_section = re.search(
            r'// WP-150 — Clear all filters.*?(?=//|\Z)',
            self.js,
            re.DOTALL,
        )
        assert clear_section, "Clear filters section not found"
        section = clear_section.group(0)
        assert "opp-search" in section
        assert "opp-from-date" in section
        assert "opp-to-date" in section
        assert "opp-sort" in section
        assert "show-archived" in section
        assert "oppPipelineFilter" in section

    def test_date_inputs_have_title_attribute(self):
        """Date inputs have title attributes for accessibility."""
        assert 'title="Data de início"' in self.html or "Data de início" in self.html
        assert 'title="Data de fim"' in self.html or "Data de fim" in self.html
