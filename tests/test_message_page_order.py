"""Exercise real message pagination handlers with overlapping API responses."""
import subprocess


def test_latest_message_page_wins():
    subprocess.run(["node", "tests/js/message_page_order.cjs"], check=True)
