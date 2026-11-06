"""Exercise overlapping conversation queries through real UI event handlers."""
import subprocess


def test_latest_conversation_refresh_wins():
    subprocess.run(["node", "tests/js/conversation_refresh_order.cjs"], check=True)
