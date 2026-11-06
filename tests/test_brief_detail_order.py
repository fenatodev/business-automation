"""Run the delivered brief detail handlers with controlled synthetic responses."""
import subprocess


def test_brief_detail_selection_order():
    subprocess.run(["node", "tests/js/brief_detail_order.cjs"], check=True)
