import subprocess


def test_reply_template_empty_status_behavior():
    subprocess.run(["node", "tests/js/reply_template_empty_status.cjs"], check=True)
