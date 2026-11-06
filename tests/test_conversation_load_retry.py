"""Exercise conversation refresh failure and retry through the real UI handlers."""
import subprocess
from html.parser import HTMLParser
from pathlib import Path


def test_conversation_load_retry_behavior():
    subprocess.run(["node", "tests/js/conversation_load_retry.cjs"], check=True)


def test_conversation_load_feedback_markup():
    class Elements(HTMLParser):
        def __init__(self):
            super().__init__()
            self.by_id = {}

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if "id" in attrs:
                self.by_id[attrs["id"]] = (tag, attrs)

    parser = Elements()
    parser.feed(Path("app/operator_ui/index.html").read_text())
    _, status = parser.by_id["conv-load-status"]
    assert status["role"] == "status"
    assert status["aria-live"] == "polite"
    tag, retry = parser.by_id["conv-load-retry"]
    assert tag == "button"
    assert retry["type"] == "button"
    assert "hidden" in retry
    assert retry["aria-controls"] == "conv-list"
    assert parser.by_id["conv-list"][1]["aria-busy"] == "false"
