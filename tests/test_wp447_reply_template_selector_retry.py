from pathlib import Path
import subprocess


def test_reply_template_selector_retry_controls_exist():
    html = Path("app/operator_ui/index.html").read_text()
    assert 'id="reply-template-status"' in html
    assert 'id="reply-template-retry"' in html


def test_reply_template_selector_retry_behavior():
    subprocess.run(["node", "tests/js/reply_template_selector_retry.cjs"], check=True)
