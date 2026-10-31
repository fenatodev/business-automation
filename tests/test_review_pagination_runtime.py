"""Run actual UI JavaScript to catch route validation regressions missed by static checks."""
from pathlib import Path
import subprocess


def test_review_queue_pagination_runtime():
    result = subprocess.run(
        ["node", "tests/js/review_pagination.cjs"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stdout + result.stderr
