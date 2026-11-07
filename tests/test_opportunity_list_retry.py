"""Exercise opportunity list refresh feedback and retry handlers."""
import subprocess


def test_opportunity_list_refresh_can_retry_after_failure():
    subprocess.run(["node", "tests/js/opportunity_list_retry.cjs"], check=True)
