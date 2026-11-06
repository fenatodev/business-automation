"""Run customer detail handlers with controlled synthetic responses."""
import subprocess


def test_customer_conversation_selection_order():
    subprocess.run(["node", "tests/js/customer_conversation_order.cjs"], check=True)
