"""Exercise overlapping searches through the real lead UI event handlers."""
import subprocess


def test_latest_lead_refresh_wins():
    subprocess.run(["node", "tests/js/lead_refresh_order.cjs"], check=True)
