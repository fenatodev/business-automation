"""Exercise the actual opportunity editor with synthetic delayed responses."""
import subprocess


def test_opportunity_edit_consistency():
    subprocess.run(["node", "tests/js/opportunity_edit_consistency.cjs"], check=True)
