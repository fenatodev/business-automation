"""WP-277: Test failed tasks badge in notifications."""

import os

UI_DIR = os.path.join(os.path.dirname(__file__), "..", "app", "operator_ui")
HTML = open(os.path.join(UI_DIR, "index.html"), encoding="utf-8").read()
JS = open(os.path.join(UI_DIR, "app.js"), encoding="utf-8").read()


class TestFailedTasksBadge:
    """Verify failed tasks badge in notifications."""

    def test_html_has_task_failed_badge(self):
        """HTML has task failed badge element."""
        assert 'id="task-failed-badge"' in HTML

    def test_html_badge_is_hidden_by_default(self):
        """Badge is hidden by default."""
        assert 'id="task-failed-badge" class="pending-badge" hidden' in HTML

    def test_html_badge_in_tasks_section(self):
        """Badge is in the tasks section."""
        idx_tasks = HTML.index("TAREFAS INTERNAS")
        idx_badge = HTML.index('id="task-failed-badge"')
        assert idx_tasks < idx_badge

    def test_js_fetches_failed_tasks(self):
        """JS fetches failed tasks in updateNotifications."""
        assert '"/internal-tasks/dashboard"' in JS

    def test_js_updates_task_failed_badge(self):
        """JS updates task-failed-badge."""
        assert 'task-failed-badge' in JS

    def test_js_counts_failed_tasks(self):
        """JS counts failed tasks."""
        assert 'failedTaskCount' in JS

    def test_js_includes_failed_tasks_in_total(self):
        """JS includes failed tasks in notification total."""
        assert 'pendingCount + newLeadCount + openConvCount + failedTaskCount' in JS

    def test_js_hides_badge_when_no_failed_tasks(self):
        """JS hides badge when no failed tasks."""
        assert 'badge.hidden = true' in JS

    def test_js_shows_badge_when_failed_tasks_exist(self):
        """JS shows badge and sets count when failed tasks exist."""
        assert 'badge.hidden = false' in JS
        assert 'badge.textContent = count' in JS

    def test_js_uses_one_dashboard_snapshot(self):
        """JS reads all notification counters from one tenant-scoped snapshot."""
        assert 'fetch("/internal-tasks/dashboard"' in JS
        assert 'dashboard.tasks?.failed' in JS
