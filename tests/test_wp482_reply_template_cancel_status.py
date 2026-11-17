import subprocess


def test_reply_template_cancel_status():
    subprocess.run(
        ["node", "tests/js/reply_template_cancel_status.cjs"], check=True
    )
