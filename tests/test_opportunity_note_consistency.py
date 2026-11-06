"""Run the actual opportunity note listener against synthetic delayed responses."""
import subprocess


def test_opportunity_note_consistency():
    subprocess.run(["node", "tests/js/opportunity_note_consistency.cjs"], check=True)
