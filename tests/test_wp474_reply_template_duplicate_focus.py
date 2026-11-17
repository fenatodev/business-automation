import subprocess


def test_reply_template_duplicate_focus():
    subprocess.run(
        ["node", "tests/js/reply_template_duplicate_focus.cjs"], check=True
    )
