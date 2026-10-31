"""WP-165 — Clear filters button in leads and customers sections.

Tests that the clear filters buttons exist and the JavaScript handlers reset all filters,
completing filter parity across all 6 operator modules.
"""
import re


class TestLeadClearFiltersUI:
    """Test lead clear filters UI contract."""

    @classmethod
    def setup_class(cls):
        with open("app/operator_ui/index.html") as f:
            cls.html = f.read()
        with open("app/operator_ui/app.js") as f:
            cls.js = f.read()

    def test_lead_clear_filters_button_exists(self):
        """Clear filters button is in the leads section."""
        assert 'id="lead-clear-filters"' in self.html

    def test_lead_clear_filters_button_label(self):
        """Button has correct label."""
        assert 'Limpar filtros' in self.html

    def test_lead_clear_filters_in_lead_filters(self):
        """Button is inside the lead-filters container."""
        # Verify it's near other lead filter elements
        assert 'class="lead-filters"' in self.html
        assert 'id="lead-clear-filters"' in self.html
        lead_section = self.html[self.html.index('class="lead-filters"'):]
        assert 'id="lead-clear-filters"' in lead_section[:3000]

    def test_js_lead_clear_filters_handler_exists(self):
        """JavaScript has lead clear filters event listener."""
        assert 'lead-clear-filters' in self.js

    def test_js_lead_clear_filters_resets_status(self):
        """Clear filters resets status filter."""
        clear_section = re.search(
            r'lead-clear-filters.*?refreshLeads', self.js, re.DOTALL
        )
        assert clear_section is not None
        assert 'lead-filter-status' in clear_section.group(0)

    def test_js_lead_clear_filters_resets_search(self):
        """Clear filters resets search input."""
        clear_section = re.search(
            r'lead-clear-filters.*?refreshLeads', self.js, re.DOTALL
        )
        assert clear_section is not None
        assert 'lead-search' in clear_section.group(0)

    def test_js_lead_clear_filters_resets_dates(self):
        """Clear filters resets date inputs."""
        clear_section = re.search(
            r'lead-clear-filters.*?refreshLeads', self.js, re.DOTALL
        )
        assert clear_section is not None
        assert 'lead-from-date' in clear_section.group(0)
        assert 'lead-to-date' in clear_section.group(0)

    def test_js_lead_clear_filters_resets_sort(self):
        """Clear filters resets sort to default."""
        clear_section = re.search(
            r'lead-clear-filters.*?refreshLeads', self.js, re.DOTALL
        )
        assert clear_section is not None
        assert 'lead-sort' in clear_section.group(0)

    def test_js_lead_clear_filters_resets_offset(self):
        """Clear filters resets pagination offset."""
        clear_section = re.search(
            r'lead-clear-filters.*?refreshLeads', self.js, re.DOTALL
        )
        assert clear_section is not None
        assert 'leadOffset = 0' in clear_section.group(0)

    def test_leads_export_csv_in_filters(self):
        """Export CSV button is in lead-filters, not panel-actions."""
        lead_section = self.html[self.html.index('class="lead-filters"'):] 
        assert 'id="leads-export-csv"' in lead_section[:3000]


class TestCustomerClearFiltersUI:
    """Test customer clear filters UI contract."""

    @classmethod
    def setup_class(cls):
        with open("app/operator_ui/index.html") as f:
            cls.html = f.read()
        with open("app/operator_ui/app.js") as f:
            cls.js = f.read()

    def test_customer_clear_filters_button_exists(self):
        """Clear filters button is in the customers section."""
        assert 'id="customer-clear-filters"' in self.html

    def test_customer_clear_filters_in_customer_filters(self):
        """Button is inside the customer-filters container."""
        assert 'class="customer-filters"' in self.html
        assert 'id="customer-clear-filters"' in self.html
        customer_section = self.html[self.html.index('class="customer-filters"'):] 
        assert 'id="customer-clear-filters"' in customer_section[:3000]

    def test_js_customer_clear_filters_handler_exists(self):
        """JavaScript has customer clear filters event listener."""
        assert 'customer-clear-filters' in self.js

    def test_js_customer_clear_filters_resets_search(self):
        """Clear filters resets search input."""
        clear_section = re.search(
            r'customer-clear-filters.*?refreshCustomers', self.js, re.DOTALL
        )
        assert clear_section is not None
        assert 'customer-search' in clear_section.group(0)

    def test_js_customer_clear_filters_resets_dates(self):
        """Clear filters resets date inputs."""
        clear_section = re.search(
            r'customer-clear-filters.*?refreshCustomers', self.js, re.DOTALL
        )
        assert clear_section is not None
        assert 'customer-from-date' in clear_section.group(0)
        assert 'customer-to-date' in clear_section.group(0)

    def test_js_customer_clear_filters_resets_sort(self):
        """Clear filters resets sort to default."""
        clear_section = re.search(
            r'customer-clear-filters.*?refreshCustomers', self.js, re.DOTALL
        )
        assert clear_section is not None
        assert 'customer-sort' in clear_section.group(0)

    def test_js_customer_clear_filters_resets_offset(self):
        """Clear filters resets pagination offset."""
        clear_section = re.search(
            r'customer-clear-filters.*?refreshCustomers', self.js, re.DOTALL
        )
        assert clear_section is not None
        assert 'customerOffset = 0' in clear_section.group(0)


class TestFilterParity:
    """Verify all 6 modules have clear filters buttons."""

    @classmethod
    def setup_class(cls):
        with open("app/operator_ui/index.html") as f:
            cls.html = f.read()

    def test_opportunities_have_clear_filters(self):
        assert 'id="opp-clear-filters"' in self.html

    def test_conversations_have_clear_filters(self):
        assert 'id="conv-clear-filter"' in self.html

    def test_review_queue_has_clear_filters(self):
        assert 'id="rq-clear-filters"' in self.html

    def test_internal_tasks_have_clear_filters(self):
        assert 'id="task-clear-filters"' in self.html

    def test_leads_have_clear_filters(self):
        assert 'id="lead-clear-filters"' in self.html

    def test_customers_have_clear_filters(self):
        assert 'id="customer-clear-filters"' in self.html
