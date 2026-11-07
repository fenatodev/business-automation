from pathlib import Path
import subprocess


def test_conversation_message_retry_controls_exist():
    html = Path("app/operator_ui/index.html").read_text()
    assert 'id="conv-messages-status"' in html
    assert 'role="status" aria-live="polite"' in html
    assert 'id="conv-messages-retry"' in html
    assert 'aria-controls="conv-messages"' in html


def test_conversation_message_retry_behavior():
    subprocess.run(["node", "tests/js/conversation_message_retry.cjs"], check=True)
