from pathlib import Path
import subprocess


def test_proposal_brief_retry_control_exists():
    html = Path("app/operator_ui/index.html").read_text()
    assert 'id="brief-load-retry"' in html
    assert 'aria-controls="brief-form"' in html


def test_proposal_brief_retry_behavior():
    subprocess.run(["node", "tests/js/proposal_brief_retry.cjs"], check=True)
