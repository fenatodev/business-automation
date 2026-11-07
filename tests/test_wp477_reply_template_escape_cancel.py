import subprocess


def test_reply_template_escape_cancels_edit_only():
    subprocess.run(
        ["node", "tests/js/reply_template_escape_cancel.cjs"], check=True
    )
