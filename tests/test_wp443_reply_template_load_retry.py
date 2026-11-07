from pathlib import Path
import subprocess


def test_reply_template_retry_control_exists():
    html = Path("app/operator_ui/index.html").read_text()
    assert 'id="reply-template-load-status"' in html
    assert 'role="status" aria-live="polite"' in html
    assert 'id="reply-template-load-retry"' in html
    assert 'aria-controls="reply-template-list"' in html


def test_reply_template_retry_behavior():
    subprocess.run(["node", "tests/js/reply_template_load_retry.cjs"], check=True)
