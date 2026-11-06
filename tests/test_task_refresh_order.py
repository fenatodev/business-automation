"""Exercise overlapping task queries through real operator UI handlers."""
import subprocess


def test_latest_task_refresh_wins():
    subprocess.run(["node", "tests/js/task_refresh_order.cjs"], check=True)
