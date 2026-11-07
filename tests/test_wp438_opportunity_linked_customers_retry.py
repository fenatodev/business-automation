from pathlib import Path
import subprocess


def test_opportunity_linked_customers_retry_controls_exist():
    html = Path("app/operator_ui/index.html").read_text()
    assert 'id="opp-customers-status"' in html
    assert 'id="opp-customers-retry"' in html
    assert 'aria-controls="opp-customers-list"' in html


def test_opportunity_linked_customers_retry_behavior():
    subprocess.run(["node", "tests/js/opportunity_linked_customers_retry.cjs"], check=True)
