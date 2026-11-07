import pathlib
import subprocess


def test_customer_conversation_retry_controls_exist():
    html = pathlib.Path("app/operator_ui/index.html").read_text()
    assert 'id="customer-conversations-status"' in html
    assert 'role="status" aria-live="polite"' in html
    assert 'id="customer-conversations-retry"' in html
    assert 'aria-controls="customer-conversations-list"' in html


def test_customer_conversation_retry_behavior():
    subprocess.run(["node", "tests/js/customer_detail_conversation_retry.cjs"], check=True)
