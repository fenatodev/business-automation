import subprocess


def test_reply_template_cancel_focus():
    subprocess.run(
        ["node", "tests/js/reply_template_cancel_focus.cjs"], check=True
    )
