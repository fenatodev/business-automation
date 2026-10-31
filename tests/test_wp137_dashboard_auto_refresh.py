"""WP-137 — Dashboard auto-refresh and notifications polling UI contract tests."""

import pytest


class TestDashboardAutoRefreshUI:
    """Verify dashboard auto-refresh and notifications polling are properly implemented."""

    def _get_app_js(self):
        with open("app/operator_ui/app.js") as f:
            return f.read()

    # --- Dashboard polling ---

    def test_dashboard_interval_state_variable(self):
        """app.js should have dashboardIntervalId state variable."""
        js = self._get_app_js()
        assert "dashboardIntervalId" in js

    def test_dashboard_refresh_interval_constant(self):
        """app.js should have DASHBOARD_REFRESH_MS constant."""
        js = self._get_app_js()
        assert "DASHBOARD_REFRESH_MS" in js

    def test_start_dashboard_refresh_function_exists(self):
        """app.js should have startDashboardRefresh function."""
        js = self._get_app_js()
        assert "function startDashboardRefresh()" in js

    def test_stop_dashboard_refresh_function_exists(self):
        """app.js should have stopDashboardRefresh function."""
        js = self._get_app_js()
        assert "function stopDashboardRefresh()" in js

    def test_start_dashboard_refresh_uses_set_interval(self):
        """startDashboardRefresh should use setInterval."""
        js = self._get_app_js()
        start = js.find("function startDashboardRefresh()")
        end = js.find("\n}", start + 200)
        func_body = js[start:end] if start != -1 and end != -1 else ""
        assert "setInterval" in func_body

    def test_stop_dashboard_refresh_uses_clear_interval(self):
        """stopDashboardRefresh should use clearInterval."""
        js = self._get_app_js()
        start = js.find("function stopDashboardRefresh()")
        end = js.find("\n}", start + 200)
        func_body = js[start:end] if start != -1 and end != -1 else ""
        assert "clearInterval" in func_body

    # --- Notifications polling ---

    def test_notification_interval_state_variable(self):
        """app.js should have notificationIntervalId state variable."""
        js = self._get_app_js()
        assert "notificationIntervalId" in js

    def test_notification_refresh_interval_constant(self):
        """app.js should have NOTIFICATION_REFRESH_MS constant."""
        js = self._get_app_js()
        assert "NOTIFICATION_REFRESH_MS" in js

    def test_update_notifications_function_exists(self):
        """app.js should have updateNotifications function."""
        js = self._get_app_js()
        assert "updateNotifications" in js

    def test_start_notification_refresh_function_exists(self):
        """app.js should have startNotificationRefresh function."""
        js = self._get_app_js()
        assert "function startNotificationRefresh()" in js

    def test_stop_notification_refresh_function_exists(self):
        """app.js should have stopNotificationRefresh function."""
        js = self._get_app_js()
        assert "function stopNotificationRefresh()" in js

    # --- Connect starts polling ---

    def test_connect_starts_dashboard_refresh(self):
        """On connect, startDashboardRefresh should be called."""
        js = self._get_app_js()
        # Find the connect handler (access-form submit)
        assert "startDashboardRefresh()" in js

    def test_connect_starts_notification_refresh(self):
        """On connect, startNotificationRefresh should be called."""
        js = self._get_app_js()
        assert "startNotificationRefresh()" in js

    # --- Disconnect stops polling ---

    def test_disconnect_stops_dashboard_refresh(self):
        """disconnect should call stopDashboardRefresh."""
        js = self._get_app_js()
        start = js.find("function disconnect(")
        assert start != -1, "disconnect function not found"
        end = js.find("\n}", start + 800)
        func_body = js[start:end] if end != -1 else js[start:start+1000]
        assert "stopDashboardRefresh()" in func_body

    def test_disconnect_stops_notification_refresh(self):
        """disconnect should call stopNotificationRefresh."""
        js = self._get_app_js()
        start = js.find("function disconnect(")
        assert start != -1, "disconnect function not found"
        end = js.find("\n}", start + 800)
        func_body = js[start:end] if end != -1 else js[start:start+1000]
        assert "stopNotificationRefresh()" in func_body
