from pathlib import Path
import subprocess


def test_reply_template_submit_guard():
    subprocess.run(["node", "tests/js/reply_template_submit_guard.cjs"], check=True)
