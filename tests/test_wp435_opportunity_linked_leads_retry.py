from pathlib import Path
import subprocess


def test_opportunity_linked_leads_retry_controls_exist():
    html = Path("app/operator_ui/index.html").read_text()
    assert 'id="opp-leads-status"' in html
    assert 'role="status" aria-live="polite"' in html
    assert 'id="opp-leads-retry"' in html
    assert 'aria-controls="opp-leads-list"' in html


def test_opportunity_linked_leads_retry_behavior():
    subprocess.run(["node", "tests/js/opportunity_linked_leads_retry.cjs"], check=True)
