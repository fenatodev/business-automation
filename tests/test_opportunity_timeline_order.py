"""Exercise timeline selection races using synthetic responses and the real handler."""
import subprocess


def test_opportunity_timeline_selection_order():
    subprocess.run(["node", "tests/js/opportunity_timeline_order.cjs"], check=True)
