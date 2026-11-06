"""Exercise lead detail reads with synthetic responses and navigation."""
import subprocess


def test_lead_detail_conversations():
    subprocess.run(["node", "tests/js/lead_detail_conversations.cjs"], check=True)
