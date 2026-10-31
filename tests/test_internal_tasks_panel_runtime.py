"""Run internal tasks panel JavaScript to catch route validation regressions."""
from pathlib import Path
import subprocess


def test_internal_tasks_panel_runtime():
    result = subprocess.run(
        ["node", "tests/js/internal_tasks.cjs"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stdout + result.stderr
