"""Exercise concurrent dashboard polling with controlled synthetic responses."""
import subprocess


def test_latest_dashboard_refresh_wins():
    subprocess.run(["node", "tests/js/dashboard_refresh_order.cjs"], check=True)
