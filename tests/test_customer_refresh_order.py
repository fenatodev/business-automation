"""Exercise overlapping customer searches through real UI event handlers."""
import subprocess


def test_latest_customer_refresh_wins():
    subprocess.run(["node", "tests/js/customer_refresh_order.cjs"], check=True)
