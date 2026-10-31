"""WP-164 — Clear filters button in internal tasks section.

Tests that the task clear filters button exists and the JavaScript handler resets all filters.
"""
import re


class TestTaskClearFiltersUI:
    """Test task clear filters UI contract."""

    @classmethod
    def setup_class(cls):
        with open("app/operator_ui/index.html") as f:
            cls.html = f.read()
        with open("app/operator_ui/app.js") as f:
            cls.js = f.read()

    def test_task_clear_filters_button_exists(self):
        """Clear filters button is in the tasks section."""
        assert 'id="task-clear-filters"' in self.html

    def test_task_clear_filters_button_label(self):
        """Button has correct label."""
        assert 'Limpar filtros' in self.html

    def test_task_clear_filters_in_task_filters(self):
        """Button is inside the task-filters container."""
        # The button is in the HTML after task-filters class
        assert 'class="task-filters"' in self.html
        assert 'id="task-clear-filters"' in self.html
        # Verify it's near other task filter elements
        task_section = self.html[self.html.index('class="task-filters"'):]
        assert 'id="task-clear-filters"' in task_section[:2000]

    def test_js_clear_filters_handler_exists(self):
        """JavaScript has clear filters event listener."""
        assert 'task-clear-filters' in self.js

    def test_js_clear_filters_resets_status(self):
        """Clear filters resets status filter."""
        assert 'task-status-filter' in self.js
        # Find the clear filters handler
        clear_section = re.search(
            r'task-clear-filters.*?refreshTasks\(\)', self.js, re.DOTALL
        )
        assert clear_section is not None
        assert 'task-status-filter' in clear_section.group(0)

    def test_js_clear_filters_resets_sort(self):
        """Clear filters resets sort to default."""
        clear_section = re.search(
            r'task-clear-filters.*?refreshTasks\(\)', self.js, re.DOTALL
        )
        assert clear_section is not None
        assert 'task-sort' in clear_section.group(0)

    def test_js_clear_filters_resets_dates(self):
        """Clear filters resets date inputs."""
        clear_section = re.search(
            r'task-clear-filters.*?refreshTasks\(\)', self.js, re.DOTALL
        )
        assert clear_section is not None
        assert 'task-from-date' in clear_section.group(0)
        assert 'task-to-date' in clear_section.group(0)

    def test_js_clear_filters_resets_offset(self):
        """Clear filters resets pagination offset."""
        clear_section = re.search(
            r'task-clear-filters.*?refreshTasks\(\)', self.js, re.DOTALL
        )
        assert clear_section is not None
        assert 'taskOffset = 0' in clear_section.group(0)

    def test_js_clear_filters_refreshes_list(self):
        """Clear filters triggers list refresh."""
        clear_section = re.search(
            r'task-clear-filters.*?refreshTasks\(\)', self.js, re.DOTALL
        )
        assert clear_section is not None
        assert 'refreshTasks()' in clear_section.group(0)

    def test_all_modules_have_clear_filters(self):
        """All major modules now have clear filters buttons."""
        # Opportunities
        assert 'id="opp-clear-filters"' in self.html
        # Conversations
        assert 'id="conv-clear-filter"' in self.html
        # Review queue
        assert 'rq-clear-filters' in self.js
        # Tasks
        assert 'id="task-clear-filters"' in self.html
