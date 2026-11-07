from pathlib import Path
import subprocess


def test_opportunity_conversation_retry_controls_exist():
    html = Path("app/operator_ui/index.html").read_text()
    assert 'id="opp-conv-status"' in html
    assert 'role="status" aria-live="polite"' in html
    assert 'id="opp-conv-retry"' in html
    assert 'aria-controls="opp-conv-list"' in html


def test_opportunity_conversation_retry_behavior():
    subprocess.run(["node", "tests/js/opportunity_conversation_retry.cjs"], check=True)
